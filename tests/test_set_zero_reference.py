"""PLC-HMI-20260923-20 (C8, "Sıfır Referansı Belirle", sade sürüm): mevcut
X/Y fiziksel konumunu 0 yapan, tek RW (`xSetZeroRequest`, LEVEL) + mevcut
MC_Home_X/MC_Home_Y FB'lerinin 5+5 RO üyesiyle çalışan akış. Bu modül yalnız
`MachineService`'in mantığını (izin, gönderim, readback edge-detection,
bağlantı kaybı, zaman aşımı) izole test eder - gerçek PLC'ye bağlanılmaz.
UI tarafındaki 3 saniyelik gerçek-zaman sayaç davranışı `test_set_zero_
dialog.py`'de, widget smoke testiyle doğrulanır."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

import pytest

from core.models import ConnectionState
from services.machine_service import SET_ZERO_RESULT_TIMEOUT_S, MachineService

MANUAL = 10  # CycleState.MANUAL
CUTTING = 80  # CycleState.CUTTING, an AUTO_CYCLE_ACTIVE_STATE

_FULL_SET_ZERO_NODES = {
    "cmd_set_zero_request": "ns=4;s=|var|MAT LC-C07.Application.GVL.xSetZeroRequest",
    "x_home_done": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.Done",
    "x_home_busy": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.Busy",
    "x_home_error": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.Error",
    "x_home_error_id": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.ErrorID",
    "x_home_aborted": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.CommandAborted",
    "y_home_done": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.Done",
    "y_home_busy": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.Busy",
    "y_home_error": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.Error",
    "y_home_error_id": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.ErrorID",
    "y_home_aborted": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.CommandAborted",
}


def _real_service(tmp_path, nodes: dict | None = None) -> MachineService:
    cfg = tmp_path / "opcua.json"
    config = {
        "endpoint": "opc.tcp://192.168.0.2:4840",
        "nodes": dict(_FULL_SET_ZERO_NODES) if nodes is None else nodes,
    }
    cfg.write_text(json.dumps(config), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = MANUAL
    svc.snapshot.emergency_ok = True
    svc.snapshot.x_servo_ready = True
    svc.snapshot.y_servo_ready = True
    svc.snapshot.blade_down = False
    svc.snapshot.clamp_down = False
    return svc


# -- tags-not-configured guard (C0.4/C5 disiplini) ---------------------------


def test_tags_not_configured_blocks_button_and_request(tmp_path):
    svc = _real_service(tmp_path, nodes={})

    assert svc.set_zero_tags_configured() is False
    assert svc.set_zero_reference_allowed_now() is False
    assert svc.request_set_zero() is False
    svc._worker.request_write.assert_not_called()


def test_demo_mode_ignores_tags_configured(tmp_path):
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "", "nodes": {}}), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    assert svc.demo_mode is True

    assert svc.set_zero_tags_configured() is True


# -- C8-S03: koşullar sağlanmazsa başlamaz -----------------------------------


def test_denied_when_stale(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.stale = True
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_when_disconnected(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.DISCONNECTED
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_outside_manual_cycle_state(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_state = CUTTING
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_when_not_manual_mode(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = False
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_when_emergency_not_ok(tmp_path):
    """"EMG basılı" - xEmergencyOK henüz TRUE değil (görev notu C8-S03)."""
    svc = _real_service(tmp_path)
    svc.snapshot.emergency_ok = False
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_when_servo_not_ready(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.x_servo_ready = False
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_when_blade_down(tmp_path):
    """"mekanizmaların yukarıda olduğu" ön koşulu."""
    svc = _real_service(tmp_path)
    svc.snapshot.blade_down = True
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_when_clamp_down(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.clamp_down = True
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_while_axis_moving(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.x_actual_vel = 5.0
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_while_jog_active(tmp_path):
    """C8-S03: "Fiziksel besleme/jog talebi ile aynı anda referans kabul
    edilmez." Jog aktifken sıfırlama başlamaz."""
    svc = _real_service(tmp_path)
    svc._jog_x_active = True
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_while_cycle_active(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_active = True
    assert svc.set_zero_reference_allowed_now() is False


def test_denied_while_move_to_start_busy(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.move_to_start_busy = True
    assert svc.set_zero_reference_allowed_now() is False


def test_request_refused_and_nothing_written_when_conditions_not_met(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = False

    assert svc.request_set_zero() is False
    svc._worker.request_write.assert_not_called()
    assert svc.set_zero_status() == "idle"


# -- C8-S05: jog/besleme kilidi Request/Busy sürerken --------------------


def test_jog_locked_while_set_zero_sent(tmp_path):
    svc = _real_service(tmp_path)
    assert svc.request_set_zero() is True

    svc.jog_x(1, True)

    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", True)


# -- gönderim + C8-S04: doğru sırayla başarı ---------------------------------


def test_request_writes_true_and_tracks_sent(tmp_path):
    svc = _real_service(tmp_path)

    assert svc.request_set_zero() is True

    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", True)
    assert svc.set_zero_status() == "sent"
    assert svc.set_zero_reference_allowed_now() is False  # zaten gönderilmiş


def test_busy_then_both_done_is_success_and_releases_request(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_set_zero()

    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
    assert svc.set_zero_status() == "busy"

    svc._on_raw_snapshot(
        {
            "x_home_busy": False,
            "y_home_busy": False,
            "x_home_done": True,
            "y_home_done": True,
        }
    )

    assert svc.set_zero_status() == "done"
    svc._worker.request_write.assert_called_with("cmd_set_zero_request", False)
    assert svc.set_zero_reference_allowed_now() is True  # sent artık False


def test_single_axis_success_is_not_accepted_as_success(tmp_path):
    """"Tek eksen başarılı olursa iki eksen başarı kabul edilmez" (görev notu)."""
    svc = _real_service(tmp_path)
    svc.request_set_zero()
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})

    svc._on_raw_snapshot(
        {
            "x_home_busy": False,
            "y_home_busy": False,
            "x_home_done": True,
            "y_home_done": False,
            "y_home_error": True,
        }
    )

    assert svc.set_zero_status() == "error"


def test_error_writes_false_and_releases(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_set_zero()
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})

    svc._on_raw_snapshot(
        {"x_home_busy": False, "y_home_busy": False, "x_home_error": True, "x_home_error_id": 42}
    )

    assert svc.set_zero_status() == "error"
    assert svc.snapshot.x_home_error_id == 42
    svc._worker.request_write.assert_called_with("cmd_set_zero_request", False)


def test_command_aborted_counts_as_error(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_set_zero()
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})

    svc._on_raw_snapshot({"x_home_busy": False, "y_home_busy": False, "y_home_aborted": True})

    assert svc.set_zero_status() == "error"


# -- C8-S05: eski Done yeni sonuç sayılmaz ("cleared" deseni) ----------------


def test_stale_done_from_a_previous_attempt_is_not_counted_as_new_result(tmp_path):
    """Bir önceki denemeden kalan Done latched TRUE iken yeni bir talep
    gönderilirse, PLC henüz Busy TRUE göstermeden o eski Done yeni bu
    denemenin sonucu SAYILMAMALI - C5'teki aynı bug fix'in C8 karşılığı."""
    svc = _real_service(tmp_path)
    svc._on_raw_snapshot({"x_home_done": True, "y_home_done": True})  # önceki denemeden kalan

    svc.request_set_zero()
    # Henüz Busy TRUE görülmedi VE Done hâlâ TRUE - "cleared" olmamalı,
    # dolayısıyla bu eski Done okuması "done" saymamalı.
    svc._on_raw_snapshot({"x_home_done": True, "y_home_done": True})

    assert svc.set_zero_status() == "sent"
    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", True)  # FALSE hiç yazılmadı

    # Şimdi PLC gerçekten yeni bir Busy okur (eski latch temizlendi) - artık takip edilir.
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True, "x_home_done": False, "y_home_done": False})
    assert svc.set_zero_status() == "busy"

    svc._on_raw_snapshot({"x_home_busy": False, "y_home_busy": False, "x_home_done": True, "y_home_done": True})
    assert svc.set_zero_status() == "done"


def test_all_three_false_also_counts_as_cleared(tmp_path):
    svc = _real_service(tmp_path)
    svc._on_raw_snapshot({"x_home_error": True})  # eski hata

    svc.request_set_zero()
    # Busy hiç görülmeden üçü de (Done/Error/Aborted) FALSE - eski latch
    # zaten temizlenmiş demektir, "cleared" sayılabilir.
    svc._on_raw_snapshot({"x_home_error": False})

    svc._on_raw_snapshot({"x_home_done": True, "y_home_done": True})
    assert svc.set_zero_status() == "done"


# -- C8-S05: bağlantı kaybı / zaman aşımı ------------------------------------


def test_connection_loss_while_pending_does_not_claim_success_or_resend(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_set_zero()
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
    assert svc.set_zero_status() == "busy"
    svc._worker.request_write.reset_mock()

    svc.snapshot.stale = True
    svc._update_set_zero_status(svc.snapshot)  # gerçek modda tick bunu çağırır

    assert svc.set_zero_status() == "busy"  # donmuş durum - ne done ne error
    svc._worker.request_write.assert_not_called()  # TRUE tekrar gönderilmedi

    # Yeniden bağlandık - eski okumaya güvenilmez, talep sıfırdan iptal edilir.
    svc.snapshot.stale = False
    svc._update_set_zero_status(svc.snapshot)

    assert svc.set_zero_status() == "idle"
    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", False)
    assert svc.set_zero_reference_allowed_now() is True


def test_result_wait_timeout_is_treated_as_error(tmp_path, monkeypatch):
    svc = _real_service(tmp_path)
    svc.request_set_zero()
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
    assert svc.set_zero_status() == "busy"

    svc._set_zero_sent_at = time.monotonic() - SET_ZERO_RESULT_TIMEOUT_S - 1.0
    svc._update_set_zero_status(svc.snapshot)

    assert svc.set_zero_status() == "error"
    svc._worker.request_write.assert_called_with("cmd_set_zero_request", False)


# -- gerçek OPC UA reddi -------------------------------------------------


def test_real_write_rejection_marks_error_and_emits_command_write_error(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_set_zero()

    errors: list[tuple[str, str]] = []
    svc.commandWriteError.connect(lambda tag, reason: errors.append((tag, reason)))

    svc._on_error("Write failed for 'cmd_set_zero_request': BadUserAccessDenied")

    assert errors == [("cmd_set_zero_request", "BadUserAccessDenied")]
    assert svc.set_zero_status() == "error"
    assert svc.set_zero_reference_allowed_now() is True  # sent artık False
