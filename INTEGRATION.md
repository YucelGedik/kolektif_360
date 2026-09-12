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

`app/main.py` VisionCut'a taşınmaz — onun yerine VisionCut'ın kendi ana
penceresine:

1. Bir **"Makine Ekranı"** butonu eklenir (Vision ekranının navigasyonuna).
2. Bu buton, `MachineService` örneğini oluşturup `.start()` çağırır ve
   `ui.machine.machine_page.MachinePage(service)`'i gösterir.
3. `MachinePage.navigateRequested` sinyali `"manual" | "settings" |
   "alarms" | "camera"` değerleri yayar; VisionCut'ın navigasyon katmanı bu
   sinyali dinleyip ilgili sayfaya (`ManualPage`, `SettingsPage`,
   `AlarmPage`, ya da kendi kamera ekranına) geçmelidir.

`app/main.py`'deki `MainWindow` sınıfı, bu kablolamanın referans
implementasyonudur — VisionCut'ın kendi navigasyon standardı farklıysa aynı
mantık (servis oluştur → sayfaları oluştur → sinyalleri navigasyona bağla)
korunarak kendi navigasyon sistemlerine taşınabilir.

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
