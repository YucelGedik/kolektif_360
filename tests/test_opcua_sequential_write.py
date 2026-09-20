"""Faz 2 (geçici Vision veri simülatörü, PLC-HMI-20260917-02):
`request_write_sequence` must write each field in order, waiting for each
write to actually complete before starting the next, and must stop (not
write past) the first failure - so "data fields before sequence number" is
a real network-level ordering guarantee, not just call order. Plain
back-to-back `request_write()` calls give no such guarantee (each schedules
an independent coroutine)."""

from __future__ import annotations

import asyncio

from plc.models import OpcUaConfig
from plc.opcua_client import OpcUaWorker
from plc.tag_map import TagMap


def _worker() -> OpcUaWorker:
    config = OpcUaConfig(endpoint="")
    return OpcUaWorker(config, TagMap(config))


def test_write_sequence_writes_all_fields_in_order_and_reports_success():
    worker = _worker()
    calls: list[tuple[str, object]] = []
    results: list[tuple[bool, str]] = []
    worker.sequentialWriteResult.connect(lambda ok, msg: results.append((ok, msg)))

    async def fake_write_checked(name, value):
        calls.append((name, value))
        return True, ""

    worker._write_checked = fake_write_checked  # type: ignore[method-assign]

    async def scenario():
        worker._loop = asyncio.get_running_loop()
        worker.request_write_sequence(
            [
                ("vision_target_x", 10.0),
                ("vision_target_y", 1.0),
                ("vision_ready", True),
                ("vision_sequence", 101),
            ]
        )
        await asyncio.sleep(0.05)

    asyncio.run(scenario())

    assert calls == [
        ("vision_target_x", 10.0),
        ("vision_target_y", 1.0),
        ("vision_ready", True),
        ("vision_sequence", 101),
    ]
    assert results == [(True, "")]


def test_write_sequence_stops_at_first_failure_and_never_writes_sequence():
    worker = _worker()
    calls: list[tuple[str, object]] = []
    results: list[tuple[bool, str]] = []
    worker.sequentialWriteResult.connect(lambda ok, msg: results.append((ok, msg)))

    async def fake_write_checked(name, value):
        calls.append((name, value))
        if name == "vision_target_y":
            return False, "BadTypeMismatch"
        return True, ""

    worker._write_checked = fake_write_checked  # type: ignore[method-assign]

    async def scenario():
        worker._loop = asyncio.get_running_loop()
        worker.request_write_sequence(
            [
                ("vision_target_x", 10.0),
                ("vision_target_y", 1.0),
                ("vision_sequence", 101),
            ]
        )
        await asyncio.sleep(0.05)

    asyncio.run(scenario())

    assert calls == [("vision_target_x", 10.0), ("vision_target_y", 1.0)]
    assert results == [(False, "Yazma başarısız: vision_target_y (BadTypeMismatch)")]


def test_write_sequence_awaits_each_write_before_starting_the_next():
    """The core requirement: a slow first write must actually finish before
    the next one starts, not just be *called* first."""
    worker = _worker()
    order: list[str] = []

    async def fake_write_checked(name, value):
        if name == "slow":
            await asyncio.sleep(0.05)
        order.append(name)
        return True, ""

    worker._write_checked = fake_write_checked  # type: ignore[method-assign]

    async def scenario():
        worker._loop = asyncio.get_running_loop()
        worker.request_write_sequence([("slow", 1), ("fast", 2)])
        await asyncio.sleep(0.1)

    asyncio.run(scenario())

    assert order == ["slow", "fast"]


def test_request_write_sequence_reports_failure_when_no_loop():
    worker = _worker()
    results: list[tuple[bool, str]] = []
    worker.sequentialWriteResult.connect(lambda ok, msg: results.append((ok, msg)))

    worker.request_write_sequence([("vision_target_x", 1.0)])

    assert results == [(False, "PLC bağlı değil")]
