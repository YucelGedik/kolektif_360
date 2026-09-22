"""PLC-HMI-20260922-18 (HMI-A05, C06_1 audit): "Mesaj sınıfını canlı
tabloya bağla" - M01-M09 (`core/notification_catalog.py`) statik referans
olarak vardı ama ana ekranın Hata/Uyarı/Mesaj tablosuna hiç yansımıyordu.
Bu testler, M01-M09'un aynı "canlı, kalıcı DEĞİL" desende (U-serisiyle
aynı: `AlarmRepository`'ye yazılmaz, snapshot'a göre anında görünür/
kaybolur) tabloya düştüğünü - ve M08'in özel "yalnız yeni sonuç" (edge,
durum sürse bile tekrarlanmaz) davranışını doğrular."""

from __future__ import annotations

import contextlib
import json

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

import persistence.db as db_module
from core.cycle_state import CycleState
from persistence.alarms import SEVERITY_MESSAGE
from services.machine_service import MachineService
from ui.machine.machine_page import MachinePage


@contextlib.contextmanager
def _isolated_engine(tmp_path):
    db_module.init_engine(tmp_path / "test_machine_page_message_table.db")
    try:
        yield
    finally:
        db_module.init_engine()


def _page(tmp_path) -> tuple[MachinePage, MachineService]:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    page = MachinePage(svc)
    return page, svc


def _emit(svc: MachineService, **overrides) -> None:
    snap = svc._snapshot
    for key, value in overrides.items():
        setattr(snap, key, value)
    svc.snapshotUpdated.emit(snap)
    _app.processEvents()


def _table_rows(page: MachinePage) -> list[tuple[str, str, str, str]]:
    table = page._alarm_table
    return [tuple(table.item(row, col).text() for col in range(4)) for row in range(table.rowCount())]


def test_m01_state_message_appears_while_state_holds(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)

        _emit(svc, stale=False, cycle_state=int(CycleState.WAIT_VISION))

        rows = _table_rows(page)
        messages = [r for r in rows if r[1] == "Mesaj"]
        assert len(messages) == 1
        occurred, severity, source, text = messages[0]
        assert occurred == "ŞİMDİ"
        assert source == "PLC"
        assert text == "[M01] Kamera verisi bekleniyor."


def test_message_disappears_when_state_changes_away_no_history(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        _emit(svc, stale=False, cycle_state=int(CycleState.WAIT_VISION))
        assert any(r[1] == "Mesaj" for r in _table_rows(page))

        _emit(svc, cycle_state=int(CycleState.MANUAL))

        assert not any(r[1] == "Mesaj" for r in _table_rows(page))
        assert svc.recent_alarms() == []  # hiç kalıcı iz yok


def test_unchecking_mesaj_filter_hides_the_live_message(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        _emit(svc, stale=False, cycle_state=int(CycleState.WAIT_VISION))
        assert any(r[1] == "Mesaj" for r in _table_rows(page))

        page._alarm_filter_checks[SEVERITY_MESSAGE].setChecked(False)

        assert not any(r[1] == "Mesaj" for r in _table_rows(page))


def test_m08_appears_once_on_the_tick_status_first_becomes_done(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        svc._move_to_start_status = "busy"
        _emit(svc, stale=False, cycle_state=int(CycleState.MANUAL))
        assert not any("[M08]" in r[3] for r in _table_rows(page))

        svc._move_to_start_status = "done"
        _emit(svc)

        rows = [r for r in _table_rows(page) if "[M08]" in r[3]]
        assert len(rows) == 1
        assert rows[0][1] == "Mesaj"
        assert rows[0][3] == "[M08] Başlangıç konumuna dönüş tamamlandı."


def test_m08_does_not_repeat_while_status_stays_done(tmp_path):
    """"M08 yalnız yeni sonuç olarak gösterilsin" (görev notu) - status
    "done" olarak KALSA bile M08 yalnız o ilk tick'te bir kez görünür."""
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        svc._move_to_start_status = "busy"
        _emit(svc, stale=False, cycle_state=int(CycleState.MANUAL))
        svc._move_to_start_status = "done"
        _emit(svc)
        assert any("[M08]" in r[3] for r in _table_rows(page))

        _emit(svc)  # status hâlâ "done", yeni bir snapshot tick'i

        assert not any("[M08]" in r[3] for r in _table_rows(page))


def test_m08_fires_again_after_a_new_request_cycle(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        svc._move_to_start_status = "busy"
        _emit(svc, stale=False, cycle_state=int(CycleState.MANUAL))
        svc._move_to_start_status = "done"
        _emit(svc)
        assert any("[M08]" in r[3] for r in _table_rows(page))

        svc._move_to_start_status = "sent"  # yeni bir istek başladı
        _emit(svc)
        assert not any("[M08]" in r[3] for r in _table_rows(page))

        svc._move_to_start_status = "done"  # ikinci kez tamamlandı
        _emit(svc)

        assert any("[M08]" in r[3] for r in _table_rows(page))
