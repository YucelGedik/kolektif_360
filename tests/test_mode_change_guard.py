"""H2 (2026-09-18, kullanıcı test notu): "Otomatik mod aktifken ve perde
kesim işlemi devam ederken Manuel ekranındaki 'Manuel Modu Etkinleştir'
butonu aktif kalıyor... disable olmalı." UI tarafı (manual_page.py) butonu
görsel olarak engelliyor; bu testler asıl engelin `MachineService.
set_manual_mode` seviyesinde de olduğunu doğrular - UI dışından/gecikmeli
bir çağrı da yazı üretmemeli. Gerçek bir PLC'ye bağlanılmaz."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.models import ConnectionState
from services.machine_service import MachineService


def _demo_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    svc.snapshot.stale = False  # service.start() would normally do this
    return svc


def _real_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}', encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    return svc


def test_mode_change_allowed_when_idle_and_connected(tmp_path):
    svc = _real_service(tmp_path)

    svc.set_manual_mode(True)

    svc._worker.request_write.assert_called_once_with("manual_mode", True)


def test_mode_change_refused_while_cycle_active(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_active = True

    svc.set_manual_mode(True)

    svc._worker.request_write.assert_not_called()


def test_mode_change_refused_while_stale(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.stale = True

    svc.set_manual_mode(True)

    svc._worker.request_write.assert_not_called()


def test_mode_change_refused_while_disconnected(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.DISCONNECTED

    svc.set_manual_mode(True)

    svc._worker.request_write.assert_not_called()


def test_mode_change_refused_in_error_state(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.ERROR

    svc.set_manual_mode(True)

    svc._worker.request_write.assert_not_called()


def test_demo_mode_change_allowed_when_idle(tmp_path):
    svc = _demo_service(tmp_path)

    svc.set_manual_mode(True)

    assert svc._demo.manual_mode is True


def test_demo_mode_change_refused_while_cycle_active(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.cycle_active = True
    before = svc._demo.manual_mode

    svc.set_manual_mode(not before)

    assert svc._demo.manual_mode == before  # unchanged - refused


def test_demo_mode_change_refused_while_stale(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.stale = True
    before = svc._demo.manual_mode

    svc.set_manual_mode(not before)

    assert svc._demo.manual_mode == before
