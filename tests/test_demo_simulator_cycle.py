"""Regression tests for the demo/simulation state flow, updated per the
2026-09-16 correction pass:

- MANUAL is only ever shown while manual_mode is True; the auto-mode resting
  state is WAIT_FOR_MATERIAL.
- Normal STOP: STOPPING -> BLADE_UP -> RETURN_AXES -> CLAMP_UP ->
  CYCLE_COMPLETE -> WAIT_FOR_MATERIAL (no RECOVERY).
- Fault reset: FAULT -> RECOVERY -> BLADE_UP -> RETURN_AXES -> CLAMP_UP ->
  CYCLE_COMPLETE -> WAIT_FOR_MATERIAL (RECOVERY only after a fault).
"""

from __future__ import annotations

from core.cycle_state import AUTO_CYCLE_ACTIVE_STATES, CycleState
from core.models import MachineSnapshot
from services.demo_simulator import DemoSimulator


class _NoopAlarms:
    def raise_alarm(self, code, source):
        raise AssertionError("no alarm expected in this scenario")

    def active_count(self):
        return 0

    def clear_active(self):
        return 0


class _FakeAlarms:
    """Permissive stand-in for tests that deliberately trigger a fault."""

    def raise_alarm(self, code, source):
        return None

    def active_count(self):
        return 1

    def clear_active(self):
        return 1


def _auto_ready(sim: DemoSimulator, snap: MachineSnapshot) -> None:
    """Switch to AUTO mode and let the idle state sync to WAIT_FOR_MATERIAL,
    mirroring an operator leaving MANUAL before pressing Start."""
    sim.apply_initial(snap)
    assert snap.cycle_state == int(CycleState.MANUAL)
    sim.set_mode(True)
    sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
    assert snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL)


def test_manual_state_only_shown_while_manual_mode_true():
    sim = DemoSimulator()
    snap = MachineSnapshot()
    sim.apply_initial(snap)
    assert snap.cycle_state == int(CycleState.MANUAL)

    sim.set_mode(True)  # -> auto
    sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
    assert snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL)

    sim.set_mode(False)  # -> manual again
    sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
    assert snap.cycle_state == int(CycleState.MANUAL)


def test_full_auto_cycle_reaches_completion_and_returns_to_wait_for_material():
    sim = DemoSimulator()
    snap = MachineSnapshot()
    _auto_ready(sim, snap)

    sim.request_start()
    seen_states: set[int] = set()
    left_wait = False
    # Full cycle at default params (175 mm/s cut, 3600 mm) takes ~30s
    # simulated; cap generously so a stuck transition fails fast.
    for _ in range(1400):  # 70s of simulated time at dt=0.05
        sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
        seen_states.add(snap.cycle_state)
        if snap.cycle_state != int(CycleState.WAIT_FOR_MATERIAL):
            left_wait = True
        elif left_wait:
            break
    assert left_wait, "simulator never left WAIT_FOR_MATERIAL after request_start()"

    for state in (
        CycleState.CLAMP_DOWN,
        CycleState.WAIT_VISION,
        CycleState.ALIGN_Y,
        CycleState.WAIT_BLADE_REQUEST,
        CycleState.BLADE_DOWN,
        CycleState.CUTTING,
        CycleState.BLADE_UP,
        CycleState.RETURN_AXES,
        CycleState.CLAMP_UP,
        CycleState.CYCLE_COMPLETE,
    ):
        assert int(state) in seen_states, f"{state.name} was never entered"

    assert int(CycleState.RECOVERY) not in seen_states  # normal cycle, no fault
    assert snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL)
    assert snap.cycle_active is False
    assert snap.x_actual_pos == 0.0


def test_normal_stop_skips_recovery_and_returns_to_wait_for_material():
    sim = DemoSimulator()
    snap = MachineSnapshot()
    _auto_ready(sim, snap)
    sim.request_start()

    for _ in range(200):
        sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
        if snap.cycle_state == int(CycleState.CUTTING):
            break
    assert snap.cycle_state == int(CycleState.CUTTING)

    sim.request_stop()
    seen_states: set[int] = set()
    for _ in range(400):
        sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
        seen_states.add(snap.cycle_state)
        if snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL) and int(
            CycleState.STOPPING
        ) in seen_states:
            break

    assert int(CycleState.STOPPING) in seen_states
    assert int(CycleState.BLADE_UP) in seen_states
    assert int(CycleState.RETURN_AXES) in seen_states
    assert int(CycleState.CLAMP_UP) in seen_states
    assert int(CycleState.CYCLE_COMPLETE) in seen_states
    assert int(CycleState.RECOVERY) not in seen_states, "normal STOP must not go through RECOVERY"
    assert snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL)
    assert snap.cycle_active is False


def test_fault_reset_goes_through_recovery_to_wait_for_material():
    sim = DemoSimulator()
    snap = MachineSnapshot()
    _auto_ready(sim, snap)

    # Force a fault directly (white-box) instead of waiting out the idle
    # timer - equivalent end state, much faster test.
    sim._raise_demo_alarm(snap, _FakeAlarms(), lambda: None)
    assert snap.cycle_state == int(CycleState.FAULT)

    sim.request_reset()
    seen_states: set[int] = set()
    for _ in range(200):
        sim.tick(0.05, snap, _NoopAlarms(), lambda: None)
        seen_states.add(snap.cycle_state)
        if snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL) and int(
            CycleState.RECOVERY
        ) in seen_states:
            break

    assert int(CycleState.RECOVERY) in seen_states
    assert int(CycleState.BLADE_UP) in seen_states
    assert int(CycleState.RETURN_AXES) in seen_states
    assert int(CycleState.CLAMP_UP) in seen_states
    assert int(CycleState.CYCLE_COMPLETE) in seen_states
    assert snap.cycle_state == int(CycleState.WAIT_FOR_MATERIAL)
    assert snap.cycle_active is False


def test_auto_cycle_active_states_are_all_real_enum_members():
    # Guards against a future edit reintroducing a stale CycleState name.
    for state in AUTO_CYCLE_ACTIVE_STATES:
        assert isinstance(state, CycleState)
