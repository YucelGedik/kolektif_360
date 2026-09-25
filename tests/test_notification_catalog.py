"""Kullanıcı isteği (2026-09-22): Alarmlar sayfasındaki "Alarm Listesi"
sekmesinin statik veri kaynağı. Bu testler yalnız veri bütünlüğünü
doğrular (Qt/UI'ye dokunmaz) - tekrarlanan/boş kod, geçersiz severity gibi
kopyala-yapıştır hatalarını yakalar."""

from __future__ import annotations

from core.notification_catalog import NOTIFICATION_CATALOG
from persistence.alarms import SEVERITIES


def test_all_catalog_ids_are_unique():
    ids = [e.catalog_id for e in NOTIFICATION_CATALOG]
    assert len(ids) == len(set(ids))


def test_every_entry_has_a_valid_severity():
    assert all(e.severity in SEVERITIES for e in NOTIFICATION_CATALOG)


def test_every_entry_has_non_empty_text_and_context():
    assert all(e.text.strip() for e in NOTIFICATION_CATALOG)
    assert all(e.context.strip() for e in NOTIFICATION_CATALOG)


def test_covers_all_h_u_m_ids_from_the_20260921_task():
    ids = {e.catalog_id for e in NOTIFICATION_CATALOG}
    expected = (
        {f"H{n:02d}" for n in range(1, 23)}
        | {f"U{n:02d}" for n in range(1, 12)}
        | {f"M{n:02d}" for n in range(1, 10)}
        # 2026-09-26 (VisionCut entegrasyonu, mesaj 22 §8-§9): Start bekleniyor,
        # kamera Start kilidi, VisionCut arızaları.
        | {"M10", "U12", "V400", "V600"}
    )
    assert ids == expected
