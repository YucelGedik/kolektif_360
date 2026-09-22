"""2026-09-16 (kullanıcı isteği): cross-parameter safety rules - these can
never hold at the PLC without breaking motion, so an OPC UA write must never
be attempted if they would be violated:

  lrX_CutStartPos < lrX_CutEndPos
  lrY_SoftwareMin < lrY_CenterPosition < lrY_SoftwareMax
  lrY_SoftwareMin < lrY_SoftwareMax
"""

from __future__ import annotations

import pytest

from services.machine_service import MachineService


def _demo_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    return MachineService(config_path=cfg)


def test_x_cut_start_must_stay_below_x_cut_end(tmp_path):
    svc = _demo_service(tmp_path)
    # defaults: start=0, end=3600
    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_start_pos", 4000.0)  # >= end
    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_end_pos", -10.0)  # <= start
    svc.set_parameter("lr_x_cut_start_pos", 100.0)  # still < 3600, ok
    assert svc.get_parameter_value("lr_x_cut_start_pos") == 100.0


def test_y_software_min_must_stay_below_max(tmp_path):
    svc = _demo_service(tmp_path)
    # defaults: min=-30, center=0, max=30
    with pytest.raises(ValueError):
        svc.set_parameter("lr_y_software_min", 40.0)  # >= max
    with pytest.raises(ValueError):
        svc.set_parameter("lr_y_software_max", -40.0)  # <= min


def test_y_software_min_must_stay_below_center(tmp_path):
    svc = _demo_service(tmp_path)
    with pytest.raises(ValueError):
        svc.set_parameter("lr_y_software_min", 5.0)  # >= center (0)


def test_y_software_max_must_stay_above_center(tmp_path):
    svc = _demo_service(tmp_path)
    with pytest.raises(ValueError):
        svc.set_parameter("lr_y_software_max", -5.0)  # <= center (0)


def test_y_center_must_stay_between_software_min_and_max(tmp_path):
    svc = _demo_service(tmp_path)
    with pytest.raises(ValueError):
        svc.set_parameter("lr_y_center_position", 35.0)  # >= max (30)
    with pytest.raises(ValueError):
        svc.set_parameter("lr_y_center_position", -35.0)  # <= min (-30)
    svc.set_parameter("lr_y_center_position", 10.0)  # within (-30, 30), ok
    assert svc.get_parameter_value("lr_y_center_position") == 10.0


def test_failed_cross_validation_does_not_write_to_plc(tmp_path):
    """The core requirement: validation failure must NOT reach the OPC UA
    write path at all."""
    from unittest.mock import MagicMock

    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}', encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_start_pos", 5000.0)  # invalid: >= end (3600)

    svc._worker.request_write.assert_not_called()


def test_valid_edit_still_writes_normally(tmp_path):
    from unittest.mock import MagicMock

    from core.models import ConnectionState

    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}', encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    # PLC-HMI-20260922-18 (HMI-A01): real-mode set_parameter now requires a
    # fresh, connected snapshot - mark this fixture as such.
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False

    svc.set_parameter("lr_x_cut_start_pos", 100.0)  # valid: < end (3600)

    svc._worker.request_write.assert_called_once_with("lr_x_cut_start_pos", 100.0)
