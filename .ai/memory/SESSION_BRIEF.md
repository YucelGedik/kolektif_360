# SESSION_BRIEF - Son guncelleme: 2026-09-24

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Standalone `.exe` hazırlandı (2026-09-24, kullanıcı: "programı IPC'ye
atacağım, direkt tıkla çalıştır exe hazırla").** PyInstaller ile
paketlendi; bu sırada VisionCut mesaj 08 (madde a/b, `INTEGRATION.md`)'de
zaten bilinen 2 gerçek paketleme hatası da düzeltildi:
- **Yeni `core/app_paths.py::app_base_dir()`** - frozen (`.exe`) çalışırken
  `.exe`nin bulunduğu klasörü, dev'de proje kökünü döndürür.
  `persistence/db.py::DATA_DIR` ve `plc/tag_map.py::DEFAULT_CONFIG_PATH`
  artık buna bağlı - önceden `__file__`e göreliydi, frozen'da geçici/
  salt-okunur bir açılım dizinine düşerdi.
- **Config dosyası yoksa/bozuksa artık çökmek yerine Demo moda düşülüyor**
  (`MachineService.__init__`, `TagMapError` yakalanıyor).
- `save_config()` artık `config/` klasörünü yoksa oluşturuyor (ilk
  çalıştırmada "Kaydet" `FileNotFoundError` verirdi).
- Çıktı: `dist/BuferaMakineEkrani/` (exe + gerçek `config/opcua.json` +
  boş `data/`) - **taşınabilir, bu klasörü olduğu gibi IPC'ye kopyala.**
  Build script: `packaging/BuferaMakineEkrani.spec` (`.venv\Scripts\
  pyinstaller.exe packaging\BuferaMakineEkrani.spec`, proje kökünden).
- 3 gerçek senaryoda test edildi (screenshot ile): config yokken Demo
  moda düşüyor + `data/` klasörünü kendi yanında oluşturuyor; gerçek
  config ile **GERÇEK PLC'ye bağlandı** ("PLC: BAĞLI" doğrulandı).
5 yeni test (`test_frozen_packaging.py` + `test_tag_map.py`+1). Tam suite
371/371. `dist/`/`build/` `.gitignore`'a eklendi (exe repoya commit
edilmedi, yalnız kaynak kod + spec dosyası).

**Bilinen, HENÜZ TEMİZLENMEMİŞ DB kirliliği:** proje `data/bufera.db`'de
4 sahipsiz demo-alarm kaydı var (bugünkü `pytest` koşumlarından - aynı
eski desen). Kullanıcının GERÇEK `python -m app.main` oturumu şu an AÇIK
(10:56'dan beri) - temizlik için önce kapatması istenecek, kendiliğinden
DOKUNULMADI.

## Siradaki Gorevler

- [ ] Kullanıcı: exe'yi IPC'ye kopyalayıp gerçek ortamda deneyecek.
- [ ] `data/bufera.db`'deki 4 sahipsiz kayıt - kullanıcı uygulamayı
      kapatınca temizlenecek.
- [ ] Kullanıcı: C8 (5 fiziksel test) + C8E (6 fiziksel test) sahada
      denenecek.
- [ ] PLC tarafı: X/Y fiziksel limit sensörleri - uç/polarite/durdurma
      davranışı henüz belirlenmedi.
- [ ] VisionCut'tan 4 paketleme hatası için gerçek yama dosyası bekleniyor
      (mesaj 13 ile "son push'u aldınız mı" diye soruldu, henüz yanıt yok).
- [ ] PLC tarafı: C7 test kayıtları kullanıcının genel bildirimiyle
      uzlaştırılacak.
- [ ] `data/bufera.db` paylaşımlı-engine TAM test-suite izolasyonu hâlâ
      açık bakım işi (yalnız benim ad-hoc betiklerim değil, `pytest`in
      kendisi de sızdırıyor - bkz. Kısa Notlar).
- [ ] "Otomatik çevrim kesilmişse" toparlanma MESAJ'ı (mesaj 21) bilinçli
      ERTELENDİ.
- [ ] DPI ölçek-yuvarlama düzeltmesi kullanıcı tarafından HENÜZ
      doğrulanmadı (laptop panelinde tam ekran testi).

## Son Build/Test

- `pytest`: 371/371 (2026-09-24).

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`/`CHANGELOG_MEMORY.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - degistirmeden once yedekle.
- **`data/bufera.db` PAYLAŞIMLI - `pytest`in KENDİSİ bile izole değil**
  (demo_simulator testleri gerçek DB'ye yazıyor, bugün 2026-09-24'te de
  tekrar oldu). Kendi ad-hoc betiklerimde `persistence.db.init_engine(
  <izole tmp yol>)` kullanıyorum ama bu TESTLERİ kapsamıyor - tam çözüm
  hâlâ açık. DB'ye şüpheli yazı görülünce önce çalışan orphan `python -m
  app.main`/`pytest` süreci var mı diye bak (`Get-CimInstance Win32_
  Process -Filter "name='python.exe'" | Select CommandLine`). Manuel
  silme yalnız uygulama KAPALIYKEN, kullanıcı onayıyla.
- **Gerçek PLC'nin OPC UA sunucusu `MaxNodesPerRead=MaxNodesPerBrowse=
  MaxNodesPerWrite=100`** - `_read_loop` otomatik chunk'lıyor.
- Yeni PLC NodeId'sini gerçek config'e eklemeden önce salt-okunur browse ile
  doğrula.
- Demo modda `MachineService.start()` çağrılmadan `snapshot.stale` hep True
  kalır - smoke test'te elle `False` set edilmeli.
- `QFont.setFeature()` PySide6 6.11.1/Windows'ta resize'da glif bozulmasına
  yol açabiliyor - kullanma. DPI PassThrough politikası KULLANICI
  TARAFINDAN HENÜZ DOĞRULANMADI.
- Frozen (`.exe`) çalışırken config/data yolları `core/app_paths.py::
  app_base_dir()`e bağlı (`.exe`nin klasörü) - `__file__`e göre YENİ yol
  ekleme, bu helper'ı kullan.
- **VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC`** (dış
  repo, PUBLIC) - `gh` hesabımız buraya PUSH YETKİLİ.
