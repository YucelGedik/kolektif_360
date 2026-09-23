# SESSION_BRIEF - Son guncelleme: 2026-09-23

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260923-25 (PLC'nin kaynak incelemesi): C8'in sonuç takibinde
2 gerçek P1 kusur bulundu ve düzeltildi + H16 metni güncellendi
(2026-09-23).** Detay: `CHANGELOG_MEMORY.md` üst giriş, PLC yanıtı
`.ai/Codex_Codesys.md` sonu. Özet:
- "Hızlı Done / sonsuz bekleme": PLC çok hızlı tamamlarsa Busy hiç
  görülmeden Done gelebiliyordu, eski kod bunu sonsuza dek "sent"te
  bırakıyordu (timeout kontrolüne bile ulaşmadan). `request_set_zero()`
  artık gönderim anındaki temiz/kirli durumu kaydediyor.
- "Gerçek Busy bırakılmadan modal kapanabiliyor": zaman aşımı/reconnect
  anında `combined_busy` hâlâ True olsa bile eskiden hemen "error"e geçip
  kilidi açıyordu - yeni `_set_zero_timeout_latched` bayrağı, eksen
  GERÇEKTEN durana kadar kilidi açmıyor.
- H16 metni mesaj 21'e göre güncellendi ("Acil stop aktif. Bıçak ve
  baskıya geri çekme komutu verildi...").
5 yeni/güncellenen test, tam suite 366/366, gerçek render ile doğrulandı.

**Kayıt düzeltmeleri (PLC talebiyle):** "MANUAL_RETURN_STOP(140) Reset
kararı açık" maddesi KALDIRILDI - PLC'nin C5.1/C6 kaynak kararı var,
kullanıcı da fiziksel testte geçti bildirdi. "C8E henüz başlanmadı" iddiası
da YANLIŞTI - PLC C08_2 bazlı C8E kodunu zaten hazırlamış (saha testi
bekliyor, HMI tarafı henüz test edilmedi).

## Siradaki Gorevler

- [ ] Kullanıcı: C8 (5 fiziksel test) + C8E (6 fiziksel test) sahada
      denenecek - PLC'nin genel "bir tur geçti" bildirimi bu SON
      değişikliklerden ÖNCEydi, hepsini değil yalnız değişen senaryoları
      tekrarla.
- [ ] PLC tarafı: X/Y fiziksel limit sensörleri - uç/polarite/durdurma
      davranışı henüz belirlenmedi, varsayılmıyor.
- [ ] VisionCut'tan 4 paketleme hatası için gerçek yama dosyası bekleniyor.
- [ ] PLC tarafı: C7 test kayıtları kullanıcının genel bildirimiyle
      uzlaştırılacak (henüz yapılmadı).
- [ ] "Otomatik çevrim kesilmişse" toparlanma MESAJ'ı (mesaj 21'in ikinci
      kısmı) bilinçli olarak ERTELENDİ - yeni cause-tracking gerektiriyor,
      C8E saha testi beklerken şimdi eklemek riskli görüldü.
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu: PLC de bunu
      flagledi ("gerçek bufera.db üzerinden test/sonradan kayıt silme
      yapılmamalı") - kendi doğrulama betiklerimiz artık izole
      `init_engine()` kullanacak; TÜM `tests/*.py` için tam izolasyon hâlâ
      açık bakım işi.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.
- [ ] Bugünkü tüm değişiklikler henüz commit edilmedi (kullanıcı onayı bekliyor).

## Son Build/Test

- `pytest`: 366/366 (2026-09-23).

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`/`CHANGELOG_MEMORY.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - degistirmeden once yedekle
  (`config/opcua.json.bak*`, `.gitignore`'da).
- **`data/bufera.db` PAYLAŞIMLI, testler/doğrulama betikleri izole DEĞİL -
  bu 3+ kez gerçek karışıklığa yol açtı (kullanıcı bir demo-mod sızıntısını
  gerçek Vision arızası sandı).** Kendi ad-hoc doğrulama betiklerinde ARTIK
  `persistence.db.init_engine(<izole tmp yol>)` kullan (mevcut
  `tests/test_set_zero_dialog.py::_isolated_engine` deseniyle aynı) -
  gerçek DB'ye asla yazma. PLC de bunu flagledi, manuel silme YAPMA.
- **Gerçek PLC'nin OPC UA sunucusu `MaxNodesPerRead=MaxNodesPerBrowse=
  MaxNodesPerWrite=100`** - toplam config node sayısı bunu aşarsa TÜM
  bağlantı kopar. `_read_loop` artık otomatik chunk'lıyor.
- Yeni PLC NodeId'sini gerçek config'e eklemeden önce salt-okunur browse ile
  doğrula (kanıtsız "PLC yapmadı" iddia etme).
- Demo modda `MachineService.start()` çağrılmadan `snapshot.stale` hep True
  kalır - smoke test'te `svc.snapshot.stale = False` elle set edilmeli.
- `QFont.setFeature()` PySide6 6.11.1/Windows'ta resize'da glif bozulmasına
  yol açabiliyor - kullanma. DPI ölçek-yuvarlama politikası (PassThrough)
  da eklendi (2026-09-23) - ekranlar arası farklı-DPI glif bozulması
  şüphesiyle, KULLANICI TARAFINDAN HENÜZ DOĞRULANMADI.
- UI ekran görüntüsü alırken `app.setStyleSheet(STYLESHEET)` çağrılmazsa tema
  hiç uygulanmaz, yanıltıcı görünür.
- **VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC`** (dış
  repo, PUBLIC) - `gh` hesabımız buraya PUSH YETKİLİ.
