# Bufera Makine Ekranı - Degisiklik Hafizasi

Yeni girisleri en uste ekle. Eski ve uzun detaylari `CHANGELOG_ARCHIVE.md`
dosyasina tasi.

## 2026-09-12

### AI hafiza sistemi projeye uyarlandi

- Eklenenler: `CLAUDE.md`, `.ai/` (INDEX, RULES, memory/*, skills/design/*, hooks/*)
- Kaynak: `D:\work\GitProjects\MilGor_Project\ai-starter-kit` sablonlari,
  Bufera projesinin gercek durumuyla dolduruldu (TODO birakilmadi).
- Build/Test: etkilenmedi (sadece dokumantasyon/hafiza dosyalari).

### Ilk proje iskeleti + iki gercek hata duzeltmesi

- Eklenenler: `core/`, `plc/`, `services/`, `persistence/`, `ui/machine/`,
  `app/main.py`, `tests/`, `config/opcua*.json`, `README.md`, `INTEGRATION.md`.
- Duzeltilen hatalar (gercek calistirma + ekran goruntusu ile bulundu):
  1. `manual_page.py`/`settings_page.py`/`alarm_page.py` "Ana Ekran" geri
     butonu `"main"` anahtari yayiyordu, `app/main.py` sozlugu
     `"machine_main"` bekliyordu -> KeyError, operator sayfada kilitleniyordu.
     Duzeltme: uc sayfa da `"machine_main"` yaymaya cekildi.
  2. `app/main.py::main()` icinde `service.start()`, `MainWindow` (ve onun
     sinyal aboneleri) olusturulmadan ONCE cagiriliyordu -> ilk Demo mod
     bildirimi kimse dinlemeden kayboluyordu, status bar "PLC: --" gosteriyordu.
     Duzeltme: `service.start()` cagrisi `MainWindow` olusturulup `show()`
     yapildiktan sonraya alindi.
- Build/Test: `pytest` 8/8 gecti. `python -m app.main` gercekten calistirilip
  PowerShell + UI Automation ile 4 ekranin ekran goruntusu alindi (Operator,
  Manuel, Ayarlar, Alarmlar) ve dogrulandi.
