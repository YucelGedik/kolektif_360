"""2026-09-18 (kullanıcı isteği): ana ekrandaki birleşik Alarm/Uyarı/Mesaj
panosu. `AlarmEvent.severity` alanı ve genel `log_event()` (Uyarı/Mesaj
sabit bir kod tablosuna bağlı değil) ile ilgili testler.

Not: `persistence/db.py` process-genelinde tek bir global engine/session
factory kullanıyor (`config_path` gibi MachineService'e enjekte edilebilir
değil - bu bilinen, ayrıca kullanıcıya bildirilen bir sınırlama). DB'ye
gerçekten dokunan testler burada `init_engine(tmp_path/...)` ile İZOLE bir
dosyaya yönlendirip test sonunda varsayılana GERİ döndürüyor, böylece bu
dosyadaki testler diğer test dosyalarının paylaşımlı `data/bufera.db`'sini
kirletmiyor - ama bu geçici bir önlem, kalıcı çözüm değil."""

from __future__ import annotations

import contextlib

import persistence.db as db_module
from persistence.alarms import (
    SEVERITY_ALARM,
    SEVERITY_LABELS_TR,
    SEVERITY_MESSAGE,
    SEVERITY_WARNING,
    AlarmEvent,
    AlarmRepository,
    alarm_text,
)
from ui.machine.machine_page import filter_alarm_events


@contextlib.contextmanager
def _isolated_engine(tmp_path):
    db_module.init_engine(tmp_path / "test_alarms.db")
    try:
        yield
    finally:
        db_module.init_engine()  # varsayılan data/bufera.db'ye geri dön


def test_all_three_severities_have_turkish_labels():
    assert set(SEVERITY_LABELS_TR) == {SEVERITY_ALARM, SEVERITY_WARNING, SEVERITY_MESSAGE}
    assert all(isinstance(v, str) and v for v in SEVERITY_LABELS_TR.values())


def test_filter_alarm_events_default_all_selected_returns_everything():
    events = [
        AlarmEvent(severity=SEVERITY_ALARM, source="X AXIS", message="a"),
        AlarmEvent(severity=SEVERITY_WARNING, source="Y AXIS", message="b"),
        AlarmEvent(severity=SEVERITY_MESSAGE, source="PLC", message="c"),
    ]

    result = filter_alarm_events(events, {SEVERITY_ALARM, SEVERITY_WARNING, SEVERITY_MESSAGE})

    assert result == events


def test_filter_alarm_events_only_warning():
    alarm = AlarmEvent(severity=SEVERITY_ALARM, source="X AXIS", message="a")
    warning = AlarmEvent(severity=SEVERITY_WARNING, source="Y AXIS", message="b")
    message = AlarmEvent(severity=SEVERITY_MESSAGE, source="PLC", message="c")

    result = filter_alarm_events([alarm, warning, message], {SEVERITY_WARNING})

    assert result == [warning]


def test_filter_alarm_events_none_selected_returns_empty():
    events = [AlarmEvent(severity=SEVERITY_ALARM, source="X AXIS", message="a")]

    assert filter_alarm_events(events, set()) == []


def test_raise_alarm_still_uses_alarm_severity_and_coded_text(tmp_path):
    with _isolated_engine(tmp_path):
        repo = AlarmRepository()
        event = repo.raise_alarm(1001, "X AXIS")

        assert event.severity == SEVERITY_ALARM
        assert event.code == 1001
        assert event.message == alarm_text(1001)


def test_log_event_supports_warning_and_message_without_a_code(tmp_path):
    with _isolated_engine(tmp_path):
        repo = AlarmRepository()
        warning = repo.log_event(SEVERITY_WARNING, "Y AXIS", "Serbest metin uyarı")
        message = repo.log_event(SEVERITY_MESSAGE, "OPERATOR", "Serbest metin mesaj")

        assert warning.code is None
        assert warning.severity == SEVERITY_WARNING
        assert warning.message == "Serbest metin uyarı"
        assert message.severity == SEVERITY_MESSAGE

        recent = repo.recent()
        assert {e.severity for e in recent} == {SEVERITY_WARNING, SEVERITY_MESSAGE}


def test_log_event_rejects_unknown_severity(tmp_path):
    with _isolated_engine(tmp_path):
        repo = AlarmRepository()
        try:
            repo.log_event("BILINMEYEN", "PLC", "x")
            assert False, "ValueError bekleniyordu"
        except ValueError:
            pass


def test_migration_adds_severity_column_to_a_pre_existing_table(tmp_path):
    """Kullanıcının gerçek `data/bufera.db`'sinde zaten olan, `severity`
    sütunu OLMAYAN eski satırların kaybolmadan/hata vermeden çalışmaya
    devam ettiğini doğrular (gerçek DB üzerinde elle doğrulandı, bu test
    izole bir dosyada aynı senaryoyu tekrar üretir)."""
    import sqlite3

    db_path = tmp_path / "legacy.db"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE alarm_events ("
        "id INTEGER PRIMARY KEY, occurred_at DATETIME, cleared_at DATETIME, "
        "code INTEGER, source VARCHAR(32), message VARCHAR(200))"
    )
    con.execute(
        "INSERT INTO alarm_events (occurred_at, code, source, message) "
        "VALUES ('2026-01-01 00:00:00', 1001, 'X AXIS', 'eski satır')"
    )
    con.commit()
    con.close()

    db_module.init_engine(db_path)
    try:
        repo = AlarmRepository()
        events = repo.recent()
        assert len(events) == 1
        assert events[0].message == "eski satır"
        assert events[0].severity == SEVERITY_ALARM  # migration default
    finally:
        db_module.init_engine()
