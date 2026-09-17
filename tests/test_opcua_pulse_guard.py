"""Faz 2: request_pulse must not stack a second TRUE/FALSE edge for the same
command while one is already mid-pulse (user requirement, 2026-09-16)."""

from __future__ import annotations

import asyncio

from plc.models import OpcUaConfig
from plc.opcua_client import OpcUaWorker
from plc.tag_map import TagMap


def test_request_pulse_ignores_second_call_while_in_flight():
    config = OpcUaConfig(endpoint="", command_pulse_ms=50)
    worker = OpcUaWorker(config, TagMap(config))
    calls: list[tuple[str, bool]] = []

    async def fake_write(name: str, value) -> None:
        calls.append((name, value))

    worker._write = fake_write  # type: ignore[method-assign]

    async def scenario() -> None:
        worker._loop = asyncio.get_running_loop()
        worker.request_pulse("cmd_start")
        worker.request_pulse("cmd_start")  # same command, already in flight -> ignored
        await asyncio.sleep(0.15)  # let the 50ms pulse complete

    asyncio.run(scenario())

    assert calls == [("cmd_start", True), ("cmd_start", False)]


def test_request_pulse_allows_different_commands_concurrently():
    config = OpcUaConfig(endpoint="", command_pulse_ms=50)
    worker = OpcUaWorker(config, TagMap(config))
    calls: list[tuple[str, bool]] = []

    async def fake_write(name: str, value) -> None:
        calls.append((name, value))

    worker._write = fake_write  # type: ignore[method-assign]

    async def scenario() -> None:
        worker._loop = asyncio.get_running_loop()
        worker.request_pulse("cmd_start")
        worker.request_pulse("cmd_stop")  # different command -> must still fire
        await asyncio.sleep(0.15)

    asyncio.run(scenario())

    assert ("cmd_start", True) in calls
    assert ("cmd_stop", True) in calls


def test_request_pulse_allows_repeat_after_previous_pulse_completes():
    config = OpcUaConfig(endpoint="", command_pulse_ms=30)
    worker = OpcUaWorker(config, TagMap(config))
    calls: list[tuple[str, bool]] = []

    async def fake_write(name: str, value) -> None:
        calls.append((name, value))

    worker._write = fake_write  # type: ignore[method-assign]

    async def scenario() -> None:
        worker._loop = asyncio.get_running_loop()
        worker.request_pulse("cmd_reset")
        await asyncio.sleep(0.08)  # let it fully complete
        worker.request_pulse("cmd_reset")  # second, separate press -> must fire
        await asyncio.sleep(0.08)

    asyncio.run(scenario())

    assert calls == [
        ("cmd_reset", True),
        ("cmd_reset", False),
        ("cmd_reset", True),
        ("cmd_reset", False),
    ]
