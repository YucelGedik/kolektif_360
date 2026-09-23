"""asyncua-based OPC UA worker.

Runs its own asyncio event loop inside a QThread so the Qt UI thread is never
blocked by network I/O (brief section 11, 18, 20, 26). Exposes Qt signals for
connection state and snapshot updates, and thread-safe methods to request
writes from the UI thread.

Connection state machine: Disconnected -> Connecting -> Connected / Degraded
/ Error, with reconnect on drop (brief section 18). Reads are batched via
`Client.read_values` once per configured `read_interval_ms`.

Known follow-up (brief section 28, "OPC UA endpoint security configuration",
"actual CODESYS namespace table"): value writes let asyncua infer the OPC UA
VariantType from the Python type by default (bool -> Boolean, float ->
Double, int -> Int64). Confirmed real-PLC mismatch (2026-09-17): PLC UDINT
tags (`Heartbeat`, `udiVisionSequence`) rejected a plain Python `int` write
because asyncua infers `Int64` for it, not `UInt32` - `EXPLICIT_VARIANT_TYPES`
below overrides the inferred type for exactly those tags.

Second confirmed mismatch (2026-09-18, real-PLC "BadTypeMismatch" on
Settings LREAL parameters `lrX_CutVelocity`/`lrX_CutEndPos` - reads work,
writes are rejected): guessing the right VariantType per tag ahead of
evidence doesn't scale and got this one wrong too (a plain Python float
correctly infers Double, yet the server still rejected it - the node's
*actual* advertised DataType on this particular symbol must be something
else, e.g. Float/Single). Instead of adding more guesses, `_write_checked`
now asks the SERVER what DataType each node actually is
(`Node.read_data_type_as_variant_type()`, cached per tag after the first
successful read) and writes using THAT type whenever no `EXPLICIT_
VARIANT_TYPES` override exists - self-correcting for every tag, not just
ones we've hit a bug report for. `EXPLICIT_VARIANT_TYPES` stays as a
zero-round-trip fast path for the two tags already confirmed by source
(GVL is UDINT) and as a fallback if the server query itself fails.
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

# Tags whose real PLC DataType does not match what asyncua would infer from
# the Python value's type, so an explicit VariantType must be sent instead
# (2026-09-17, real-PLC bug report: "Yazma başarısız: vision_sequence" -
# GVL.Heartbeat / GVL.udiVisionSequence are UDINT; a plain Python int would
# be sent as Int64 and rejected). Add further tags here only after a real
# BadTypeMismatch is confirmed for them - do not guess ahead of evidence.
EXPLICIT_VARIANT_TYPES: dict[str, "ua.VariantType"] = {
    "vision_sequence": ua.VariantType.UInt32,
    "vision_heartbeat": ua.VariantType.UInt32,
}

# Gerçek PLC bulgusu (2026-09-23): config'e 8 aday tag (H12-H15/H20-H22/U06)
# eklenip node sayısı 96'dan 104'e çıkınca, tek `read_values()` çağrısı
# `BadTooManyOperations` ile reddedildi. Salt-okunur browse ile sunucunun
# `ServerCapabilities/OperationLimits/MaxNodesPerRead` değeri doğrulandı
# (=100) VE ampirik olarak bisect edildi (n=100 OK, n=101 FAIL - tam sınır).
# Node sayısı zamanla büyümeye devam edecek (yeni PLC görevleri) - sabit bir
# üst sınıra güvenmek yerine `_read_loop` artık gerekirse birden çok
# `read_values()` çağrısına bölünür.
MAX_NODES_PER_READ = 100


class OpcUaWorker(QThread):
    connectionStateChanged = Signal(str)
    snapshotReady = Signal(dict)
    errorOccurred = Signal(str)
    # Geçici Vision veri simülatörü (PLC-HMI-20260917-02): tek paketin tüm
    # alanlarını sırayla, her birinin ağ üzerinden tamamlanmasını bekleyerek
    # yazar - back-to-back fire-and-forget request_write() çağrıları OPC UA
    # seviyesinde sıralama garantisi vermiyor (görev notu). Sonuç tek sinyalle
    # bildirilir: tüm alanlar başarılıysa True, ilk başarısız alanda False +
    # hangi tag olduğunu söyleyen mesaj; kalan alanlar yazılmaz.
    sequentialWriteResult = Signal(bool, str)

    def __init__(self, config: OpcUaConfig, tag_map: TagMap, parent=None):
        super().__init__(parent)
        self._config = config
        self._tag_map = tag_map
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._client: Client | None = None
        self._nodes: dict[str, Any] = {}
        self._running = True
        self._pulses_in_flight: set[str] = set()
        self._sequence_future: "asyncio.Future | None" = None
        # Tag -> server-reported VariantType, resolved lazily on first write
        # and cached for the life of this connection (cleared on reconnect,
        # since node handles/session are recreated then).
        self._resolved_variant_types: dict[str, "ua.VariantType"] = {}

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
                self._resolved_variant_types = {}

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
        # MAX_NODES_PER_READ (2026-09-23 gerçek PLC bulgusu): sunucu tek
        # Read servisinde bu sayıdan fazla node'u reddediyor - birden çok
        # node_list bu sınırı aşarsa birden fazla `read_values()` çağrısına
        # bölünür, her tick'te aynı toplam snapshot'ı üretmeye devam eder.
        name_chunks = [names[i : i + MAX_NODES_PER_READ] for i in range(0, len(names), MAX_NODES_PER_READ)]
        node_chunks = [node_list[i : i + MAX_NODES_PER_READ] for i in range(0, len(node_list), MAX_NODES_PER_READ)]
        consecutive_errors = 0

        while self._running:
            try:
                snapshot: dict[str, Any] = {}
                for chunk_names, chunk_nodes in zip(name_chunks, node_chunks):
                    values = await self._client.read_values(chunk_nodes)
                    snapshot.update(zip(chunk_names, values))
                self.snapshotReady.emit(snapshot)
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
        if name in self._pulses_in_flight:
            # Same command already mid-pulse (e.g. double-click) - ignore
            # rather than stacking a second TRUE/FALSE edge. Marked here,
            # synchronously, so two request_pulse() calls made back-to-back
            # (no await between them) still see each other.
            return
        self._pulses_in_flight.add(name)
        asyncio.run_coroutine_threadsafe(self._pulse(name), self._loop)

    def request_write_sequence(self, fields: list[tuple[str, Any]]) -> None:
        """Writes each (tag, value) in `fields` one at a time, awaiting the
        PLC's write response before starting the next one, then emits
        `sequentialWriteResult`. Used only by the temporary Vision simulator
        (2026-09-17) so the "data fields before sequence number" packet
        contract is an actual network-level ordering guarantee, not just
        call order on our side."""
        if self._loop is None:
            self.sequentialWriteResult.emit(False, "PLC bağlı değil")
            return
        self._sequence_future = asyncio.run_coroutine_threadsafe(
            self._write_sequence(list(fields)), self._loop
        )

    def cancel_pending_sequence(self) -> None:
        """Gerçekten iptal eder - sadece sonucu yok saymaz (görev notu,
        2026-09-17: "Generation yalnız eski sonucu yok saymak değil,
        worker'daki eski yazıları gerçekten iptal/engellemek için
        kullanılmalı"). Disarm/reconnect anında hâlâ bekleyen bir paket
        varsa, kalan alanları (özellikle sequence'i) PLC'ye YAZMADAN durur -
        `await` noktasında `CancelledError` fırlatılır, `_write_sequence`
        bunu sessizce yutar (artık geçerli bir oturum yok, bildirecek sonuç
        da yok)."""
        future = self._sequence_future
        if future is not None and not future.done():
            future.cancel()

    async def _write_sequence(self, fields: list[tuple[str, Any]]) -> None:
        try:
            for name, value in fields:
                ok, error = await self._write_checked(name, value)
                if not ok:
                    # Gerçek OPC UA hata metnini kullanıcıya göster - salt
                    # "tag adı" (2026-09-17 bug report: bunu görmeden
                    # BadTypeMismatch teşhis edilemiyordu).
                    self.sequentialWriteResult.emit(False, f"Yazma başarısız: {name} ({error})")
                    return
            self.sequentialWriteResult.emit(True, "")
        except asyncio.CancelledError:
            pass  # disarmed/reconnected mid-flight - bildirilecek bir sonuç yok

    async def _write(self, name: str, value: Any) -> None:
        await self._write_checked(name, value)

    async def _resolve_variant_type(self, name: str, node: Any) -> "ua.VariantType | None":
        """Server-confirmed VariantType for this node, resolved once and
        cached (2026-09-18: guessing per-tag doesn't scale - ask the PLC
        what type it actually advertises instead)."""
        cached = self._resolved_variant_types.get(name)
        if cached is not None:
            return cached
        try:
            variant_type = await node.read_data_type_as_variant_type()
        except Exception as exc:  # noqa: BLE001 - best-effort, fall back to inferred type
            logger.warning("Could not read DataType for '%s': %s", name, exc)
            return None
        self._resolved_variant_types[name] = variant_type
        return variant_type

    async def _write_checked(self, name: str, value: Any) -> tuple[bool, str]:
        node = self._nodes.get(name)
        if node is None or self._client is None:
            message = f"Write skipped, not connected: {name}"
            self.errorOccurred.emit(message)
            return False, message
        try:
            explicit_type = EXPLICIT_VARIANT_TYPES.get(name)
            if explicit_type is not None:
                # Bilinen UDINT tagları - her zaman int değer (vision_
                # simulator bu ikisine hep int/mod-2^32 sonucu yollar).
                await node.write_value(ua.Variant(int(value), explicit_type))
            elif (resolved_type := await self._resolve_variant_type(name, node)) is not None:
                await node.write_value(ua.Variant(value, resolved_type))
            else:
                # Sunucu tipi öğrenilemedi (ör. okuma da başarısız) - eski
                # davranış: asyncua'nın Python tipinden çıkarımına güven.
                await node.write_value(value)
            return True, ""
        except (ua.UaError, OSError) as exc:
            message = f"{exc.__class__.__name__}: {exc}"
            self.errorOccurred.emit(f"Write failed for '{name}': {message}")
            return False, message

    async def _pulse(self, name: str) -> None:
        try:
            await self._write(name, True)
            await asyncio.sleep(self._config.command_pulse_ms / 1000)
            await self._write(name, False)
        finally:
            self._pulses_in_flight.discard(name)
