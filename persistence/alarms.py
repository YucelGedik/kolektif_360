"""Alarm history: brief section 9 (Saat/Kod/Kaynak/Alarm/Durum) persisted
locally so the Alarm screen survives an app restart."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from persistence.db import Base, get_session

# Brief section 9 suggested alarm code ranges (kept out of VisionCut's own
# 100-603 range, which belongs to the camera application):
#   1000-1099 Servo / Axis
#   1100-1199 Pneumatic
#   1200-1299 Vision/Communication
#   1300-1399 Process
#   1400-1499 Operator/Interlock
ALARM_TEXTS_TR: dict[int, str] = {
    1001: "X Servo Hazır Değil",
    1002: "Y Servo Hazır Değil",
    1101: "Baskı Aşağı Zaman Aşımı",
    1102: "Bıçak Aşağı Zaman Aşımı",
    1201: "Vision Heartbeat Kayboldu",
    1202: "Vision Hazır Değil",
    1203: "OPC UA Haberleşmesi Koptu",
    1204: "Kesim Sırasında Çizgi Kayboldu",
    1301: "Y Takip Limiti Aşıldı",
    1302: "Kesim Yarıda Kesildi",
    1401: "Start Interlock Sağlanmadı",
}

ALARM_SOURCES = ("PLC", "X AXIS", "Y AXIS", "VISION", "PNEUMATIC", "OPC UA")

# 2026-09-18 (kullanıcı isteği): ana ekrandaki birleşik Alarm/Uyarı/Mesaj
# panosu için üç seviye. H4 (merkezi alarm ekranı) PLC C2 sözleşmesini
# bekliyor - bu sadece EKRAN/VERİ MODELİDİR, canlı PLC alarm tag'i
# bağlanmadı; satırlar şimdilik kullanıcı/HMI tarafından elle doldurulacak
# ("onları dolduracağız").
SEVERITY_ALARM = "ALARM"
SEVERITY_WARNING = "UYARI"
SEVERITY_MESSAGE = "MESAJ"
SEVERITIES = (SEVERITY_ALARM, SEVERITY_WARNING, SEVERITY_MESSAGE)

SEVERITY_LABELS_TR: dict[str, str] = {
    SEVERITY_ALARM: "Hata",
    SEVERITY_WARNING: "Uyarı",
    SEVERITY_MESSAGE: "Mesaj",
}


def alarm_text(code: int) -> str:
    return ALARM_TEXTS_TR.get(code, f"Bilinmeyen Alarm ({code})")


class AlarmEvent(Base):
    __tablename__ = "alarm_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)
    cleared_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(16), default=SEVERITY_ALARM)
    # PLC-HMI-20260922-18 (HMI-A02): `ALARM_CATALOG` giriş kimliği (H01,
    # H20, ...) - yalnız katalog-driven kayıtlarda dolu; restart sonrası
    # `MachineService`'in RAM'deki `_active_alarm_events`'i DB'deki gerçek
    # açık kayıtlarla uzlaştırabilmesi için gerekli (mesaj metnine göre
    # eşleştirme kırılgan olurdu - katalog metni değişebilir).
    catalog_id: Mapped[str | None] = mapped_column(String(8), nullable=True)

    @property
    def active(self) -> bool:
        return self.cleared_at is None


class AlarmRepository:
    def raise_alarm(self, code: int, source: str) -> AlarmEvent:
        """Mevcut, kod-tabanlı ALARM girişleri (davranış değişmedi)."""
        return self.log_event(SEVERITY_ALARM, source, alarm_text(code), code=code)

    def log_event(
        self,
        severity: str,
        source: str,
        message: str,
        code: int | None = None,
        catalog_id: str | None = None,
    ) -> AlarmEvent:
        """Genel giriş - Uyarı/Mesaj için de kullanılır; bunların sabit bir
        kod tablosu olmak zorunda değil (görev notu: kullanıcı satırları
        elle dolduracak)."""
        if severity not in SEVERITIES:
            raise ValueError(f"Bilinmeyen severity: {severity}")
        with get_session() as session:
            event = AlarmEvent(
                code=code, source=source, message=message, severity=severity, catalog_id=catalog_id
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    def clear_event(self, event_id: int) -> None:
        """Tek bir aktif kaydı kapatır (PLC-HMI-20260921-16, C6.1) - Reset
        tıklamasıyla DEĞİL, o kaydın PLC koşulunun gerçekten FALSE okunduğu
        an çağrılır. `clear_active()`'ın aksine yalnız BU kaydı etkiler."""
        with get_session() as session:
            event = session.get(AlarmEvent, event_id)
            if event is not None and event.cleared_at is None:
                event.cleared_at = dt.datetime.now()
                session.commit()

    def clear_active(self) -> int:
        with get_session() as session:
            active = (
                session.query(AlarmEvent)
                .filter(AlarmEvent.cleared_at.is_(None))
                .all()
            )
            for event in active:
                event.cleared_at = dt.datetime.now()
            session.commit()
            return len(active)

    def recent(self, limit: int = 100) -> list[AlarmEvent]:
        with get_session() as session:
            return (
                session.query(AlarmEvent)
                .order_by(AlarmEvent.occurred_at.desc())
                .limit(limit)
                .all()
            )

    def active_events(self) -> list[AlarmEvent]:
        """PLC-HMI-20260922-18 (HMI-A02, C06_1 audit): `recent(limit=100)`
        geçmiş görünümü için doğru bir sınırdır, ama bir kaydın AKTİF
        (henüz kapanmamış) olması bu sınırdan bağımsız olmalı - 100'den
        fazla geçmiş/temizlenmiş olay birikirse `recent()` gerçekten aktif
        eski bir HATA'yı listeden düşürebilir. "Güncel Alarmlar" ve ALARM
        sayacı bu yüzden ayrı, SINIRSIZ bir sorgu kullanır."""
        with get_session() as session:
            return (
                session.query(AlarmEvent)
                .filter(AlarmEvent.cleared_at.is_(None))
                .order_by(AlarmEvent.occurred_at.desc())
                .all()
            )

    def open_catalog_events(self) -> list[AlarmEvent]:
        """PLC-HMI-20260922-18 (HMI-A02): hâlâ açık (cleared_at IS NULL) VE
        bir `catalog_id` taşıyan kayıtlar - `MachineService` başlangıçta
        bunları RAM'deki `_active_alarm_events`'e geri yükleyerek DB ile
        uzlaşır. En yeniden en eskiye sıralı (aynı catalog_id için birden
        fazla açık kayıt varsa - eski bir bug'ın kalıntısı - en yenisi
        tutulur, eskiler ayrı temizlenir)."""
        with get_session() as session:
            return (
                session.query(AlarmEvent)
                .filter(AlarmEvent.cleared_at.is_(None), AlarmEvent.catalog_id.isnot(None))
                .order_by(AlarmEvent.occurred_at.desc())
                .all()
            )

    def active_count(self) -> int:
        return len(self.active_events())
