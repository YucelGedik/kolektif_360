# Bufera Tekstil — HMI ↔ PLC Entegrasyon Görev Planı

## Amaç
Mevcut PySide6 makine ekranını, CODESYS/MAT LC-C07 PLC ile OPC UA üzerinden gerçek taglarla bağlamak. UI tasarımını bozmadan demo verilerini kaldırmak, merkezi tag haritası kurmak, komutların doğru yazma semantiğini uygulamak ve gerçek kamera yazılımı gelene kadar Vision simülasyon ekranı hazırlamak.

> Kritik mimari kural: HMI proses/motion mantığını yürütmez. HMI yalnızca operatör isteklerini PLC'ye yazar ve PLC durumlarını okur. Motion interlock, recovery, safety ve state machine PLC'dedir.

---

## 1. Uygulama mimarisi

Aşağıdaki ayrım korunmalı:

- `plc/` veya eşdeğer servis: OPC UA bağlantısı, reconnect, read/write, tag registry
- `core/`: PLC'den bağımsız snapshot/state modeli
- `ui/`: sadece ekran bağlama ve kullanıcı olayları
- `config/`: endpoint ve NodeId/tag eşlemesi
- `services/`: alarm geçmişi, simulator gibi yardımcı servisler

UI widget'larının içinde doğrudan NodeId yazılmamalı. Tüm PLC tagları tek merkezi registry/map üzerinden çözülmeli.

Önerilen gerçek CODESYS NodeId kalıbı:

`ns=4;s=|var|MAT LC-C07.Application.GVL.<TAG>`

Namespace index veya prefix sahada değişebileceği için `ns=4` ve prefix config'te tutulmalı, kod içine dağılmamalı.

---

## 2. Bağlantı durumları

### PLC bağlantı rozeti
Ekrandaki `PLC: DEMO MOD` alanı PLC tagı değildir; OPC UA client durumundan türetilmeli.

Durumlar:
- BAĞLI
- BAĞLANIYOR
- BAĞLANTI YOK
- DEMO MOD

Gerçek PLC'ye bağlıyken demo veri üretimi kapatılmalı.

### Vision hazır rozeti
`VISION: HAZIR` yalnızca `VisionReady` tagına bağlanmamalı.

Önerilen UI condition:

`VisionReady AND xVisionHeartbeatOK AND NOT VisionFault`

---

## 3. Ana ekran — PLC → HMI okumaları

| UI öğesi | PLC Tag / Kaynak | Tip | Not |
|---|---|---:|---|
| X Pozisyonu | `ActualX_mm` | LREAL | mm |
| Y Pozisyonu | `ActualY_mm` | LREAL | mm, işaretli göster |
| X Servo Hazır | `xX_PowerStatus` + `xX_PowerError` | BOOL | Status TRUE ve Error FALSE ise hazır |
| Y Servo Hazır | `xY_PowerStatus` + `xY_PowerError` | BOOL | Status TRUE ve Error FALSE ise hazır |
| Mod | `xManualMode` | BOOL | TRUE=MANUEL, FALSE=AUTO |
| Çevrim Durumu | `eMachineState` | ENUM | mapping aşağıda |
| Perde Baskısı | `ClampDown` | BOOL | Şimdilik timer tabanlı; sensör kontrolü yapılacak |
| Bıçak | `BladeZDown` | BOOL | Şimdilik timer tabanlı; sensör kontrolü yapılacak |
| Vision Çizgi | `LineValid` | BOOL | TRUE=GEÇERLİ |
| Perde Besleme | `FeedActive`, `FeedManualAllowed`, `FeedComplete` | BOOL | UI metni state'e göre türetilebilir |
| Kesim Aktif | `CutActive` | BOOL | Kesim state'i için ana gösterge |
| Emergency | `EmergencyState` | BOOL | TRUE=Emergency aktif |
| Machine Ready | `MachineReady` | BOOL | PLC tarafından hesaplanır |
| Vision heartbeat | `xVisionHeartbeatOK` | BOOL | Kamera bağlantı sağlığı |
| Trajectory Fault | `xTrajectoryFault` | BOOL | Alarm/diagnostic |

### Kesim ilerlemesi
PLC'den ayrı yüzde tagı gerekmiyor.

UI hesabı:

`progress = clamp((ActualX_mm - lrX_CutStartPos) / (lrX_CutEndPos - lrX_CutStartPos), 0, 1)`

- CUTTING sırasında canlı göster.
- WAIT_FOR_MATERIAL/INIT durumunda 0% göster.
- Cut tamamlanıp dönüş başlarken istenirse kısa süre 100% tutulabilir.

---

## 4. Ana ekran — HMI → PLC komutları

### START / STOP / RESET
Taglar:
- `Start`
- `Stop`
- `Reset`

Bunlar PLC'de `R_TRIG` ile işleniyor. HMI sürekli TRUE bırakmamalı.

Yazma semantiği:
1. TRUE yaz
2. kısa süre sonra FALSE yaz

Önerilen pulse: 100–250 ms.

Buton enable kuralları UI tarafında kullanıcı deneyimi için uygulanabilir ancak PLC interlocklarının yerine geçmez.

Önerilen:
- START enable: `MachineReady AND NOT xCycleActive AND NOT xManualMode`
- STOP enable: `xCycleActive`
- RESET enable: alarm/fault/emergency bırakılmış durumlarda

---

## 5. `eMachineState` UI mapping

| Değer | Enum | Ekran metni |
|---:|---|---|
| 0 | INIT | Başlatılıyor |
| 10 | MANUAL | Manuel |
| 20 | WAIT_FOR_MATERIAL | Perde Bekliyor |
| 30 | CLAMP_DOWN | Baskı İniyor |
| 40 | WAIT_VISION | Kamera Bekleniyor |
| 50 | ALIGN_Y | Y Hizalanıyor |
| 60 | WAIT_BLADE_REQUEST | Bıçak Talebi Bekleniyor |
| 70 | BLADE_DOWN | Bıçak İniyor |
| 80 | CUTTING | Kesim |
| 90 | BLADE_UP | Bıçak Kalkıyor |
| 100 | RETURN_AXES | Eksenler Dönüyor |
| 110 | CLAMP_UP | Baskı Kalkıyor |
| 120 | CYCLE_COMPLETE | Çevrim Tamamlandı |
| 500 | STOPPING | Durduruluyor |
| 510 | RECOVERY | Recovery |
| 900 | FAULT | Arıza |

Bilinmeyen değer gelirse `Bilinmeyen Durum (<value>)` göster.

---

## 6. Manuel / Servis ekranı

### Önemli UX kuralı
`MANUEL` sayfasına gitmek otomatik olarak manuel moda geçirmemeli. Navigasyon ile proses komutu ayrılmalı.

Sayfada açık bir kontrol olmalı:
- `MANUEL MODU ETKİNLEŞTİR`

PLC tagı:
- `xManualMode`

### Jog komutları
HMI yalnızca request taglarını yazmalı:
- `xX_JogPlusRequest`
- `xX_JogMinusRequest`
- `xY_JogPlusRequest`
- `xY_JogMinusRequest`

Hold-to-run davranışı:
- mouse/touch press → TRUE
- release/cancel/page close/app focus lost → FALSE

HMI kesinlikle doğrudan şunları yazmamalı:
- `xX_JogPlus`
- `xX_JogMinus`
- `xY_JogPlus`
- `xY_JogMinus`

Bunları `Jog_Control` PLC içinde interlocklardan geçirerek üretir.

### Jog yavaş / hızlı
Mevcut PLC'de yalnızca:
- `lrX_JogVelocity`
- `lrY_JogVelocity`

var.

UI'daki `JOG Yavaş / JOG Hızlı` iki preset olarak kalacaksa iki çözümden biri seçilmeli:
1. preset değerleri HMI config'te tutulup seçildiğinde mevcut `lrX_JogVelocity` / `lrY_JogVelocity` tagına yazılır, veya
2. PLC'ye ayrı slow/fast parametreleri eklenir.

Şimdilik 1. seçenek önerilir; yeni PLC tagı eklemeye gerek yok.

### Y Merkeze Git
Mevcut UI'daki `MERKEZE GİT / Y=0` için HMI doğrudan `xY_MoveExecute` yazmamalı.

PLC'ye yeni bir operator request tagı eklenmesi önerilir:
- `xY_CenterRequest : BOOL`

Bu request `Jog_Control`/manual-control mantığında sadece MANUAL state'te `lrY_MovePosition := lrY_CenterPosition` ve `xY_MoveExecute` üretsin.

Bu tag eklenene kadar buton pasif tutulmalı.

### Manuel bıçak / baskı
Mevcut `Bıçak Aşağı/Yukarı` ve `Baskı Aşağı/Yukarı` butonları internal PLC command taglarına direkt bağlanmamalı.

Önerilen yeni request tagları:
- `xManualBladeDownRequest : BOOL`  // TRUE=Aşağı, FALSE=Yukarı
- `xManualClampDownRequest : BOOL`  // TRUE=Aşağı, FALSE=Yukarı

PLC bunları yalnızca MANUAL state ve uygun interlocklarda `xBladeValveCmd` / `xClampValveCmd` komutlarına dönüştürmeli.

Bu request tagları eklenene kadar bu butonlar pasif/demo tutulmalı.

---

## 7. Ayarlar / Mühendislik ekranı

UI'da demo sabitleri gösterilmemeli; ilk bağlantıda PLC'den read-back yapılmalı.

### Mevcut PLC parametreleri

| UI Parametresi | PLC Tag | Birim |
|---|---|---|
| X Kesim Hızı | `lrX_CutVelocity` | mm/s |
| X Dönüş Hızı | `lrX_ReturnVelocity` | mm/s |
| X Kesim Acc/Dec | `lrX_CutAccDec` | mm/s² |
| X Dönüş Acc/Dec | `lrX_ReturnAccDec` | mm/s² |
| X Kesim Başlangıç | `lrX_CutStartPos` | mm |
| X Kesim Bitiş | `lrX_CutEndPos` | mm |
| Y Merkez Konum | `lrY_CenterPosition` | mm |
| Y Yazılım Min | `lrY_SoftwareMin` | mm |
| Y Yazılım Max | `lrY_SoftwareMax` | mm |
| Y Follow Max Hız | `lrY_MaxVelocity` | mm/s |
| Maksimum dY/dX | `lrMaxAllowedSlope` | mm/mm |
| Y Move Hızı | `lrY_MoveVelocity` | mm/s |
| Y Move Acc/Dec | `lrY_MoveAccDec` | mm/s² |
| X Jog Hızı | `lrX_JogVelocity` | mm/s |
| Y Jog Hızı | `lrY_JogVelocity` | mm/s |
| Jog Acc/Dec | `lrJogAccDec` | mm/s² |
| Stop Acc/Dec | `lrStopAccDec` | mm/s² |
| Pozisyon Toleransı | `lrPositionTolerance` | mm |
| Stop Hız Toleransı | `lrStopVelocityTolerance` | mm/s |
| Vision Heartbeat Timeout | `tVisionHeartbeatTimeout` | TIME |

### UI'daki mevcut uyumsuzluklar
Şu anda ekrandaki demo değerleri PLC'den farklı olabilir. Örnek:
- X Cut speed UI 180 iken PLC 175 olabilir.
- X Acc/Dec UI 2000 iken PLC `lrX_CutAccDec` 500 olabilir.
- Y Max UI 23 iken PLC 30 olabilir.
- Y Max Hız UI 50 iken PLC `lrY_MaxVelocity` 5 olabilir.
- Heartbeat timeout UI 500 ms iken PLC 2 s olabilir.

Bu nedenle HMI ilk açılışta PLC değerlerini okumalı ve widgetları onunla doldurmalı.

### Ayrı X ivme / yavaşlama alanı
PLC artık tek `lrX_CutAccDec` kullanıyor. UI'da ayrı `X İvme` ve `X Yavaşlama` alanı gösterilmemeli. Tek alan:
- `X Kesim Acc/Dec`

Aynı yaklaşım return/jog için de geçerli.

### Pnömatik gecikmeler
Logic_Control'da şu an `T#500ms` hard-coded:
- Clamp Down
- Blade Down
- Blade Up
- Clamp Up

Ayarlar ekranından değiştirilecekse PLC'de GVL parametrelerine taşınmalı:
- `tClampDownDelay`
- `tBladeDownDelay`
- `tBladeUpDelay`
- `tClampUpDelay`

PLC tarafı güncellenene kadar UI'daki bu alanlar gerçek PLC ayarı gibi gösterilmemeli veya `henüz bağlı değil` olarak işaretlenmeli.

### Vision zaman aşımı
`Vision Zaman Aşımı` isimli ayrı PLC tagı şu an tanımlı değil. Heartbeat timeout ile karıştırılmamalı. Gereksinim netleşene kadar kaldır veya devre dışı bırak.

### Parametre yazma
Parametre write işlemleri merkezi PLC service üzerinden yapılmalı. Başarılı write sonrası read-back yap ve UI'da `Uygulandı` göster.

Mühendislik ayarlarının yanlışlıkla değiştirilmemesi için mevcut engineering enable/permission yaklaşımı korunmalı.

---

## 8. Alarm ekranı

Şu an merkezi bir `AlarmCount` PLC tagı yok. `ALARM: N` UI tarafında aktif alarm koşullarından türetilebilir.

İlk aktif alarm kaynakları:
- `EmergencyState`
- `NOT xVisionHeartbeatOK`
- `VisionFault`
- `xX_PowerError`
- `xY_PowerError`
- `xX_CutError`
- `xX_ReturnError`
- `xY_MoveError`
- `xY_FollowError`
- `xTrajectoryFault`

Alarm history edge-latched olmalı:
- condition FALSE→TRUE olduğunda bir kayıt ekle
- her poll'da tekrar kayıt ekleme
- condition TRUE→FALSE olduğunda durum `TEMİZLENDİ` olarak güncellenebilir

Vision `FaultCode` varsa ayrı detay olarak kaydedilebilir.

`RESET` alarm geçmişini silmek zorunda değildir; PLC Reset komutu ile alarm history temizleme farklı işlemlerdir.

---

## 9. Kamera simülasyon ekranı

Gerçek VisionCut uygulaması bu makinede olmadığı için bu ekran bir `Vision Emulator` olacak.

### HMI'nin Vision gibi PLC'ye yazacağı taglar
- `VisionReady`
- `LineValid`
- `VisionFault`
- `TargetX_mm`
- `TargetY_mm`
- `CutPermit`
- `ZDownRequest`
- `Heartbeat`
- `udiVisionSequence`
- `Confidence` (opsiyonel)
- `FaultCode` (test için)

### Simulator otomasyonları

#### Heartbeat Auto
- ON/OFF toggle
- ON iken config'teki periyotta `Heartbeat += 1`
- OFF iken heartbeat sabit kalmalı; PLC watchdog timeout test edilebilmeli

#### Yeni Vision Paketi Gönder
Buton sırası kesin olmalı:
1. `TargetX_mm` yaz
2. `TargetY_mm` yaz
3. `LineValid`, `Confidence`, gerekli process bitlerini yaz
4. `udiVisionSequence += 1` EN SON yaz

Bu, gerçek kamera paket protokolünü simüle eder.

#### ZDown handshake testi
- Simulator `ZDownRequest=TRUE` yazar
- PLC'den `BladeZDown` okunur
- BladeZDown TRUE görüldüğünde simulator bunu ekranda doğrular

### Simulator'ın sadece okuyacağı PLC → Vision tagları
- `MachineReady`
- `CutActive`
- `EmergencyState`
- `ActualX_mm`
- `X_Velocity`
- `CutEndX_mm`
- `FeedActive`
- `FeedComplete`
- `BladeZDown`

Simulator ekranı bu değerleri ayrı bir `PLC → VISION MONITOR` panelinde göstermeli.

---

## 10. PLC iç tagları — HMI doğrudan yazmamalı

Aşağıdaki taglar UI operator komutu değildir:

- `xX_CutExecute`
- `xX_ReturnExecute`
- `xY_MoveExecute`
- `xY_FollowEnable`
- `xX_JogPlus`
- `xX_JogMinus`
- `xY_JogPlus`
- `xY_JogMinus`
- `xMotionStop`
- `xAxisReset`
- `xClampValveCmd`
- `xBladeValveCmd`
- `eMachineState`
- `xTrajectoryValid`
- `xTrajectoryFault`
- actual position/velocity/status tagları

Bu taglar PLC state machine/interlock katmanının çıktılarıdır.

---

## 11. OPC UA servis davranışı

- Reconnect otomatik olmalı.
- UI thread bloklanmamalı.
- Read/write async veya worker thread üzerinden yapılmalı.
- Son geçerli snapshot saklanmalı fakat bağlantı kaybolduğunda UI bunun stale olduğunu göstermeli.
- PLC bağlantısı yokken START/STOP/RESET/JOG yazıları engellenmeli.
- Page close/focus loss/app exit durumunda tüm hold-type request tagları FALSE'a çekilmeye çalışılmalı.
- Bir write başarısızsa UI optimistic olarak başarı göstermemeli.

Önerilen HMI polling:
- hızlı state/position/status: 50–100 ms
- diagnostics/settings: 250–1000 ms

Gerçek kamera tracking trafiği HMI üzerinden geçmeyecek; Vision uygulaması PLC'ye doğrudan yazar.

---

## 12. Uygulama sırası

AI/Codex bu işi tek seferde rastgele refactor etmemeli. Şu sırayla ilerlesin:

1. Mevcut repo ve ekran sınıflarını incele; UI tasarımını değiştirme.
2. Merkezi OPC UA tag registry oluştur.
3. Connection state + snapshot model oluştur.
4. Ana ekranı gerçek read taglarına bağla.
5. START/STOP/RESET pulse write ekle.
6. Manual screen: manual-mode ve jog request handshake'i bağla.
7. Ayarlar ekranını gerçek PLC parameter read/write ile eşleştir; mevcut uyumsuz widgetları düzelt.
8. Alarm engine'i edge-based yap.
9. Vision Simulator ekranını ekle.
10. Demo mode ile real PLC mode'u aynı UI'da fakat farklı data provider üzerinden çalıştır.
11. Testler ekle.

Her aşamada önce plan/etkilenecek dosyaları raporla, sonra kodu değiştir.

---

## 13. Acceptance testleri

- PLC bağlı değilken kontrol komutları gönderilemiyor.
- PLC bağlanınca actual X/Y gerçek değer gösteriyor.
- MachineState doğru Türkçe metne dönüşüyor.
- START pulse TRUE→FALSE çalışıyor.
- STOP pulse TRUE→FALSE çalışıyor.
- RESET pulse TRUE→FALSE çalışıyor.
- Manual mode olmadan Jog request motion üretmiyor.
- Manual mode'da X/Y jog hold-to-run çalışıyor.
- Jog release ile request FALSE oluyor.
- Soft limitte PLC jog'u kesiyor ve UI takılı kalmıyor.
- Heartbeat simulator AUTO çalışırken `xVisionHeartbeatOK=TRUE`.
- Heartbeat durdurulunca timeout sonrası FALSE.
- Yeni Vision paketi Sequence en son artırılarak gönderiliyor.
- `ZDownRequest -> BladeZDown` handshake'i izlenebiliyor.
- Vision/trajectory fault alarmı bir kez history'ye ekleniyor, her poll'da tekrarlanmıyor.
- Ayar write sonrası PLC read-back UI değerine eşit.

