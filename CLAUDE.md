# Bufera Makine Ekranı - AI Baslangic Protokolu

Bu dosya, AI ajaninin projeye az token harcayarak girmesi ve calisma stilini
korumasi icin ana protokoldur.

## Oturum Baslangici

### Compact sonrasi

Context icinde onceki oturumdan devam edildigi anlasiliyorsa:

1. Sadece `.ai/memory/SESSION_BRIEF.md` dosyasini oku.
2. Kullaniciya aktif durum, siradaki gorev ve hazir oldugunu bildir.
3. Kullanici istemedikce buyuk hafiza dosyalarini okuma.

### Taze oturum

1. Once `.ai/memory/SESSION_BRIEF.md` dosyasini oku.
2. Yeterli degilse `.ai/RULES.md` icindeki aktif faz/aktif is bolumunu oku.
3. Kod degisikligi yapmadan once sadece gereken dosyalari oku.

## Buyuk Dosya Okuma Kurali

Buyuk dosyalari tam okuma. Sadece su durumlarda ilgili bolumu oku:

- Kullanici acikca mimariyi, proje gecmisini veya dosya yapisini sorarsa.
- Kod degisikligi icin ilgili bolume gercekten ihtiyac varsa.
- Teknik karar verirken onceki karar kaydi gerekiyorsa.
- `docs/BUFERA_MAKINE_EKRANI_CODEX_ENTEGRASYON_BRIFI.md` cok uzun (32 bolum);
  yalnizca ilgili bolum numarasi biliniyorsa o kismi oku.

## Yasaklar

- Oturum basinda `PROJECT_MEMORY.md` dosyasini komple okuma.
- Oturum basinda `CHANGELOG_MEMORY.md` dosyasini komple okuma.
- Kullanici net bir gorev verdiyse gereksiz oryantasyon yapma.
- Projeye ozel olmayan buyuk refactor veya stil degisikligi yapma.
- VisionCut'in gercek kaynak koduna erisimimiz oldugunu varsayma (yok,
  bkz. `INTEGRATION.md`).
- Gercek bir PLC baglantisi varmis gibi davranma; varsayilan calisma modu
  Demo moddur (`config/opcua.json` endpoint bos).

## Hafiza Guncelleme Kurali

Her anlamli kod degisikliginden sonra su sirayla guncelle:

1. `.ai/memory/SESSION_BRIEF.md`
   - Aktif durum
   - Siradaki gorevler
   - Son build/test sonucu
   - Son 3 onemli degisiklik
2. `.ai/RULES.md`
   - Tamamlanan gorevi `[ ]` -> `[x]` yap
   - Yeni mikro gorev gerekiyorsa ekle
3. `.ai/memory/CHANGELOG_MEMORY.md`
   - Yeni girisi en uste ekle
   - Tarih, degisen dosyalar, test/build sonucu yaz

`PROJECT_MEMORY.md`, `RULES_ARCHIVE.md` ve `CHANGELOG_ARCHIVE.md` sadece mimari
degisiklik, yeni faz plani veya arsivleme ihtiyaci oldugunda guncellenir.

## Proje Ozeti

- Proje: Bufera Makine Ekranı (VisionCut entegrasyonu icin bagimsiz teslim paketi)
- Stack: Python 3.13, PySide6 6.11.1, asyncua, pydantic 2.13.4, SQLAlchemy 2.x, SQLite, pytest
- Build: `python -m venv .venv` + `pip install -r requirements.txt`
- Run: `.venv\Scripts\python.exe -m app.main` (Demo modda calisir, gercek PLC gerekmez)
- Ana kaynak dizini: `core/`, `plc/`, `services/`, `persistence/`, `ui/machine/`, `app/`
- Test komutu: `pytest` (proje kokunden, `.venv` aktifken)

## Dosya Haritasi

```text
.ai/
  INDEX.md
  RULES.md                    <- mimari kurallar + aktif yol haritasi
  memory/
    SESSION_BRIEF.md          <- oturum girisi; her zaman once bunu oku
    PROJECT_MEMORY.md         <- teknik referans; ihtiyac aninda oku
    CHANGELOG_MEMORY.md       <- son degisiklikler; ihtiyac aninda oku
    CHANGELOG_ARCHIVE.md      <- eski degisiklik arsivi
    RULES_ARCHIVE.md          <- tamamlanan faz detaylari
    DECISIONS.md              <- teknik karar gecmisi
  skills/design/
    DESIGN.tr.md              <- UI tasarim sistemi
    DESIGN.en.md              <- UI design system
docs/
  BUFERA_MAKINE_EKRANI_CODEX_ENTEGRASYON_BRIFI.md   <- orijinal 32 bolumluk brif
README.md                     <- kurulum + calistirma
INTEGRATION.md                <- VisionCut'a teslim notlari
```

## UI Degisikligi Yaparken

UI veya gorunum degisikligi yapmadan once `.ai/skills/design/DESIGN.tr.md`
dosyasini oku. Ayrica `ui/machine/theme.py` (renk/font tokenlari) ve
`ui/machine/widgets.py` (Card/Readout/StatusChip/HoldButton) icindeki mevcut
bilesenleri yeniden kullan; yeni bir tema/bilesen seti kurma.

## Teknik Karar Gerektiginde

Once `.ai/memory/DECISIONS.md` dosyasini oku. Yeni karar alinirsa ayni dosyaya
tarih, baglam, karar ve sonuc olarak ekle.
