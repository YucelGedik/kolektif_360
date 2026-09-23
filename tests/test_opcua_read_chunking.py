"""Gerçek PLC bulgusu (2026-09-23): config'e 8 aday tag (H12-H15/H20-H22/
U06) eklenip toplam node sayısı 96'dan 104'e çıkınca, tek `read_values()`
çağrısı sunucudan `BadTooManyOperations` aldı. Salt-okunur browse +
ampirik bisect ile sunucunun sınırı doğrulandı: `MaxNodesPerRead=100`
(n=100 OK, n=101 FAIL - tam sınır). `_read_loop` artık bu sınırı aşan node
listelerini birden çok `read_values()` çağrısına bölüyor."""

from __future__ import annotations

import asyncio
import math

from plc import opcua_client
from plc.models import OpcUaConfig
from plc.opcua_client import OpcUaWorker
from plc.tag_map import TagMap


class _FakeNode:
    def __init__(self, name: str):
        self.name = name


class _FakeClient:
    """`read_values()` sayaç tutar; her tam "tick" (tüm chunk'lar okunduğunda)
    worker'ı durdurur ki `_read_loop` sonsuz döngüde kalmasın."""

    def __init__(self, worker: OpcUaWorker, chunks_per_tick: int):
        self._worker = worker
        self._chunks_per_tick = chunks_per_tick
        self.calls: list[list[str]] = []

    async def read_values(self, nodes):
        self.calls.append([n.name for n in nodes])
        if len(self.calls) == self._chunks_per_tick:
            self._worker._running = False
        return [f"value-{n.name}" for n in nodes]


class _FakeSignal:
    def __init__(self):
        self.received: list[dict] = []

    def emit(self, value):
        self.received.append(value)


def test_read_loop_splits_into_chunks_under_the_server_limit(monkeypatch):
    monkeypatch.setattr(opcua_client, "MAX_NODES_PER_READ", 3)
    config = OpcUaConfig(endpoint="", read_interval_ms=5)
    worker = OpcUaWorker(config, TagMap(config))
    worker._nodes = {f"tag{i}": _FakeNode(f"tag{i}") for i in range(7)}

    expected_chunks = math.ceil(7 / 3)  # [3, 3, 1] -> 3 çağrı
    fake_client = _FakeClient(worker, chunks_per_tick=expected_chunks)
    worker._client = fake_client
    signal = _FakeSignal()
    worker.snapshotReady = signal  # type: ignore[assignment]

    async def scenario() -> None:
        worker._stop_event = asyncio.Event()
        worker._running = True
        await worker._read_loop()

    asyncio.run(scenario())

    assert [len(c) for c in fake_client.calls] == [3, 3, 1]
    assert len(signal.received) == 1
    merged = signal.received[0]
    assert set(merged.keys()) == {f"tag{i}" for i in range(7)}
    assert merged["tag0"] == "value-tag0"
    assert merged["tag6"] == "value-tag6"


def test_read_loop_issues_a_single_call_when_under_the_limit(monkeypatch):
    monkeypatch.setattr(opcua_client, "MAX_NODES_PER_READ", 100)
    config = OpcUaConfig(endpoint="", read_interval_ms=5)
    worker = OpcUaWorker(config, TagMap(config))
    worker._nodes = {f"tag{i}": _FakeNode(f"tag{i}") for i in range(5)}

    fake_client = _FakeClient(worker, chunks_per_tick=1)
    worker._client = fake_client
    signal = _FakeSignal()
    worker.snapshotReady = signal  # type: ignore[assignment]

    async def scenario() -> None:
        worker._stop_event = asyncio.Event()
        worker._running = True
        await worker._read_loop()

    asyncio.run(scenario())

    assert len(fake_client.calls) == 1
    assert len(fake_client.calls[0]) == 5
