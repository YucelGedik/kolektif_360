"""PLC-HMI-20260917-03 görev notu: "Generation yalnız eski sonucu yok saymak
değil, worker'daki eski yazıları gerçekten iptal/engellemek için
kullanılmalı." Bu testler `OpcUaWorker.cancel_pending_sequence()`'ın bekleyen
bir `request_write_sequence` coroutine'ini GERÇEKTEN durdurduğunu (kalan
alanları PLC'ye hiç yazmadan) doğrular - sadece Qt sinyal sonucunu yok saymak
değil."""

from __future__ import annotations

import asyncio

from plc.models import OpcUaConfig
from plc.opcua_client import OpcUaWorker
from plc.tag_map import TagMap


def _worker() -> OpcUaWorker:
    config = OpcUaConfig(endpoint="")
    return OpcUaWorker(config, TagMap(config))


def test_cancel_pending_sequence_stops_before_remaining_fields_are_written():
    worker = _worker()
    calls: list[str] = []
    results: list[tuple[bool, str]] = []
    worker.sequentialWriteResult.connect(lambda ok, msg: results.append((ok, msg)))

    async def fake_write_checked(name, value):
        calls.append(name)
        if name == "slow":
            await asyncio.sleep(0.2)  # cancel() bu await sırasında gelecek
        return True, ""

    worker._write_checked = fake_write_checked  # type: ignore[method-assign]

    async def scenario():
        worker._loop = asyncio.get_running_loop()
        worker.request_write_sequence([("slow", 1), ("vision_sequence", 5)])
        await asyncio.sleep(0.02)  # "slow" başladı, henüz tamamlanmadı
        worker.cancel_pending_sequence()
        await asyncio.sleep(0.3)  # iptalin işlendiğinden emin ol

    asyncio.run(scenario())

    assert calls == ["slow"]  # "vision_sequence" HİÇ yazılmadı
    assert results == []  # iptal edilen bir sonuç sinyali göndermez


def test_cancel_pending_sequence_is_a_noop_if_nothing_pending():
    worker = _worker()

    worker.cancel_pending_sequence()  # crash etmemeli

    assert True


def test_cancel_pending_sequence_does_not_affect_an_already_completed_write():
    worker = _worker()
    calls: list[str] = []
    results: list[tuple[bool, str]] = []
    worker.sequentialWriteResult.connect(lambda ok, msg: results.append((ok, msg)))

    async def fake_write_checked(name, value):
        calls.append(name)
        return True, ""

    worker._write_checked = fake_write_checked  # type: ignore[method-assign]

    async def scenario():
        worker._loop = asyncio.get_running_loop()
        worker.request_write_sequence([("vision_target_x", 1.0), ("vision_sequence", 5)])
        await asyncio.sleep(0.05)  # tamamlanmasına izin ver
        worker.cancel_pending_sequence()  # artık done() -> etkisiz
        await asyncio.sleep(0.02)

    asyncio.run(scenario())

    assert calls == ["vision_target_x", "vision_sequence"]
    assert results == [(True, "")]
