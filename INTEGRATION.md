# VisionCut Entegrasyonu İçin Notlar

Bu belge, bu repodaki Makine Ekranı'nı VisionCut'ın kendi Python/PySide6
uygulamasına ekleyecek geliştiriciler için yazılmıştır.

## Neden bu şekilde yapıldı

Bu ekran Bufera tarafında, VisionCut'ın gerçek kaynak koduna erişimimiz
olmadan geliştirildi. Bu yüzden:

- Kendi başına çalışabilen bir `app/main.py` geliştirme kabuğu içerir
  (VisionCut'ın "Kamera Ekranı"nın yerine geçmez, sadece yer tutucudur).
- `ui/machine/theme.py` ve `ui/machine/widgets.py`, VisionCut'ın gerçek tema
  tokenlarını / `Card`, `Readout`, `SectionTabs` bileşenlerini kullanmak
  yerine, brifte tanımlanan renk paletiyle **birebir uyumlu kendi minimal
  setini** içerir. VisionCut tarafında bu bileşenler zaten varsa, entegrasyon
  sırasında bu iki dosyanın VisionCut eşdeğerleriyle değiştirilmesi ve geri
  kalan sayfa dosyalarının (`machine_page.py` vb.) o bileşenlere uyarlanması
  önerilir.

## Ne taşınmalı

VisionCut'ın kendi `core / plc / services / ui` klasörlerine doğrudan
bırakılabilecek parçalar:

```
core/cycle_state.py
core/models.py
core/parameters.py
plc/models.py
plc/tag_map.py
plc/opcua_client.py
services/machine_service.py
services/demo_simulator.py
persistence/db.py
persistence/alarms.py
persistence/settings_store.py
ui/machine/  (tamamı)
config/opcua.example.json  (referans; gerçek config VisionCut'ın kendi
                             deployment config mekanizmasına uyarlanabilir)
```

### Mimari karar (2026-09-23) — ayrı süreç, TEK PENCERE DEĞİL

**Bu bölüm daha önce "VisionCut, `MachinePage`'i kendi penceresine gömer
(tek süreç)" diyordu - bu plan artık geçerli değil.** VisionCut ajanı
(mesaj 07, `visioncut_message/mesajlar/2026-09-20_07_visioncut.md`), tek
süreçte kare hızı doğruluğunun (ölçüldü: 60→40 fps düşüşü hatayı %47
artırıyor) ve GIL paylaşımının (ölçüldü: bizim ekranlarımız kaldırılınca
26,9→35,1 fps) kendi kamera işleme performansını bozduğunu gösterdi; iki
insan da (Murat Turan mesaj 08'de, Yücel Gedik 2026-09-23'te) **iki ayrı
tam ekran süreç** kararını onayladı. Detay ve gerekçe: `visioncut_message/
KARARLAR.md` + mesajlar `07`-`10`.

Yeni model:
1. VisionCut'ın kendi programında **"Makine Ekranı"** butonu — bu repodan
   derlenmiş ayrı bir `.exe`'yi başlatır (çalışmıyorsa) ya da öne getirir
   (çalışıyorsa), kendini küçültür. PLC tag'i GEREKMEZ.
2. Bizim tarafta (bu repoda) aynı mantığın tersi: "KAMERA EKRANI" butonu
   VisionCut'ın exe'sini başlatır/öne getirir, biz küçülürüz. Pencere eşleme
   başlıkla yapılır (bizim başlığımız "Makine Ekran" alt dizesini içermeye
   devam etmeli - mesaj `08.2`).
3. `app/main.py` artık yalnız bir "dev shell" değil - PyInstaller ile
   paketlenen GERÇEK teslim programı. Mevcut yer tutucu kamera sayfası ve
   `MachinePage.navigateRequested`'in `"camera"` değerini sayfa değişimi
   olarak yorumlayan eski davranış (VisionCut mesaj `08`'de bulduğu 4
   hatanın (c)/(d) maddeleri) bu karara göre değişmeli - **uygulama henüz
   YAPILMADI**, VisionCut'ın gerçek yama dosyasını bekliyoruz (mesaj `08.1`
   yanıtımız, 2026-09-23).
4. Ayrıca online-doğrulanmamış iki gerçek paketleme hatası da düzeltilmeli
   (VisionCut mesaj `08`, madde a/b): `plc/tag_map.py` config dosyası
   yoksa çökmek yerine demo moda düşmeli; `persistence/db.py`/`plc/
   tag_map.py`'deki `__file__`'e göreli yollar, paketlenmiş/frozen
   çalışmada yazılabilir bir konuma (örn. `%ProgramData%`) taşınmalı. Bu
   ikisi mimari kararından BAĞIMSIZ, her koşulda gerçek bir hata.

Eski (artık geçersiz) plan referans için: VisionCut kendi ana penceresine
bir "Makine Ekranı" butonu ekler, bu buton `MachineService`'i oluşturup
`.start()` çağırır ve `MachinePage(service)`'i AYNI pencerede gösterirdi;
`navigateRequested`'in `"camera"` değeri VisionCut'ın kendi kamera
sayfasına dönmek için kullanılırdı. Bu artık uygulanmayacak.

## Eski ShowVisionScreen / VisionScreenRelease

Brif bölüm 5'e göre bu taglar PLC sözleşmesinde durduğu için
`config/opcua.example.json`'a eklenmedi ama silinmedi de — VisionCut'ın
kendi PLC servisi bu tagları zaten kullanıyorsa dokunulmamalı. Bu repo
sadece yeni `HMI_*` / `PAR_*` / `cmd_*` taglarını ekliyor.

## Kesin olmayan noktalar (brif bölüm 28)

`core/cycle_state.py`, `core/parameters.py` ve `config/opcua.example.json`
tek doğru kaynak olacak şekilde tasarlandı: PLC tarafı GVL tag adlarını,
CycleState kodlarını veya parametre limitlerini kesinleştirdikçe sadece bu
üç dosya güncellenmesi yeterli olmalı — UI kodunun hiçbir yerinde bu
değerler tekrar hard-code edilmedi.

## Bilinen eksikler / sonraki adımlar

- OPC UA yazımlarında (`plc/opcua_client.py`) VariantType asyncua tarafından
  otomatik çıkarılıyor; gerçek PLC ile `BadTypeMismatch` görülürse ilgili tag
  için açık `ua.VariantType` geçilmeli.
- JOG Yavaş/Hızlı seçimi için PLC tarafında henüz bir tag yok (brif bölüm 13
  bunu tanımlamıyor); şu an sadece demo modda etkili. Gerçek PLC'de hız
  seçimi netleşince `services/machine_service.py::jog_x/jog_y` güncellenmeli.
- Mühendislik erişimi şu an sade bir checkbox; VisionCut'ta zaten bir
  kullanıcı/rol sistemi varsa (brif bölüm 8) onun yerine bağlanmalı.
