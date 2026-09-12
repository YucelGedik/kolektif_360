# SESSION_BRIEF - Son guncelleme: 2026-09-12

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Faz 7 - Gercek PLC entegrasyonuna hazirlik**

Proje iskeleti tamamlandi: `core/plc/services/persistence/ui/app` katmanlari
yazildi, Demo modda (PLC yokken) tum ekranlar gercekten calistirilip
dogrulandi. VisionCut'in kendi kaynak kodu elimizde YOK (baska sirkete ait);
bu repo VisionCut'a sonradan entegre edilecek bagimsiz bir teslim paketi.

## Siradaki Gorevler

- [ ] `.ai/hooks/session_brief_inject.ps1` hook'unun (`.claude/settings.local.json`
      icinde, bu makineye ozel) yeni bir oturumda otomatik calistigini dogrula.
- [ ] Gercek PLC GVL tag adlari geldiginde `config/opcua.example.json`
      guncelle.
- [ ] VisionCut'i yapan sirkete teslim oncesi `INTEGRATION.md` gozden gecir.

## Son Build/Test

- `pytest`: 8/8 gecti (2026-09-12).
- `python -m app.main`: gercekten calistirildi, 4 ekran ekran goruntusuyle
  dogrulandi (Operator/Manuel/Ayarlar/Alarmlar).

## Son Degisiklikler

- 2026-09-12 - Repo GitHub'a (`YucelGedik/kolektif_360`, `master`) push edildi.
- 2026-09-12 - `ai-starter-kit` hafiza sistemi projeye uyarlandi (`CLAUDE.md`, `.ai/`),
  SESSION_BRIEF hook'u `.claude/settings.local.json` ile baglandi (OPC_UA01_SCR/
  OPC_UA02_SCR_LNX projelerindeki ayni desen).
- 2026-09-12 - Iki gercek hata bulundu ve duzeltildi: (1) alt sayfalardaki
  "Ana Ekran" geri butonu yanlis navigasyon anahtari gonderiyordu, (2) Demo
  mod durumu ilk acilista status bar'da gorunmuyordu (sinyal sira hatasi).
- 2026-09-12 - Ilk proje iskeleti + demo simulator + 4 ekran + git init/commit.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur.
- Detay gerekiyorsa `RULES.md`, `PROJECT_MEMORY.md` veya `DECISIONS.md` ihtiyac aninda okunur.
- Gercek PLC yok, gercek VisionCut kaynak kodu yok - varsayimlarini buna gore yap.
