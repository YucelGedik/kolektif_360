# Bufera Makine Ekranı - AI Dosya Haritasi

Bu klasor, AI ajaninin projede az token ile calismasi icin hafiza, karar ve
calisma kurallarini tutar. Kaynak kod burada degildir.

## Yapi

```text
.ai/
  INDEX.md
  RULES.md
  hooks/
    session_brief_inject.ps1
  skills/design/
    DESIGN.tr.md
    DESIGN.en.md
  memory/
    SESSION_BRIEF.md
    PROJECT_MEMORY.md
    CHANGELOG_MEMORY.md
    CHANGELOG_ARCHIVE.md
    RULES_ARCHIVE.md
    DECISIONS.md
```

## Dosya Gorevleri

| Dosya | Icerik | Ne zaman okunur |
|-------|--------|-----------------|
| `memory/SESSION_BRIEF.md` | Aktif durum, siradaki is, son build/test | Her oturum basinda |
| `RULES.md` | Mimari kurallar, aktif plan, checklist | Gorev planlarken |
| `memory/PROJECT_MEMORY.md` | Teknik referans, veri akisi, dizin haritasi | Ihtiyac aninda |
| `memory/CHANGELOG_MEMORY.md` | Kronolojik degisiklik kaydi | Son degisiklikleri ararken |
| `memory/DECISIONS.md` | Karar gecmisi | Teknik karar oncesi |
| `skills/design/DESIGN.tr.md` | UI tasarim kurallari | UI degisikligi oncesi |

## Bakim Kurali

`SESSION_BRIEF.md` kisa kalmali. Detay buyuyorsa ilgili hafiza dosyasina tasinmali.

## Bu proje icin ek not

Asil teknik brif (32 bolum, Turkce) `docs/BUFERA_MAKINE_EKRANI_CODEX_ENTEGRASYON_BRIFI.md`
dosyasindadir. `.ai/` buradaki bilgiyi tekrarlamaz, ozetler; detay icin brife
bolum numarasiyla referans verir (orn. "brif SS10" = brif bolum 10).
