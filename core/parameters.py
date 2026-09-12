"""Engineering parameter definitions for the Settings screen (brief section 8,
13, 24). Ranges below are placeholders — final mechanical limits are still
open per brief section 28 and must be tightened once known; nothing here is
hard-coded into the UI layer, it all flows through this single list."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    key: str  # matches the "par_*" tag name in config/opcua.json
    label_tr: str
    unit: str
    default: float
    min_value: float
    max_value: float


PARAMETER_SPECS: list[ParameterSpec] = [
    ParameterSpec("par_x_cut_velocity", "X Kesim Hızı", "mm/s", 175.0, 1.0, 500.0),
    ParameterSpec("par_x_return_velocity", "X Dönüş Hızı", "mm/s", 400.0, 1.0, 800.0),
    ParameterSpec("par_x_acceleration", "X İvme", "mm/s²", 2000.0, 1.0, 10000.0),
    ParameterSpec("par_x_deceleration", "X Yavaşlama", "mm/s²", 2000.0, 1.0, 10000.0),
    ParameterSpec("par_x_cut_start_pos", "X Kesim Başlangıç", "mm", 0.0, 0.0, 3600.0),
    ParameterSpec("par_x_cut_end_pos", "X Kesim Bitiş", "mm", 3600.0, 0.0, 3600.0),
    ParameterSpec("par_y_center_pos", "Y Merkez Konum", "mm", 0.0, -50.0, 50.0),
    ParameterSpec("par_y_software_min", "Y Yazılım Min", "mm", -30.0, -100.0, 0.0),
    ParameterSpec("par_y_software_max", "Y Yazılım Max", "mm", 30.0, 0.0, 100.0),
    ParameterSpec("par_y_max_velocity", "Y Max Hız", "mm/s", 50.0, 1.0, 200.0),
    ParameterSpec("par_vision_timeout_ms", "Vision Zaman Aşımı", "ms", 500.0, 10.0, 10000.0),
    ParameterSpec("par_heartbeat_timeout_ms", "Heartbeat Zaman Aşımı", "ms", 500.0, 10.0, 10000.0),
    ParameterSpec("par_clamp_down_delay_ms", "Baskı Aşağı Gecikmesi", "ms", 300.0, 0.0, 5000.0),
    ParameterSpec("par_clamp_up_delay_ms", "Baskı Yukarı Gecikmesi", "ms", 300.0, 0.0, 5000.0),
    ParameterSpec("par_blade_down_delay_ms", "Bıçak Aşağı Gecikmesi", "ms", 300.0, 0.0, 5000.0),
    ParameterSpec("par_blade_up_delay_ms", "Bıçak Yukarı Gecikmesi", "ms", 300.0, 0.0, 5000.0),
]
