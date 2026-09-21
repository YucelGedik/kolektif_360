"""PLC-HMI-20260921-10/11 (C5): "Başlangıç Konumuna Dön" - tek buton, 3
saniye kesintisiz basılı tutuş, X+Y'yi ayarlı başlangıç konumuna götüren tek
GVL.xMoveToStartRequest pulse'u. Bu modül yalnız MachineService'in mantığını
(izin, gönderim, readback edge-detection) izole test eder - gerçek PLC'ye
bağlanılmaz (H5-HOLD-T08, fiziksel hareket testi, kullanıcının kendisi
tarafından sahada yapılır). UI tarafındaki 3 saniyelik gerçek-zaman sayaç
davranışı burada değil, widget smoke testiyle doğrulandı."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from core.models import ConnectionState
from services.machine_service import MachineService

MANUAL = 10  # CycleState.MANUAL
CUTTING = 80  # CycleState.CUTTING, an AUTO_CYCLE_ACTIVE_STATE

_FULL_MOVE_TO_START_NODES = {
    "cmd_move_to_start": "ns=4;s=|var|MAT LC-C07.Application.GVL.xMoveToStartRequest",
    "move_to_start_allowed": "ns=4;s=|var|MAT LC-C07.Application.GVL.xMoveToStartAllowed",
    "move_to_start_busy": "ns=4;s=|var|MAT LC-C07.Application.GVL.xMoveToStartBusy",
    "move_to_start_done": "ns=4;s=|var|MAT LC-C07.Application.GVL.xMoveToStartDone",
    "move_to_start_aborted": "ns=4;s=|var|MAT LC-C07.Application.GVL.xMoveToStartAborted",
    "move_to_start_error": "ns=4;s=|var|MAT LC-C07.Application.GVL.xMoveToStartError",
}


def _real_service(tmp_path, nodes: dict | None = None) -> MachineService:
    cfg = tmp_path / "opcua.json"
    config = {
        "endpoint": "opc.tcp://192.168.0.2:4840",
        "nodes": dict(_FULL_MOVE_TO_START_NODES) if nodes is None else nodes,
    }
    cfg.write_text(json.dumps(config), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = MANUAL
    svc.snapshot.move_to_start_allowed = True
    svc.snapshot.move_to_start_busy = False
    return svc


def _demo_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    svc.snapshot.stale = False
    return svc


# -- T06: Allowed=FALSE or Busy=TRUE -> no timer/request, Stop stays usable -


def test_allowed_now_true_by_default(tmp_path):
    svc = _real_service(tmp_path)
    assert svc.move_to_start_allowed_now() is True


def test_allowed_now_false_when_plc_allowed_is_false(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_allowed = False
    assert svc.move_to_start_allowed_now() is False


def test_allowed_now_false_while_busy(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = True
    assert svc.move_to_start_allowed_now() is False


def test_allowed_now_false_when_stale(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.stale = True
    assert svc.move_to_start_allowed_now() is False


def test_allowed_now_false_when_disconnected(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.DISCONNECTED
    assert svc.move_to_start_allowed_now() is False


def test_request_refused_when_not_allowed_stop_unaffected(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = True
    assert svc.request_move_to_start() is False
    svc._worker.request_pulse.assert_not_called()
    # Stop must stay usable regardless (görev notu: "Stop açık").
    svc.request_stop()
    svc._worker.request_pulse.assert_called_once_with("cmd_stop")


# -- Eksik tag varken buton etkinleşmez/göndermez ----------------------------


def test_refused_when_pulse_tag_not_configured(tmp_path):
    nodes = dict(_FULL_MOVE_TO_START_NODES)
    del nodes["cmd_move_to_start"]
    svc = _real_service(tmp_path, nodes=nodes)
    assert svc.move_to_start_tags_configured() is False
    assert svc.move_to_start_allowed_now() is False
    assert svc.request_move_to_start() is False
    svc._worker.request_pulse.assert_not_called()


def test_refused_when_a_readback_tag_not_configured(tmp_path):
    nodes = dict(_FULL_MOVE_TO_START_NODES)
    del nodes["move_to_start_done"]
    svc = _real_service(tmp_path, nodes=nodes)
    assert svc.move_to_start_allowed_now() is False


# -- Gönderim + gerçek pulse ---------------------------------------------------


def test_request_move_to_start_pulses_the_tag_when_allowed(tmp_path):
    svc = _real_service(tmp_path)
    assert svc.request_move_to_start() is True
    svc._worker.request_pulse.assert_called_once_with("cmd_move_to_start")
    assert svc.move_to_start_status() == "sent"


# -- T07 / belirsizse tamamlandı iddia etme: stale latched Done/Aborted -----


def test_stale_latched_done_from_a_previous_move_is_not_claimed_as_new(tmp_path):
    """Önceki başarılı harekette Done zaten TRUE kalmış (latched). Yeni pulse
    gönderildikten HEMEN sonra gelen bir okuma hâlâ o eski True'yu taşıyorsa,
    bu YENİ isteğin sonucu sayılmamalı."""
    svc = _real_service(tmp_path)
    svc.request_move_to_start()

    # Stale: hâlâ eski Done=True, PLC henüz temizlemedi.
    svc._on_raw_snapshot({"move_to_start_done": True})
    assert svc.move_to_start_status() == "sent"  # "done" DEĞİL

    # PLC şimdi gerçekten temizledi (üçü de False) - bundan sonrası güvenilir.
    svc._on_raw_snapshot({"move_to_start_done": False, "move_to_start_aborted": False, "move_to_start_error": False})
    assert svc.move_to_start_status() == "sent"

    svc._on_raw_snapshot({"move_to_start_done": True})
    assert svc.move_to_start_status() == "done"


def test_busy_transition_is_always_trusted_as_fresh(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_move_to_start()

    svc._on_raw_snapshot({"move_to_start_busy": True})
    assert svc.move_to_start_status() == "busy"

    svc._on_raw_snapshot({"move_to_start_busy": False, "move_to_start_done": True})
    assert svc.move_to_start_status() == "done"


def test_already_at_target_fast_completion_without_observed_busy(tmp_path):
    """Zaten hedefteyse Busy hiç TRUE görünmeyebilir (görev notu: "hızlı
    zaten-hedefte tamamlanma durumunu da test et") - done/aborted/error'ın
    hepsi FALSE görülen an itibarıyla sonraki bir Done=True yine de kabul
    edilmeli, Busy'yi beklemeye gerek yok."""
    svc = _real_service(tmp_path)
    svc.request_move_to_start()

    svc._on_raw_snapshot({"move_to_start_done": False, "move_to_start_aborted": False, "move_to_start_error": False})
    svc._on_raw_snapshot({"move_to_start_done": True})

    assert svc.move_to_start_status() == "done"


def test_aborted_result_tracked(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_move_to_start()
    svc._on_raw_snapshot({"move_to_start_done": False, "move_to_start_aborted": False, "move_to_start_error": False})
    svc._on_raw_snapshot({"move_to_start_aborted": True})
    assert svc.move_to_start_status() == "aborted"


def test_error_result_tracked(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_move_to_start()
    svc._on_raw_snapshot({"move_to_start_done": False, "move_to_start_aborted": False, "move_to_start_error": False})
    svc._on_raw_snapshot({"move_to_start_error": True})
    assert svc.move_to_start_status() == "error"


def test_idle_before_any_request(tmp_path):
    svc = _real_service(tmp_path)
    assert svc.move_to_start_status() == "idle"


# -- Gerçek OPC UA yazma reddi -> "error", sonsuza dek "sent" asılı kalmaz --


def test_real_write_rejection_surfaces_as_command_write_error_and_error_status(tmp_path):
    svc = _real_service(tmp_path)
    received: list[tuple[str, str]] = []
    svc.commandWriteError.connect(lambda tag, reason: received.append((tag, reason)))

    svc.request_move_to_start()
    assert svc.move_to_start_status() == "sent"

    svc._on_error("Write failed for 'cmd_move_to_start': BadNodeIdUnknown")

    assert received == [("cmd_move_to_start", "BadNodeIdUnknown")]
    assert svc.move_to_start_status() == "error"


# -- Busy'de hareket/mod/pnömatik/ayar AYRICA kilitli, xCycleActive değil ---


def test_jog_locked_while_move_to_start_busy_even_though_cycle_active_is_false(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = True
    svc.snapshot.cycle_active = False  # görev notu: bu hareket bir "cycle" değil

    svc.jog_x(1, True)

    svc._worker.request_write.assert_not_called()


def test_mode_change_locked_while_move_to_start_busy(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = True
    svc.snapshot.cycle_active = False

    svc.set_manual_mode(False)

    svc._worker.request_write.assert_not_called()


def test_pneumatic_locked_while_move_to_start_busy(tmp_path):
    nodes = dict(_FULL_MOVE_TO_START_NODES)
    nodes.update(
        {
            "cmd_blade_retract": "ns=4;s=x",
        }
    )
    svc = _real_service(tmp_path, nodes=nodes)
    svc.snapshot.move_to_start_busy = True

    assert svc.manual_pneumatic_allowed() is False
    svc.request_blade_retract()
    svc._worker.request_pulse.assert_not_called()


def test_settings_write_locked_while_move_to_start_busy(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = True

    try:
        svc.set_parameter("lr_x_cut_velocity", 100.0)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Başlangıç konumuna dönüş" in str(exc)
    svc._worker.request_write.assert_not_called()


def test_settings_write_allowed_when_not_busy(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = False

    svc.set_parameter("lr_x_cut_velocity", 100.0)

    svc._worker.request_write.assert_called_once()


# -- Demo mode -----------------------------------------------------------------


def test_demo_move_to_start_allowed_by_default(tmp_path):
    svc = _demo_service(tmp_path)
    svc._on_tick()  # let _apply_move_to_start compute Allowed for the first time
    assert svc.snapshot.move_to_start_allowed is True  # both mechanisms up, manual, idle


def test_demo_move_to_start_completes_and_moves_axes(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.x_actual_pos = 999.0
    svc.snapshot.y_actual_pos = -999.0
    svc._on_tick()  # let _apply_move_to_start compute Allowed for the first time

    assert svc.request_move_to_start() is True
    svc._on_tick()  # process the request flag into Busy=True
    assert svc.snapshot.move_to_start_busy is True

    for _ in range(50):  # advance past MOVE_TO_START_DURATION_S
        svc._on_tick()
        if svc.snapshot.move_to_start_done:
            break

    assert svc.snapshot.move_to_start_busy is False
    assert svc.snapshot.move_to_start_done is True
    assert svc.snapshot.x_actual_pos == svc._demo.params["lr_x_cut_start_pos"]
    assert svc.snapshot.y_actual_pos == svc._demo.params["lr_y_center_position"]
    assert svc.move_to_start_status() == "done"


def test_demo_move_to_start_refused_while_a_mechanism_is_down(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.blade_up = False
    svc._on_tick()  # let _apply_move_to_start recompute Allowed

    assert svc.snapshot.move_to_start_allowed is False
    assert svc.request_move_to_start() is False
