"""Kullanıcı isteği (2026-09-22): "U01-U11 tabloda yazılsın mutlaka ama
banner gibi kalıcı olmasın... resete bağlı değil, şu an hangi mantıkla
çalışıyorsa tablonun içinde de o mantıkla çalışsın." Bu testler, ana
ekrandaki "Göster: Hata/Uyarı/Mesaj" filtreli tabloya artık canlı Start
engeli (Uxx) satırlarının da düşmesini - ve bunların `AlarmRepository`'ye
YAZILMADAN, her snapshot'ta anında görünüp kaybolmasını - doğrular."""

from __future__ import annotations

import contextlib
import json

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

import persistence.db as db_module
from persistence.alarms import SEVERITY_ALARM, SEVERITY_WARNING
from services.machine_service import MachineService
from ui.machine.machine_page import MachinePage


@contextlib.contextmanager
def _isolated_engine(tmp_path):
    db_module.init_engine(tmp_path / "test_machine_page_warning_table.db")
    try:
        yield
    finally:
        db_module.init_engine()  # varsayılan data/bufera.db'ye geri dön


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
    return [
        tuple(table.item(row, col).text() for col in range(4))
        for row in range(table.rowCount())
    ]


def test_active_start_inhibit_reason_appears_in_the_table(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)

        _emit(svc, stale=True, start_permitted=False)

        rows = _table_rows(page)
        assert len(rows) == 1
        occurred, severity, source, message = rows[0]
        assert occurred == "ŞİMDİ"
        assert severity == "Uyarı"
        assert message == "[U10] PLC verisi güncel değil; izin/konum bilgisi doğrulanamıyor."


def test_reason_disappears_the_moment_condition_clears_no_history(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        _emit(svc, stale=True, start_permitted=False)
        assert len(_table_rows(page)) == 1

        _emit(svc, stale=False, start_permitted=True)

        assert _table_rows(page) == []
        # Gerçek bir HATA gibi geçmişe de yazılmadı - AlarmRepository boş.
        assert svc.recent_alarms() == []


def test_unchecking_uyari_filter_hides_the_live_reason(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        _emit(svc, stale=True, start_permitted=False)
        assert len(_table_rows(page)) == 1

        page._alarm_filter_checks[SEVERITY_WARNING].setChecked(False)

        assert _table_rows(page) == []


def test_live_warning_is_not_tied_to_reset(tmp_path):
    """"resete falan bağlı değil" - Reset tıklamak canlı U-satırını
    etkilemez, yalnız PLC'nin kendi okuması (snapshot) değiştirince kaybolur."""
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)
        _emit(svc, stale=True, start_permitted=False)
        assert len(_table_rows(page)) == 1

        svc.request_reset()
        _app.processEvents()

        assert len(_table_rows(page)) == 1  # hâlâ aktif - Reset'ten bağımsız


def test_real_alarm_and_live_warning_coexist_in_the_same_table(tmp_path):
    with _isolated_engine(tmp_path):
        page, svc = _page(tmp_path)

        svc._on_raw_snapshot({"vision_fault": True})  # H17, gerçek HATA - kalıcı
        _emit(svc, stale=True, start_permitted=False)  # U10, canlı - kalıcı değil

        rows = _table_rows(page)
        assert len(rows) == 2
        severities = {row[1] for row in rows}
        assert severities == {"Hata", "Uyarı"}
