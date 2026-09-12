from core.cycle_state import CycleState, cycle_state_label


def test_known_state_has_turkish_label():
    assert cycle_state_label(int(CycleState.CUTTING)) == "Kesim"


def test_unknown_state_degrades_gracefully():
    assert "Bilinmeyen" in cycle_state_label(9999)


def test_all_enum_members_have_labels():
    for state in CycleState:
        label = cycle_state_label(int(state))
        assert label and "Bilinmeyen" not in label
