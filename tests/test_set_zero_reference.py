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
    "x_home_done": "ns=4;s=|var|MAT LC-C07.Application.GVL.xX_HomeDone",
    "x_home_busy": "ns=4;s=|var|MAT LC-C07.Application.GVL.xX_HomeBusy",
    "x_home_error": "ns=4;s=|var|MAT LC-C07.Application.GVL.xX_HomeError",
    "x_home_error_id": "ns=4;s=|var|MAT LC-C07.Application.GVL.eX_HomeErrorID",
    "x_home_aborted": "ns=4;s=|var|MAT LC-C07.Application.GVL.xX_HomeAborted",
    "y_home_done": "ns=4;s=|var|MAT LC-C07.Application.GVL.xY_HomeDone",
    "y_home_busy": "ns=4;s=|var|MAT LC-C07.Application.GVL.xY_HomeBusy",
    "y_home_error": "ns=4;s=|var|MAT LC-C07.Application.GVL.xY_HomeError",
    "y_home_error_id": "ns=4;s=|var|MAT LC-C07.Application.GVL.eY_HomeErrorID",
    "y_home_aborted": "ns=4;s=|var|MAT LC-C07.Application.GVL.xY_HomeAborted",
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


def test_missing_tags_lists_exactly_what_is_absent(tmp_path):
    """PLC-HMI-20260923-23: `cmd_set_zero_request` gerçek PLC'de salt-okunur
    browse ile canlı doğrulandı - yalnız 10 MC_Home RO alanı Symbol
    Configuration'da yayınlanmamış (BadNodeIdUnknown). Bu senaryoyu taklit
    eder: RW var, 10 RO yok."""
    svc = _real_service(tmp_path, nodes={"cmd_set_zero_request": "ns=4;s=|var|MAT LC-C07.Application.GVL.xSetZeroRequest"})

    missing = svc.set_zero_missing_tags()

    assert "cmd_set_zero_request" not in missing
    assert len(missing) == 10
    assert "x_home_done" in missing
    assert "y_home_aborted" in missing
    assert svc.set_zero_tags_configured() is False


def test_missing_tags_empty_when_all_configured(tmp_path):
    svc = _real_service(tmp_path)  # _FULL_SET_ZERO_NODES - hepsi var
    assert svc.set_zero_missing_tags() == []


def test_missing_tags_empty_in_demo_mode(tmp_path):
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "", "nodes": {}}), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    assert svc.set_zero_missing_tags() == []


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

    # Yeniden bağlandık - eski okumaya güvenilmez, talep sıfırdan iptal
    # edilir (RequestFALSE yazılır, TRUE tekrar gönderilmez) AMA eksen HÂLÂ
    # fiziksel olarak meşgulse (kesinti sırasında PLC hareketi sürdürmüş
    # olabilir) kilit/"sent" GERÇEKTEN durana kadar açılmaz - PLC-HMI-
    # 20260923-25 (P1 düzeltme, "reconnect dalı da idle'a geçiyor" bulgusu).
    svc.snapshot.stale = False
    svc._update_set_zero_status(svc.snapshot)

    assert svc.set_zero_status() == "busy"
    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", False)
    assert svc.set_zero_reference_allowed_now() is False  # hâlâ meşgul, yeni talep engellenir

    # Eksen sonunda GERÇEKTEN durdu - kesinti sırasında sonuç belirsiz
    # kaldığı için bu deneme kesin HATA olarak kapanır (başarı sayılmaz),
    # RequestFALSE tekrar yazılmaz (zaten yazılmıştı).
    svc._worker.request_write.reset_mock()
    svc._on_raw_snapshot({"x_home_busy": False, "y_home_busy": False})

    assert svc.set_zero_status() == "error"
    svc._worker.request_write.assert_not_called()
    assert svc.set_zero_reference_allowed_now() is True


def test_result_wait_timeout_is_treated_as_error(tmp_path, monkeypatch):
    svc = _real_service(tmp_path)
    svc.request_set_zero()
    svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
    assert svc.set_zero_status() == "busy"

    svc._set_zero_sent_at = time.monotonic() - SET_ZERO_RESULT_TIMEOUT_S - 1.0
    svc._update_set_zero_status(svc.snapshot)

    # PLC-HMI-20260923-25 (P1 düzeltme, "gerçek Busy bırakılmadan modal
    # kapanabiliyor" bulgusu): zaman aşımında RequestFALSE yazılır (tekrar
    # denenmez) AMA eksen GERÇEKTEN meşgulken (combined_busy hâlâ True)
    # kilit/"sent" ASLA açılmaz - ExecuteFALSE yazmak PLC'nin fiziksel
    # olarak durduğunun kanıtı değildir.
    assert svc.set_zero_status() == "busy"
    svc._worker.request_write.assert_called_with("cmd_set_zero_request", False)
    assert svc.set_zero_reference_allowed_now() is False

    # Aynı pulse tekrar yazılmasın - hâlâ meşgul/hâlâ zaman aşımı geçmişken
    # ikinci bir tick'te tekrar FALSE yazılmamalı.
    svc._worker.request_write.reset_mock()
    svc._update_set_zero_status(svc.snapshot)
    svc._worker.request_write.assert_not_called()

    # Eksen sonunda GERÇEKTEN durdu - zaman aşımı kararı geri alınmaz,
    # sonuç kesin HATA olarak kapanır.
    svc._on_raw_snapshot({"x_home_busy": False, "y_home_busy": False})
    assert svc.set_zero_status() == "error"
    assert svc.set_zero_reference_allowed_now() is True


def test_timeout_while_never_cleared_still_resolves_as_error(tmp_path):
    """PLC-HMI-20260923-25 (P1 düzeltme, 3. istenen test - "cleared hiç
    gelmezken timeout"): gönderim ANINDA zaten kirli (bir önceki denemeden
    kalma latched Done) VE PLC hiçbir zaman Busy göstermez/latch'i
    temizlemezse, eskiden `_update_set_zero_status` "cleared" olmadan asla
    zaman aşımı KONTROLÜNE bile ulaşmıyordu (erken return ondan önceydi) -
    durum sonsuza dek "sent" kalırdı. Artık "cleared" hiç gelmese bile
    zaman aşımı işletilir; sonuç HER ZAMAN "error" (asla "done" değil -
    eski latch bir başarı olarak KABUL EDİLMEDİ, yalnızca sonsuz bekleme
    kırıldı)."""
    svc = _real_service(tmp_path)
    svc._on_raw_snapshot({"x_home_done": True, "y_home_done": True})  # önceki denemeden kalan

    svc.request_set_zero()  # gönderim anı KİRLİ - cleared=False başlar
    svc._worker.request_write.reset_mock()

    # PLC hiçbir zaman Busy göstermedi, latch'i de hiç temizlemedi -
    # "cleared" hiç tetiklenmiyor.
    svc._set_zero_sent_at = time.monotonic() - SET_ZERO_RESULT_TIMEOUT_S - 1.0
    svc._update_set_zero_status(svc.snapshot)

    assert svc.set_zero_status() == "error"
    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", False)
    assert svc.set_zero_reference_allowed_now() is True


def test_clean_start_immediate_done_on_first_read_is_accepted(tmp_path):
    """PLC-HMI-20260923-25 (P1 düzeltme, 1. istenen test - "temiz başlangıç
    -> ilk okumada ikiDone"): PLC çok hızlı tamamlarsa, iki HMI okuması
    arasında Busy hiç görülmeden doğrudan Done=True gelebilir. Gönderim
    ANINDA snapshot zaten temizse (Busy/Done/Error hiçbiri TRUE değil) bu
    doğrudan gelen Done, YENİ talebin GERÇEK sonucu olarak güvenle kabul
    edilmeli - eskiden bu senaryoda "cleared" hiç set edilmediği için
    (yalnız post-send bir Busy/all-false gözlemiyle tetiklenirdi) durum
    sonsuza dek "sent" kalır, zaman aşımı kontrolüne bile ulaşılmazdı."""
    svc = _real_service(tmp_path)
    assert svc.set_zero_status() == "idle"  # temiz başlangıç - hiç latch yok

    svc.request_set_zero()
    svc._worker.request_write.reset_mock()

    # Busy HİÇ görülmedi - PLC doğrudan Done ile geldi.
    svc._on_raw_snapshot({"x_home_busy": False, "y_home_busy": False, "x_home_done": True, "y_home_done": True})

    assert svc.set_zero_status() == "done"
    svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", False)
    assert svc.set_zero_reference_allowed_now() is True


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
