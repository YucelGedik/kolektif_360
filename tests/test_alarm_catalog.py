"""PLC-HMI-20260921-16 (C6.1 Hata/Uyarı/Mesaj kataloğu): HATA sınıfı
bildirimlerin PLC'nin kendi latched bitlerinden üretilmesi -
`MachineService._update_alarm_conditions`. Kaynakta bulunan gerçek hata da
burada kilitlenir: Reset TIKLAMASI aktif alarmı temizlemez, yalnızca PLC'nin
kendi okuması FALSE'a dönünce temizlenir. İzole `tmp_path` DB kullanılır -
`data/bufera.db` PAYLAŞIMLI (bilinen sınırlama, test_alarm_severity.py'deki
aynı desen)."""

from __future__ import annotations

import contextlib
import json
from unittest.mock import MagicMock

import persistence.db as db_module
from core.cycle_state import CycleState
from persistence.alarms import SEVERITY_ALARM, SEVERITY_MESSAGE, SEVERITY_WARNING
from services.machine_service import MachineService


@contextlib.contextmanager
def _isolated_engine(tmp_path):
    db_module.init_engine(tmp_path / "test_alarm_catalog.db")
    try:
        yield
    finally:
        db_module.init_engine()  # varsayılan data/bufera.db'ye geri dön


def _real_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        json.dumps({"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}), encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    return svc


def test_rising_edge_logs_one_alarm_event(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)

        svc._on_raw_snapshot({"move_to_start_error": True})

        active = [e for e in svc._alarms.recent() if e.active]
        assert len(active) == 1
        assert active[0].severity == SEVERITY_ALARM
        assert active[0].source == "X AXIS"
        assert "Başlangıç konumuna dönüş sırasında arıza oluştu" in active[0].message
        assert svc.active_alarm_count() == 1


def test_condition_staying_true_does_not_duplicate(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)

        svc._on_raw_snapshot({"x_power_error": True})
        svc._on_raw_snapshot({"x_power_error": True})
        svc._on_raw_snapshot({"x_power_error": True})

        assert svc.active_alarm_count() == 1


def test_first_read_already_true_is_still_logged(tmp_path):
    """"İlk okuma TRUE aktif listede görünmeli" (görev notu) - reconnect
    sonrası bir arızanın zaten aktif olduğu ilk okumada da kaybolmamalı."""
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)

        svc._on_raw_snapshot({"vision_fault": True})

        assert svc.active_alarm_count() == 1


def test_falling_edge_clears_the_specific_event_without_reset(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        svc._on_raw_snapshot({"y_power_error": True})
        assert svc.active_alarm_count() == 1

        svc._on_raw_snapshot({"y_power_error": False})

        assert svc.active_alarm_count() == 0
        # Geçmişte kalmalı - `clear_event` yalnız `cleared_at`'ı ayarlar, satırı silmez.
        assert len(svc._alarms.recent()) == 1


def test_reset_click_does_not_clear_active_alarm_only_plc_readback_does(tmp_path):
    """PLC-HMI-20260921-16 bulgusu, gerçek bug fix: eskiden `request_reset()`
    gerçek modda pulse gönderir göndermez `_alarms.clear_active()` çağırıyordu
    - Reset PLC tarafından kabul edilmeden aktif hata ekrandan kayboluyordu."""
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        svc._on_raw_snapshot({"alarm_clamp_lost_during_cut": True})
        assert svc.active_alarm_count() == 1

        svc.request_reset()  # yalnız cmd_reset pulse'u gönderir

        assert svc.active_alarm_count() == 1  # HÂLÂ aktif - Reset tek başına temizlemez

        # PLC gerçekten kabul edip biti FALSE'a çekince (xAlarmResetAccepted
        # sonrası) ancak o zaman temizlenir.
        svc._on_raw_snapshot({"alarm_clamp_lost_during_cut": False})

        assert svc.active_alarm_count() == 0


def test_multiple_simultaneous_conditions_all_listed(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)

        svc._on_raw_snapshot({"alarm_blade_lost_during_cut": True, "y_move_error": True})

        assert svc.active_alarm_count() == 2


def test_inverted_condition_h16_emergency_ok_false(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        assert svc.snapshot.emergency_ok is True  # varsayılan "sağlıklı"

        svc._on_raw_snapshot({"emergency_ok": False})

        active = [e for e in svc._alarms.recent() if e.active]
        assert len(active) == 1
        assert "Emniyet geri bildirimi yok" in active[0].message

        svc._on_raw_snapshot({"emergency_ok": True})
        assert svc.active_alarm_count() == 0


def test_h19_fallback_when_fault_with_no_known_cause(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)

        svc._on_raw_snapshot({"cycle_state": int(CycleState.FAULT)})

        active = [e for e in svc._alarms.recent() if e.active]
        assert len(active) == 1
        assert "ayrıntılı neden bilgisi mevcut değil" in active[0].message


def test_h19_not_logged_when_a_known_cause_is_also_active(tmp_path):
    """Bilinen bir HATA (örn. H06) zaten FAULT'un nedenini açıklıyorsa H19
    jenerik yedek AYRICA sayılmaz - sahte/çift bir "bilinmiyor" olmaz."""
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)

        svc._on_raw_snapshot({"cycle_state": int(CycleState.FAULT), "x_power_error": True})

        active = [e for e in svc._alarms.recent() if e.active]
        assert len(active) == 1
        assert "X servo etkinleştirme hatası" in active[0].message


def test_h19_clears_when_leaving_fault(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        svc._on_raw_snapshot({"cycle_state": int(CycleState.FAULT)})
        assert svc.active_alarm_count() == 1

        svc._on_raw_snapshot({"cycle_state": int(CycleState.MANUAL)})

        assert svc.active_alarm_count() == 0


H20_H22_CASES = [
    ("alarm_mode_changed_during_cycle", "PLC", "mod değiştirme talebi alındı"),
    ("alarm_clamp_lost_during_cycle", "PNEUMATIC", "baskı aşağı sensörü kayboldu"),
    ("alarm_blade_not_clear_during_return", "PNEUMATIC", "bıçak açıklığı kayboldu"),
]


def test_h20_h22_initial_true_rising_falling_and_history(tmp_path):
    """PLC-HMI-20260922-17 offline test isteği: 3 yeni aday HATA (H20-H22)
    için initial TRUE / rising / falling / history aynı desende çalışmalı -
    henüz gerçek config'te eşleme yok ama motor mantığı önceden doğrulanabilir."""
    with _isolated_engine(tmp_path):
        for index, (attr, source, fragment) in enumerate(H20_H22_CASES, start=1):
            svc = _real_service(tmp_path)

            # İlk okuma zaten TRUE ise yine kaybolmadan loglanmalı.
            svc._on_raw_snapshot({attr: True})
            active = [e for e in svc._alarms.recent() if e.active]
            assert len(active) == 1
            assert active[0].source == source
            assert fragment in active[0].message

            # Falling edge - PLC'nin kendi okuması FALSE'a dönünce kapanır.
            svc._on_raw_snapshot({attr: False})
            assert svc.active_alarm_count() == 0
            # Geçmişte kalmalı (silinmez, yalnız cleared_at set edilir) -
            # `_isolated_engine` bu döngü boyunca paylaşıldığı için toplam
            # geçmiş kayıt sayısı kümülatif artar.
            assert len(svc._alarms.recent()) == index


def test_h20_h22_reset_click_does_not_clear_only_plc_readback_does(tmp_path):
    with _isolated_engine(tmp_path):
        for attr, _source, _fragment in H20_H22_CASES:
            svc = _real_service(tmp_path)
            svc._on_raw_snapshot({attr: True})
            assert svc.active_alarm_count() == 1

            svc.request_reset()

            assert svc.active_alarm_count() == 1  # Reset tek başına temizlemez

            svc._on_raw_snapshot({attr: False})
            assert svc.active_alarm_count() == 0


def test_active_alarm_count_ignores_warning_and_message_severity(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        svc._alarms.log_event(SEVERITY_WARNING, "Y AXIS", "bir uyarı")
        svc._alarms.log_event(SEVERITY_MESSAGE, "PLC", "bir mesaj")

        assert svc.active_alarm_count() == 0

        svc._on_raw_snapshot({"trajectory_fault": True})

        assert svc.active_alarm_count() == 1
