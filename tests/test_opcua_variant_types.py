"""Real-PLC bug reports:

- 2026-09-17: TargetX/TargetY yazıldı ama `udiVisionSequence`/`Heartbeat`
  yazımı "Yazma başarısız: vision_sequence" ile başarısız oldu, gerçek neden
  görünmüyordu. Kök neden: bu iki tag PLC'de UDINT; asyncua Python `int`'i
  varsayılan olarak Int64 olarak gönderiyor, PLC reddediyor (BadTypeMismatch).
  `EXPLICIT_VARIANT_TYPES` bu ikisi için açık `ua.VariantType.UInt32` yazar.
- 2026-09-18: Settings ekranındaki LREAL parametreleri (`lrX_CutVelocity`,
  `lrX_CutEndPos`) de BadTypeMismatch verdi - AMA bunlar için plain Python
  `float` doğru şekilde Double'a çıkarılıyordu (asyncua `ua.Variant(175.0)`
  gerçekten Double üretir, doğrulandı); yani tag bazında tahmin etmek
  ölçeklenmiyor/güvenilmiyor. Bunun yerine `_write_checked` artık sunucunun
  bu node için GERÇEKTEN neyi beklediğini soruyor
  (`Node.read_data_type_as_variant_type()`, ilk yazımda çözülüp tag başına
  cache'lenir) ve `EXPLICIT_VARIANT_TYPES`'ta olmayan HER tag için o tipi
  kullanıyor - tahmin değil, sunucudan doğrulanmış bilgi.

Bu testler: (1) iki bilinen UDINT tag'inin açık UInt32 ile gittiğini, (2)
sunucu farklı bir tip bildirdiğinde ONUN kazandığını ve cache'lendiğini, (3)
sunucu sorgusu başarısız olursa eski (örtük/inferred) davranışa düştüğünü,
(4) gerçek OPC UA hata metninin çağırana döndüğünü doğrular. Gerçek bir
PLC'ye bağlanılmaz - `_nodes`/`_client` sahte nesnelerle taklit edilir."""

from __future__ import annotations

import asyncio

import pytest
from asyncua import ua

from plc.models import OpcUaConfig
from plc.opcua_client import EXPLICIT_VARIANT_TYPES, OpcUaWorker
from plc.tag_map import TagMap


class _FakeNode:
    def __init__(self, *, raises: Exception | None = None, server_variant_type=None, type_lookup_raises: Exception | None = None):
        self.written: list[object] = []
        self._raises = raises
        self._server_variant_type = server_variant_type
        self._type_lookup_raises = type_lookup_raises
        self.type_lookup_calls = 0

    async def write_value(self, value):
        if self._raises is not None:
            raise self._raises
        self.written.append(value)

    async def read_data_type_as_variant_type(self):
        self.type_lookup_calls += 1
        if self._type_lookup_raises is not None:
            raise self._type_lookup_raises
        if self._server_variant_type is None:
            raise AttributeError("no server-reported type configured for this fake node")
        return self._server_variant_type


def _worker_with_nodes(nodes: dict[str, _FakeNode]) -> OpcUaWorker:
    config = OpcUaConfig(endpoint="")
    worker = OpcUaWorker(config, TagMap(config))
    worker._client = object()  # only needs to be "not None"
    worker._nodes = nodes
    return worker


def test_vision_sequence_is_written_as_explicit_uint32():
    node = _FakeNode()
    worker = _worker_with_nodes({"vision_sequence": node})

    ok, error = asyncio.run(worker._write_checked("vision_sequence", 101))

    assert ok is True, error
    assert len(node.written) == 1
    sent = node.written[0]
    assert isinstance(sent, ua.Variant)
    assert sent.VariantType == ua.VariantType.UInt32
    assert sent.Value == 101


def test_vision_heartbeat_is_written_as_explicit_uint32():
    node = _FakeNode()
    worker = _worker_with_nodes({"vision_heartbeat": node})

    ok, error = asyncio.run(worker._write_checked("vision_heartbeat", 7))

    assert ok is True, error
    sent = node.written[0]
    assert isinstance(sent, ua.Variant)
    assert sent.VariantType == ua.VariantType.UInt32
    assert sent.Value == 7


@pytest.mark.parametrize(
    "name,value",
    [
        ("vision_target_x", 10.5),  # LREAL -> inferred Double, unchanged
        ("vision_ready", True),  # BOOL -> inferred Boolean, unchanged
        ("cmd_start", True),  # existing HMI command, must not be touched
        ("lr_x_cut_velocity", 175.0),  # existing Settings parameter write
    ],
)
def test_other_tags_are_written_with_the_plain_python_value_unchanged(name, value):
    """Only the two confirmed-mismatched UDINT tags get an explicit
    VariantType - everything else keeps asyncua's inferred type exactly as
    before this fix, so BOOL/Double writes and existing HMI commands are not
    affected."""
    node = _FakeNode()
    worker = _worker_with_nodes({name: node})

    ok, error = asyncio.run(worker._write_checked(name, value))

    assert ok is True, error
    assert node.written == [value]
    assert not isinstance(node.written[0], ua.Variant)


def test_server_reported_type_wins_over_python_inferred_type():
    """The 2026-09-18 bug: a plain Python float correctly infers Double, but
    the server rejected it anyway - meaning the node's real advertised type
    isn't Double. Once the server tells us it's actually Float, that's what
    must be sent, even though nothing about the Python value changed."""
    node = _FakeNode(server_variant_type=ua.VariantType.Float)
    worker = _worker_with_nodes({"lr_x_cut_velocity": node})

    ok, error = asyncio.run(worker._write_checked("lr_x_cut_velocity", 175.0))

    assert ok is True, error
    sent = node.written[0]
    assert isinstance(sent, ua.Variant)
    assert sent.VariantType == ua.VariantType.Float
    assert sent.Value == 175.0


def test_resolved_variant_type_is_cached_after_first_write():
    node = _FakeNode(server_variant_type=ua.VariantType.Float)
    worker = _worker_with_nodes({"lr_x_cut_velocity": node})

    asyncio.run(worker._write_checked("lr_x_cut_velocity", 175.0))
    asyncio.run(worker._write_checked("lr_x_cut_velocity", 180.0))
    asyncio.run(worker._write_checked("lr_x_cut_velocity", 185.0))

    assert node.type_lookup_calls == 1  # only resolved once, then cached
    assert len(node.written) == 3
    assert all(isinstance(v, ua.Variant) and v.VariantType == ua.VariantType.Float for v in node.written)


def test_type_resolution_failure_falls_back_to_plain_inferred_write():
    """If the server-type lookup itself errors (not just "unsupported"),
    the write must not be abandoned - fall back to the old inferred-type
    behavior rather than failing the write outright."""
    node = _FakeNode(type_lookup_raises=RuntimeError("BadAttributeIdInvalid"))
    worker = _worker_with_nodes({"lr_x_cut_velocity": node})

    ok, error = asyncio.run(worker._write_checked("lr_x_cut_velocity", 175.0))

    assert ok is True, error
    assert node.written == [175.0]
    assert not isinstance(node.written[0], ua.Variant)


def test_explicit_variant_types_only_covers_the_two_confirmed_udint_tags():
    assert set(EXPLICIT_VARIANT_TYPES) == {"vision_sequence", "vision_heartbeat"}
    assert all(vt == ua.VariantType.UInt32 for vt in EXPLICIT_VARIANT_TYPES.values())


def test_real_opc_ua_error_message_is_surfaced_not_swallowed():
    """The bug report's core complaint: only the tag name was shown, not
    *why* it failed. `_write_checked` must return the real exception text."""
    node = _FakeNode(raises=ua.UaStatusCodeError(0x80740000))  # BadTypeMismatch
    worker = _worker_with_nodes({"vision_sequence": node})

    ok, error = asyncio.run(worker._write_checked("vision_sequence", 42))

    assert ok is False
    assert error  # non-empty - the real reason, not just a generic label
    assert "UaStatusCodeError" in error or "0x80740000" in error or "BadTypeMismatch" in error


def test_sequential_write_failure_message_includes_the_real_reason():
    node_ok = _FakeNode()
    node_fail = _FakeNode(raises=ua.UaStatusCodeError(0x80740000))
    worker = _worker_with_nodes({"vision_target_x": node_ok, "vision_sequence": node_fail})
    results: list[tuple[bool, str]] = []
    worker.sequentialWriteResult.connect(lambda ok, msg: results.append((ok, msg)))

    async def scenario():
        worker._loop = asyncio.get_running_loop()
        worker.request_write_sequence([("vision_target_x", 1.0), ("vision_sequence", 5)])
        await asyncio.sleep(0.05)

    asyncio.run(scenario())

    assert len(results) == 1
    ok, message = results[0]
    assert ok is False
    assert "vision_sequence" in message
    assert message != "Yazma başarısız: vision_sequence"  # must carry the real reason too
