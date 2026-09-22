"""Faz 4 (2026-09-16): PARAMETER_SPECS must match the real PLC parameter
list the user confirmed against GVL/Logic_Control - no more, no less, and
none of the old fictional `par_*` keys."""

from __future__ import annotations

from core.parameters import PARAMETER_SPECS

EXPECTED_KEYS = {
    "lr_x_cut_velocity",
    "lr_x_cut_acc_dec",
    "lr_x_return_velocity",
    "lr_x_return_acc_dec",
    "lr_x_cut_start_pos",
    "lr_x_cut_end_pos",
    "lr_y_center_position",
    "lr_y_software_min",
    "lr_y_software_max",
    "lr_y_move_velocity",
    "lr_y_move_acc_dec",
    "lr_y_max_velocity",
    "lr_x_jog_velocity",
    "lr_y_jog_velocity",
    "lr_jog_acc_dec",
    "t_vision_heartbeat_timeout",
}


def test_parameter_specs_match_confirmed_real_tag_list():
    keys = {spec.key for spec in PARAMETER_SPECS}
    assert keys == EXPECTED_KEYS


def test_no_fictional_par_prefixed_keys_remain():
    assert not any(spec.key.startswith("par_") for spec in PARAMETER_SPECS)


def test_removed_fields_are_gone():
    labels = {spec.label_tr for spec in PARAMETER_SPECS}
    assert "X İvme" not in labels
    assert "X Yavaşlama" not in labels
    assert "Vision Zaman Aşımı" not in labels


def test_y_max_hiz_renamed_to_follow_maks_hizi():
    labels = {spec.label_tr for spec in PARAMETER_SPECS}
    assert "Y Max Hız" not in labels
    assert "Y Follow Maks. Hızı" in labels


def test_default_never_clamped_by_its_own_range():
    """Real-PLC bug (2026-09-16): Y Yazılım Max's range was guessed too
    narrow (0..24) for the real PLC default (30), so QDoubleSpinBox silently
    clamped a correctly-read value on screen. Guard every spec so this class
    of bug cannot silently return."""
    for spec in PARAMETER_SPECS:
        assert spec.min_value <= spec.default <= spec.max_value, (
            f"{spec.key}: default {spec.default} outside range "
            f"[{spec.min_value}, {spec.max_value}] - Qt will clamp the display"
        )


REAL_PLC_DEFAULTS = {
    "lr_x_cut_velocity": 175.0,
    "lr_x_cut_acc_dec": 500.0,
    "lr_x_return_velocity": 400.0,
    "lr_x_return_acc_dec": 500.0,
    "lr_x_cut_start_pos": 0.0,
    "lr_x_cut_end_pos": 3600.0,
    "lr_y_center_position": 0.0,
    "lr_y_software_min": -30.0,
    "lr_y_software_max": 30.0,
    "lr_y_move_velocity": 10.0,
    "lr_y_move_acc_dec": 100.0,
    "lr_y_max_velocity": 5.0,
    "lr_x_jog_velocity": 50.0,
    "lr_y_jog_velocity": 5.0,
    "lr_jog_acc_dec": 100.0,
    "t_vision_heartbeat_timeout": 2000.0,
}


def test_defaults_match_real_plc_values_user_confirmed():
    for spec in PARAMETER_SPECS:
        assert spec.default == REAL_PLC_DEFAULTS[spec.key], (
            f"{spec.key}: default {spec.default} != real PLC value "
            f"{REAL_PLC_DEFAULTS[spec.key]} (2026-09-16 confirmation)"
        )


# 2026-09-22 (kullanıcı isteği): "HIZ SINIRLARINI BU ŞEKİLDE REVİZE ET
# MEKANİĞE BAĞLANDIK VE BU SINIRLARA KARAR VERDİK" - gerçek, onaylanmış
# mekanik hız limitleri (tahmin değil).
CONFIRMED_MECHANICAL_VELOCITY_LIMITS = {
    "lr_x_cut_velocity": (1.0, 800.0),
    "lr_x_return_velocity": (1.0, 1060.0),
    "lr_y_move_velocity": (1.0, 50.0),
    "lr_y_max_velocity": (1.0, 50.0),
    "lr_x_jog_velocity": (1.0, 400.0),
    "lr_y_jog_velocity": (1.0, 50.0),
}


def test_velocity_ranges_match_confirmed_mechanical_limits():
    specs = {spec.key: spec for spec in PARAMETER_SPECS}
    for key, (min_value, max_value) in CONFIRMED_MECHANICAL_VELOCITY_LIMITS.items():
        spec = specs[key]
        assert (spec.min_value, spec.max_value) == (min_value, max_value), (
            f"{key}: [{spec.min_value}, {spec.max_value}] != confirmed "
            f"mechanical [{min_value}, {max_value}] (2026-09-22)"
        )
