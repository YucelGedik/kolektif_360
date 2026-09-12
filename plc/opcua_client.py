"""asyncua-based OPC UA worker.

Runs its own asyncio event loop inside a QThread so the Qt UI thread is never
blocked by network I/O (brief section 11, 18, 20, 26). Exposes Qt signals for
connection state and snapshot updates, and thread-safe methods to request
writes from the UI thread.

Connection state machine: Disconnected -> Connecting -> Connected / Degraded
/ Error, with reconnect on drop (brief section 18). Reads are batched via
`Client.read_values` once per configured `read_interval_ms`.

Known follow-up (brief section 28, "OPC UA endpoint security configuration",
"actual CODESYS namespace table"): value writes currently let asyncua infer
the OPC UA VariantType from the Python type. Once the real PLC GVL is
finalized, verify each tag's actual DataType (Bool / Real / LReal / Int) with
UaExpert and, if any mismatch (`BadTypeMismatch`) appears, pass an explicit
`ua.VariantType` into `write_value` for that tag.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from asyncua import Client, ua
from PySide6.QtCore import QThread, Signal

from core.models import ConnectionState
from plc.models import OpcUaConfig
from plc.tag_map import TagMap

logger = logging.getLogger(__name__)


class OpcUaWorker(QThread):
    connectionStateChanged = Signal(str)
    snapshotReady = Signal(dict)
    errorOccurred = Signal(str)

    def __init__(self, config: OpcUaConfig, tag_map: TagMap, parent=None):
        super().__init__(parent)
        self._config = config
        self._tag_map = tag_map
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._client: Client | None = None
        self._nodes: dict[str, Any] = {}
        self._running = True

    # -- lifecycle -----------------------------------------------------

    def run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as exc:  # pragma: no cover - defensive top-level guard
            logger.exception("OPC UA worker crashed")
            self.errorOccurred.emit(str(exc))

    def stop(self) -> None:
        self._running = False
        loop, event = self._loop, self._stop_event
        if loop is not None and event is not None:
            loop.call_soon_threadsafe(event.set)

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        await self._connection_loop()

    # -- connection / read loop -----------------------------------------

    async def _connection_loop(self) -> None:
        backoff = self._config.reconnect_backoff_ms / 1000
        max_backoff = self._config.reconnect_backoff_max_ms / 1000

        while self._running:
            self.connectionStateChanged.emit(ConnectionState.CONNECTING)
            try:
                async with Client(url=self._config.endpoint) as client:
                    self._client = client
                    self._nodes = {
                        name: client.get_node(node_id)
                        for name, node_id in self._config.nodes.items()
                    }
                    self.connectionStateChanged.emit(ConnectionState.CONNECTED)
                    backoff = self._config.reconnect_backoff_ms / 1000
                    await self._read_loop()
            except Exception as exc:
                logger.warning("OPC UA connection lost/failed: %s", exc)
                self.errorOccurred.emit(str(exc))
                self.connectionStateChanged.emit(ConnectionState.ERROR)
            finally:
                self._client = None
                self._nodes = {}

            if not self._running:
                break

            self.connectionStateChanged.emit(ConnectionState.DISCONNECTED)
            if await self._interruptible_sleep(backoff):
                break
            backoff = min(backoff * 2, max_backoff)

    async def _read_loop(self) -> None:
        interval = self._config.read_interval_ms / 1000
        names = list(self._nodes.keys())
        node_list = list(self._nodes.values())
        consecutive_errors = 0

        while self._running:
            try:
                values = await self._client.read_values(node_list)
                self.snapshotReady.emit(dict(zip(names, values)))
                if consecutive_errors > 0:
                    consecutive_errors = 0
                    self.connectionStateChanged.emit(ConnectionState.CONNECTED)
            except Exception as exc:
                consecutive_errors += 1
                self.errorOccurred.emit(str(exc))
                if consecutive_errors >= 3:
                    self.connectionStateChanged.emit(ConnectionState.DEGRADED)
                if consecutive_errors >= 10:
                    raise

            if await self._interruptible_sleep(interval):
                return

    async def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleeps up to `seconds`, returns True if stop() was requested meanwhile."""
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False

    # -- writes (called from the Qt/UI thread) ---------------------------

    def request_write(self, name: str, value: Any) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._write(name, value), self._loop)

    def request_pulse(self, name: str) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._pulse(name), self._loop)

    async def _write(self, name: str, value: Any) -> None:
        node = self._nodes.get(name)
        if node is None or self._client is None:
            self.errorOccurred.emit(f"Write skipped, not connected: {name}")
            return
        try:
            await node.write_value(value)
        except (ua.UaError, OSError) as exc:
            self.errorOccurred.emit(f"Write failed for '{name}': {exc}")

    async def _pulse(self, name: str) -> None:
        await self._write(name, True)
        await asyncio.sleep(self._config.command_pulse_ms / 1000)
        await self._write(name, False)
