# Bufera Perde Kesme — Makine Ekranı / VisionCut Entegrasyon Brifi
**Amaç:** Bu doküman, VS Code içindeki Codex agent'ın mevcut Operon VisionCut uygulamasına doğrudan entegre edilecek makine kontrol ekranını geliştirmeye başlayabilmesi için hazırlanmıştır.

> **Güncel proje kararı önemlidir:** Daha önceki entegrasyon brifinde otomasyon ekranının ayrı bir uygulama olacağı varsayılmıştı. Bu proje için karar değişmiştir. Makine ekranı **ayrı uygulama olmayacak**; mevcut VisionCut uygulamasının içine yeni bir sayfa/ekran olarak eklenecektir. Vision ekranında bir **“Makine Ekranı”** butonu olacak ve aynı uygulama içinde bu sayfaya geçilecektir. Bu dokümanda bu güncel karar esas alınmalıdır.

---

## 1. Projenin kısa özeti

Makine, perde/kumaşı boylamasına kesen ve kesim çizgisindeki dikim kaynaklı doğrusal sapmayı kamera ile takip ederek Y ekseni üzerinden telafi eden yarı otomatik bir kesim makinesidir.

Makinede:

- **X ekseni:** yaklaşık 3.5–3.6 m strok. Kesim bıçağını perde boyunca boylamasına taşır.
- **Y ekseni:** kesim sırasında kamera tarafından ölçülen çizgi/ofset sapmasını telafi eder.
- **Perde besleme motoru:** 750 W asenkron motor. Operatör perdeyi kesimden önce manuel ileri/geri sürer.
- **Perde baskı pnömatiği:** tek bobinli valf. Kesim öncesi perdeyi zemine sabitler.
- **Bıçak pnömatiği:** tek bobinli valf. Bıçağı aşağı/yukarı alır.
- **Kamera/Vision sistemi:** oluk/çizgi konumunu algılar; kesim sırasında Y hedefi üretir.
- **IPC:** VisionCut uygulamasının çalıştığı Windows x64 panel PC.
- **PLC:** MAT LC-C07, CODESYS tabanlı.
- **X/Y servo:** 400 W, multi-turn absolute encoder.
- **Haberleşme:** OPC UA.

Operatör normal çevrimde perdeyi manuel olarak bıçağın altına getirir. Start verildiğinde perde baskısı iner. Vision çizgiyi doğrular ve bıçak indirilir. X ekseni sabit kesim hızıyla 0 → yaklaşık 3600 mm ilerler. Kesim boyunca kamera Y ofseti üretir ve PLC Y eksenini çizgiyi takip edecek şekilde sürer. Kesim sonunda bıçak kalkar, X hızlı dönüş yapar, Y merkeze döner, baskı kalkar. Operatör kesilen parçayı alır ve yeni perdeyi manuel sürerek çevrimi tekrar başlatır.

---

## 2. Mevcut VisionCut teknoloji yığını — AYNI YIĞINI KULLAN

Makine ekranı mevcut uygulamanın içine ekleneceği için ayrı bir .NET/WPF/WinForms uygulaması geliştirme.

**Mevcut yığın:**

- Python **3.13.12**
- PySide6 **6.11.1**
- Qt 6
- OpenCV **5.0.0**
- NumPy **2.5.1**
- Pydantic **2.13.4**
- `asyncua >= 1.1` — OPC UA
- SQLAlchemy >= 2.0
- Windows 10/11 x64
- PyInstaller — deployment
- VS Code — geliştirme ortamı

Mevcut uygulamanın mimarisi MVVM değildir. Katmanlı yapı kullanılır:

```text
core
camera
vision
plc
sync
services
ui
recipes
persistence
commissioning
app
```

Yeni makine ekranı mümkün olduğunca mevcut `ui`, `plc`, `services`, `core` katmanlarıyla uyumlu eklenmelidir.

### Agent için kural

Yeni ekranı geliştirirken önce repository'yi incele:

1. mevcut navigation/page yapısını bul,
2. mevcut tema/token dosyasını bul,
3. mevcut `Card`, `Readout`, `SectionTabs`, `TouchKeypad` vb. bileşenler varsa yeniden kullan,
4. mevcut OPC UA/plc service katmanını incele,
5. var olan logging/error handling yaklaşımına uy,
6. mevcut uygulamanın thread/UI refresh düzenini bozma.

Yeni bir ikinci framework veya paralel UI altyapısı oluşturma.

---

## 3. Panel / ekran hedefi

Hedef panel:

- **Vector VEC-VE 12"**
- **1024 × 768**
- dokunmatik
- Windows x64

UI masaüstü 1920×1080 düşünülerek tasarlanmamalı. Ana hedef **1024×768** olmalıdır.

Dokunmatik kullanım için:

- minimum buton yüksekliği yaklaşık 48 px,
- ana aksiyon butonları 56–72 px tercih edilebilir,
- küçük checkbox ve dar satırlar kullanılmamalı,
- kritik Start / Stop / Reset / Manual kontrolleri parmakla rahat kullanılmalıdır.

---

## 4. Görsel tasarım — VisionCut ile birebir uyumlu olmalı

### Ana renkler

```text
#1C2536   ana lacivert / ana yüzey
#161D2B   koyu sayfa altlığı
#243044   input / ikinci yüzey
#F47C20   ana vurgu / turuncu
#00DDFF   marka camgöbeği
#C53030   hata / tehlike
#D97706   uyarı
#2F855A   başarı / hazır
#E8EAED   birincil metin
#9FADC4   ikincil metin
#33415C   border / ayırıcı
```

### Font

Ana UI:

```text
Segoe UI
```

Sayısal göstergelerde tabular rakam kullanılmalı. Eğer mevcut projede özel number/readout style varsa onu kullan.

### UI hissi

- koyu endüstriyel HMI görünümü,
- düz ve sade,
- fazla gradient / dekoratif animasyon yok,
- status alanları hızlı okunmalı,
- normal = yeşil,
- warning = amber/turuncu,
- fault = kırmızı,
- inactive = koyu gri/lacivert,
- kamera uygulamasıyla görsel olarak tek ürün hissi vermeli.

---

## 5. Navigation / uygulama entegrasyonu

Bu ekran **aynı PySide6 uygulamasının bir sayfası** olacak.

### Vision ekranında

Bir buton:

```text
Makine Ekranı
```

Bu buton yeni makine kontrol sayfasını açar.

### Makine ekranında

Bir geri dönüş butonu:

```text
Kamera Ekranı
```

veya mevcut navigation standardı ne ise ona uy.

Bu durumda eski `ShowVisionScreen / VisionScreenRelease` mantığı ana navigation için zorunlu değildir; bunlar daha önce iki ayrı uygulamanın foreground geçişi için tasarlanmıştı.

Ancak PLC sözleşmesinde mevcut oldukları için tamamen silme. Var olan kod başka bir yerde kullanıyorsa uyumluluk korunmalı.

---

## 6. Makine çalışma senaryosu — UI bunu yansıtmalı

Normal çevrim:

```text
1. Makine hazır.
2. Operatör perdeyi fiziksel ileri/geri butonlarıyla manuel sürer.
3. Perde doğru yerde olduğunda Start verir.
4. Otomatik çevrim başlar.
5. Manuel perde besleme devre dışı kalır.
6. Perde baskısı aşağı iner.
7. Vision kesim çizgisini/oluğu doğrular.
8. Bıçak aşağı iner.
9. X ekseni sabit kesim hızıyla kesime başlar.
10. Kamera kesim boyunca Y çizgi konumunu üretir.
11. PLC Y eksenini çizgiyi takip edecek şekilde sürer.
12. X kesim sonuna ulaşır.
13. Bıçak yukarı çıkar.
14. X hızlı dönüş yapar.
15. Y 0/merkez konuma döner.
16. Baskı yukarı kalkar.
17. Çevrim tamamlanır.
18. Operatör kesilen yaklaşık 50 mm genişlikte parçayı alır.
19. Operatör perdeyi tekrar manuel sürer.
20. Yeni Start ile çevrim tekrarlar.
```

### Önemli proses kuralları

- Auto cycle aktifken manuel perde ileri/geri komutu PLC tarafından kabul edilmemeli.
- Bıçak aşağıdayken X dönüş hareketi başlamamalı.
- Baskı kalkmadan önce normal çevrim bitmiş olmalı.
- Vision hatası / heartbeat kaybı / servo hatası kesim sırasında kontrollü duruşa yol açmalı.
- Emergency safety zinciri UI tarafından uygulanmaz; PLC/safety tarafındadır.
- UI safety sistemi değildir. UI yalnız durum gösterir ve PLC'ye komut talebi gönderir.

---

## 7. X/Y motion yaklaşımı — ekranda gösterilecek önemli değerler

### X

X kesim boyunca sabit hızla gider.

Teorik başlangıç değeri:

```text
175 mm/s
```

Mekanik test sonrası gerçek maksimum/optimum kesim hızı belirlenecek ve makine ayarı olarak sabitlenecek.

Kesim yönü:

```text
X = 0 → yaklaşık 3600 mm
```

Dönüş daha yüksek hızla yapılabilir.

### Y

Y, dikim çizgisinin yavaş doğrusal sapmasını takip eder.

Gerçek proses örneği:

```text
3.6 m boyunca toplam ±24 mm civarı sapma
```

Bu ani bir sıçrama değildir; yavaş ve yaklaşık doğrusaldır.

Vision yaklaşık 60 Hz / 16–20 ms aralıkla ölçüm üretebilir.

PLC tarafındaki motion stratejisi:

```text
SMC_FollowPositionVelocity
```

ile Y için position + velocity setpoint takip yaklaşımıdır.

UI bu hesaplamayı yapmayacak. UI yalnızca debug/diagnostic amaçla aşağıdaki PLC değerlerini gösterebilir:

- X Actual Position
- X Actual Velocity
- Y Actual Position
- Y Set Position
- Y Set Velocity
- Vision Target X
- Vision Target Y
- Vision Slope
- LineValid
- Confidence

Bu değerler normal operatör ana sayfasında hepsi görünmek zorunda değildir; servis/mühendislik sekmesinde gösterilebilir.

---

## 8. Önerilen ekran yapısı

Uygulama kapsamlı olmak zorunda değil. Üç temel görünüm yeterlidir:

### A. Operatör / Ana Makine ekranı

Bu sayfa varsayılan makine sayfasıdır.

#### Üst status bar

Göster:

- Makine Durumu
- AUTO / MANUAL
- PLC Bağlantısı
- Vision Durumu
- Servo Durumu
- Emergency durumu
- Aktif alarm sayısı

Örnek status chip'leri:

```text
PLC: BAĞLI
VISION: HAZIR
X SERVO: HAZIR
Y SERVO: HAZIR
MOD: AUTO
```

#### Ana merkez alan

Büyük ve kolay okunur:

```text
X Pozisyonu:  1245.3 mm
Y Pozisyonu:    +8.42 mm
X Kesim Hızı: 175.0 mm/s
Çevrim Durumu: KESİM
```

Ayrıca progress bar:

```text
Kesim İlerlemesi
0 mm ----------------------- 3600 mm
             34 %
```

#### Proses durumu

Durum ikon/kartları:

```text
PERDE BASKISI
YUKARI / AŞAĞI

BIÇAK
YUKARI / AŞAĞI

VISION ÇİZGİ
GEÇERLİ / GEÇERSİZ

PERDE BESLEME
MANUEL AKTİF / KİLİTLİ
```

#### Ana komutlar

Butonlar:

```text
START
STOP
RESET
MANUAL / AUTO
KAMERA EKRANI
```

Start yalnız PLC tarafından izin verildiğinde aktif görünmeli.

UI tarafında sadece disable/enable görsel yardımcıdır. Asıl interlock PLC tarafında olmalıdır.

STOP normal kontrollü stop talebidir; Emergency yerine geçmez.

RESET alarm/reset talebidir.

---

### B. Manuel / Servis ekranı

Bu ekran operatör veya servis için hareket kontrollerini içerir.

#### X ekseni

```text
X -
X +

JOG Yavaş
JOG Hızlı
Actual Position
Servo Ready
Fault
```

#### Y ekseni

```text
Y -
Y +

JOG Yavaş
JOG Hızlı
Merkeze Git / Y=0
Actual Position
Servo Ready
Fault
```

#### Perde besleme

Fiziksel ileri/geri butonlar ana kontrol olsa da HMI diagnostic gösterimi yapılabilir:

```text
Perde İleri Input
Perde Geri Input
Besleme Motoru Çalışıyor
```

HMI'dan feed jog istenecekse yalnız MANUAL durumda PLC'ye momentary komut gönder.

#### Bıçak

```text
Bıçak Aşağı
Bıçak Yukarı
Blade Down feedback
Blade Up feedback
```

#### Perde baskısı

```text
Baskı Aşağı
Baskı Yukarı
Clamp Down feedback
Clamp Up feedback
```

Tüm manual butonlar basılı tutma / momentary mantıkla tasarlanabilir; ancak PLC interface'i buna göre yazılmalıdır.

---

### C. Ayarlar / Mühendislik ekranı

Normal operatör ekranından ayrılmalı.

Gösterilecek/ayarlanabilecek parametreler:

```text
X Kesim Hızı
X Dönüş Hızı
X Acceleration
X Deceleration
X Cut Start Position
X Cut End Position

Y Center Position
Y Software Min
Y Software Max
Y Max Velocity

Vision Timeout
Heartbeat Timeout
LineValid Timeout

Clamp Down Delay
Clamp Up Delay
Blade Down Delay
Blade Up Delay

OPC UA Endpoint
PLC IP
OPC UA Port
Security Policy / Mode
```

Kritik mekanik parametrelerin yanlışlıkla değiştirilmemesi için confirmation ve mümkünse engineering access kullan.

Mevcut VisionCut'ta rol sistemi yoksa yeni ağır bir kullanıcı sistemi kurmak zorunlu değildir. En azından ayarlar sayfasında “Mühendislik” uyarısı ve değişiklik confirmation kullanılabilir.

---

## 9. Alarm ekranı

Alarm listesi:

```text
Saat
Kod
Kaynak
Alarm
Durum
```

Örnek kaynaklar:

```text
PLC
X AXIS
Y AXIS
VISION
PNEUMATIC
OPC UA
```

VisionCut mevcut alarm kodları 100–603 aralığını kullanıyorsa PLC/makine tarafı için ayrı aralık kullan:

Öneri:

```text
1000–1099  Servo / Axis
1100–1199  Pneumatic
1200–1299  Vision/Communication
1300–1399  Process
1400–1499  Operator/Interlock
```

Örnek:

```text
1001 X Servo Not Ready
1002 Y Servo Not Ready
1101 Clamp Down Timeout
1102 Blade Down Timeout
1201 Vision Heartbeat Lost
1202 Vision Not Ready
1203 OPC UA Communication Lost
1204 Line Lost During Cut
1301 Y Tracking Limit Exceeded
1302 Cut Interrupted
1401 Start Interlock Not Satisfied
```

Alarm textleri kullanıcıya **Türkçe** gösterilmeli.

Kod ve yorumlar İngilizce olabilir.

---

## 10. OPC UA entegrasyonu

### Karar

Bu ekran ve VisionCut, aynı uygulama içinde olsa bile PLC verisi OPC UA üzerinden okunup yazılacaktır.

Mevcut Python library:

```text
asyncua
```

kullanılabilir.

### UaExpert'ten görülen gerçek CODESYS NodeId örneği

Mevcut PLC'den alınmış örnek:

```text
ns=4;s=|var|MAT LC-C07.Application.GVL.IPC_Y_POS
```

Variable:

```text
IPC_Y_POS
```

Type:

```text
Double
```

Bu bilgi çok önemlidir.

Eski VisionCut dokümanında sürücünün sabit olarak:

```text
ns=2;s=Brode.<tag>
```

formatını kullandığı belirtilmiştir.

**Yeni entegrasyonda bu hard-coded yaklaşımı kullanma.**

Gerçek MAT LC-C07 CODESYS server NodeId yapısı farklıdır.

### Gereken yaklaşım

OPC UA tag mapping konfigürasyon bazlı olmalıdır.

Örneğin:

```json
{
  "endpoint": "opc.tcp://192.168.x.x:4840",
  "nodes": {
    "ipc_y_pos": "ns=4;s=|var|MAT LC-C07.Application.GVL.IPC_Y_POS",
    "actual_x_mm": "...",
    "actual_y_mm": "...",
    "machine_ready": "...",
    "cycle_start_cmd": "..."
  }
}
```

Namespace index `ns=4` her deployment'ta sabit kabul edilmemelidir. Uygun olduğunda NamespaceArray / namespace URI üzerinden çözümleme tercih edilebilir. İlk sürümde tam NodeId konfigürasyonda saklanabilir.

### `BadCommunicationError`

UaExpert ekranında örnek tag için `BadCommunicationError` görülmüş.

Bu durum tek başına “NodeId yanlış” demek değildir.

Kontrol listesi:

1. PLC OPC UA Server gerçekten çalışıyor mu?
2. Endpoint doğru IP ve port mu?
3. Varsayılan port 4840 erişilebilir mi?
4. PLC ile IPC aynı ağda mı?
5. Security Policy / Security Mode uyumlu mu?
6. Sertifika trust gerekiyor mu?
7. CODESYS Symbol Configuration içinde ilgili GVL değişkeni publish edilmiş mi?
8. UAExpert session gerçekten Connected mı?
9. Namespace index ve NodeId browse ile doğrulanıyor mu?
10. PLC runtime restart / OPC UA server restart gerekli mi?
11. Variable access read/write izinleri doğru mu?

Codex agent OPC UA katmanını yazarken communication state'i UI'da açıkça göstermeli:

```text
Disconnected
Connecting
Connected
Degraded
Error
```

Bağlantı kopunca UI donmamalıdır.

---

## 11. OPC UA yazılım mimarisi önerisi

Repo yapısına uyacak şekilde benzer yapı hedeflenebilir:

```text
plc/
  opcua_client.py
  tag_map.py
  models.py

services/
  machine_service.py

ui/
  machine/
    machine_page.py
    manual_page.py
    settings_page.py
    alarm_page.py
```

Kesin isimleri mevcut repo naming standardına göre agent belirlesin.

### OPC UA worker

UI thread içinde bloklayan network çağrısı yapma.

Mevcut uygulamanın threading standardını koru.

Kaynak uygulamada QThread yaklaşımı kullanılıyor.

PLC read loop:

```text
yaklaşık 10–20 ms kritik motion/vision tagları
```

UI refresh:

```text
50–100 ms
```

olabilir.

UI'nın 10 ms'de paint yapması gerekmez.

Önemli distinction:

- PLC/Vision data acquisition hızlı olabilir.
- Operatör ekranı 10–20 FPS civarında rahatlıkla güncellenebilir.

---

## 12. Mevcut Vision / PLC sözleşmesi

Aşağıdaki taglar VisionCut kaynaklarında zaten tanımlanmıştır.

### PLC → PC / Vision

```text
MachineReady       BOOL
CutActive          BOOL
CutStart           BOOL
CutStop            BOOL
ServoReady         BOOL
EmergencyState     BOOL
BladeZDown         BOOL
FeedActive         BOOL
FeedComplete       BOOL
ShowVisionScreen   BOOL

ActualX_mm         REAL/FLOAT
ActualY_mm         REAL/FLOAT
X_Velocity         REAL/FLOAT
CutEndX_mm         REAL/FLOAT
StripLength_mm     REAL/FLOAT
Direction          INT
```

### PC / Vision → PLC

```text
VisionReady
LineValid
VisionFault
EndBufferReady
CutPermit
ZDownRequest
VisionScreenRelease

TargetY_mm
TargetX_mm
Confidence
ZDownAtX_mm
FaultCode
Heartbeat
```

### Önemli semantics

```text
TargetY_mm = MUTLAK Y hedefi
```

Mevcut Y üzerine eklenecek incremental offset değildir.

```text
TargetX_mm
```

ilgili TargetY'nin bıçak tarafından uygulanacağı X konumudur.

```text
CutPermit
```

proses kilididir; safety sinyali değildir.

Gerçek motion PLC'dedir.

---

## 13. Makine ekranı için ek OPC UA tag sözleşmesi

Aşağıdaki taglar makine UI'sının ihtiyaçları için PLC GVL tarafında oluşturulmalıdır. İsimler öneridir; PLC kodu ilerledikçe kesinleştirilebilir.

### PLC → UI status

```text
HMI_MachineReady              BOOL
HMI_AutoMode                  BOOL
HMI_ManualMode                BOOL
HMI_CycleActive               BOOL
HMI_CycleState                UINT/INT
HMI_CycleProgress             LREAL
HMI_StartPermitted            BOOL

HMI_EStopOK                   BOOL
HMI_SafetyOK                  BOOL

HMI_X_ServoReady              BOOL
HMI_X_Fault                   BOOL
HMI_X_FaultCode               UDINT/INT
HMI_X_ActualPos               LREAL
HMI_X_ActualVel               LREAL

HMI_Y_ServoReady              BOOL
HMI_Y_Fault                   BOOL
HMI_Y_FaultCode               UDINT/INT
HMI_Y_ActualPos               LREAL
HMI_Y_SetPos                  LREAL
HMI_Y_SetVel                  LREAL

HMI_ClampDown                 BOOL
HMI_ClampUp                   BOOL

HMI_BladeDown                 BOOL
HMI_BladeUp                   BOOL

HMI_FeedForwardInput          BOOL
HMI_FeedReverseInput          BOOL
HMI_FeedRunning               BOOL
HMI_FeedManualAllowed         BOOL

HMI_VisionReady               BOOL
HMI_LineValid                 BOOL
HMI_VisionFault               BOOL
HMI_VisionHeartbeatOK         BOOL
HMI_VisionTargetX             LREAL
HMI_VisionTargetY             LREAL
HMI_VisionConfidence          LREAL
HMI_VisionSlope               LREAL

HMI_AlarmActive               BOOL
HMI_AlarmCode                 UINT/INT
HMI_AlarmCount                UINT
```

### UI → PLC commands

UI command tagları **momentary/pulse request** mantığında tasarlanmalı.

```text
HMI_CmdStart                  BOOL
HMI_CmdStop                   BOOL
HMI_CmdReset                  BOOL

HMI_CmdAutoMode               BOOL
HMI_CmdManualMode             BOOL

HMI_CmdXJogPlus               BOOL
HMI_CmdXJogMinus              BOOL
HMI_CmdYJogPlus               BOOL
HMI_CmdYJogMinus              BOOL
HMI_CmdYCenter                BOOL

HMI_CmdBladeDown              BOOL
HMI_CmdBladeUp                BOOL

HMI_CmdClampDown              BOOL
HMI_CmdClampUp                BOOL
```

Eğer fiziksel feed butonları yeterliyse HMI'dan perde ileri/geri komutu ekleme. Servis ihtiyacı varsa:

```text
HMI_CmdFeedForward
HMI_CmdFeedReverse
```

eklenebilir.

### Parameter tags

```text
PAR_X_CutVelocity
PAR_X_ReturnVelocity
PAR_X_Acceleration
PAR_X_Deceleration
PAR_X_CutStartPos
PAR_X_CutEndPos

PAR_Y_CenterPos
PAR_Y_SoftwareMin
PAR_Y_SoftwareMax
PAR_Y_MaxVelocity

PAR_VisionTimeoutMs
PAR_HeartbeatTimeoutMs

PAR_ClampDownDelayMs
PAR_ClampUpDelayMs
PAR_BladeDownDelayMs
PAR_BladeUpDelayMs
```

Ayar yazımında:

- numeric range validation,
- confirmation,
- write result verification

uygulanmalı.

---

## 14. CycleState UI mapping

PLC state machine henüz geliştiriliyor. UI bunun numeric koduna doğrudan bağımlı kalmamalı; mapping tek yerde tutulmalı.

Öneri:

```text
0    INIT
10   IDLE
20   MANUAL_READY
30   WAIT_FOR_MATERIAL
40   AUTO_START_CHECK
50   CLAMP_DOWN
60   WAIT_VISION_LINE
70   BLADE_DOWN
80   CUTTING
90   CUT_FINISH
100  BLADE_UP
110  RETURN_X_Y
120  CLAMP_UP
130  CYCLE_COMPLETE

500  CONTROLLED_STOP
510  CUT_INTERRUPTED
520  RECOVERY
530  RECOVERY_BLADE_UP
540  RECOVERY_RETURN_X
550  RECOVERY_CENTER_Y
560  RECOVERY_CLAMP_UP

900  FAULT
```

UI Türkçe karşılıkları:

```text
INIT                Başlatılıyor
IDLE                Bekliyor
MANUAL_READY        Manuel Hazır
WAIT_FOR_MATERIAL   Perde Bekleniyor
AUTO_START_CHECK    Start Kontrolü
CLAMP_DOWN          Perde Baskısı İniyor
WAIT_VISION_LINE    Kamera Çizgi Bekleniyor
BLADE_DOWN          Bıçak İniyor
CUTTING             Kesim
CUT_FINISH          Kesim Tamamlanıyor
BLADE_UP            Bıçak Kalkıyor
RETURN_X_Y          Eksenler Dönüyor
CLAMP_UP            Baskı Kalkıyor
CYCLE_COMPLETE      Çevrim Tamam
CONTROLLED_STOP     Kontrollü Duruş
CUT_INTERRUPTED     Kesim Yarıda Kaldı
RECOVERY            Toparlanma
FAULT               Arıza
```

---

## 15. Start butonu davranışı

UI tarafında Start butonunun görsel enable koşulu:

```text
HMI_StartPermitted == TRUE
```

olmalıdır.

PLC tarafında gerçek interlock tekrar kontrol edilir.

Start'a basınca UI:

```text
HMI_CmdStart = TRUE
```

pulse üretir.

Önerilen pulse:

```text
100–250 ms
```

veya PLC command/ack yapısı varsa ona uy.

Buton basılı kaldığı sürece sürekli start yazma.

---

## 16. Stop davranışı

`STOP`:

- controlled stop request,
- emergency değildir,
- kesim yarıda kalırsa Recovery state açılabilir.

UI Stop butonu her zaman erişilebilir olmalı.

Stop sırasında UI kullanıcının mevcut durumu anlamasını sağlamalı:

```text
KESİM DURDURULUYOR
X kontrollü duruyor
Bıçak güvenli konuma alınıyor
```

gibi state texti PLC state üzerinden görüntülenebilir.

---

## 17. Recovery / yarım kesim ekranı

Kesim yarıda kalırsa otomatik devam etme varsayılan davranış değildir.

Göster:

```text
KESİM YARIDA KALDI

X: 1842.6 mm
Y: +8.42 mm
Bıçak: Aşağı/Yukarı
Baskı: Aşağı
Vision: Hata / Geçersiz
```

Önerilen recovery aksiyonu:

```text
TOPARLANMAYI BAŞLAT
```

PLC sırası:

```text
Bıçak Yukarı
→ X Başlangıca
→ Y Merkeze
→ Baskı Yukarı
→ IDLE / WAIT_FOR_MATERIAL
```

UI bu işlemleri tek tek doğrudan sürmemeli; PLC recovery state machine'i yürütmelidir.

---

## 18. OPC UA client davranışı

Codex agent şu prensiplere uymalı:

### Read

Kritik tagları batch/multi-read yapmaya çalış.

UI state modelini tek snapshot olarak güncelle.

### Write

Komutları ayrı service üzerinden yaz.

### Reconnect

Bağlantı kopunca:

```text
Connected -> Disconnected -> Reconnecting
```

state machine kullan.

Exponential backoff çok uzun olmamalı; makine içi local network.

### Failure

OPC UA koparsa UI:

- eski veriyi canlıymış gibi göstermemeli,
- readout'ları “—” / stale olarak işaretlemeli,
- status bar kırmızı “PLC BAĞLANTISI YOK” göstermeli,
- Start gibi komutları disable etmeli.

### Stale data

Her snapshot için timestamp tut.

Örneğin son PLC update > belirlenen timeout ise:

```text
STALE
```

kabul et.

---

## 19. Suggested Python data model

Agent repo yapısına göre uyarlayabilir.

Örnek:

```python
@dataclass(slots=True)
class MachineSnapshot:
    connected: bool = False
    machine_ready: bool = False
    auto_mode: bool = False
    manual_mode: bool = False
    cycle_active: bool = False
    cycle_state: int = 0
    cycle_progress: float = 0.0

    x_pos: float = 0.0
    x_vel: float = 0.0
    y_pos: float = 0.0
    y_set_pos: float = 0.0
    y_set_vel: float = 0.0

    clamp_down: bool = False
    blade_down: bool = False

    vision_ready: bool = False
    line_valid: bool = False
    vision_fault: bool = False

    alarm_active: bool = False
    alarm_code: int = 0
```

Hot path için mevcut proje yaklaşımına uygun olarak `dataclass(slots=True)` tercih edilebilir.

---

## 20. UI refresh modeli

Mevcut VisionCut yaklaşımına uygun olarak UI'yı worker eventleriyle 60 Hz bombardımana tutma.

Tercih:

```text
OPC UA worker:
10–20 ms veri acquisition

Machine state cache:
thread-safe / signal-safe snapshot

UI:
50–100 ms timer ile snapshot oku
```

Sayısal değerler için 10–20 FPS operatör ekranında yeterlidir.

Vision 60 FPS kalabilir.

---

## 21. Ana ekran layout önerisi — 1024×768

Yaklaşık:

```text
┌─────────────────────────────────────────────────────────────┐
│ BUFERA | MAKİNE       PLC ●  VISION ●  AUTO  ALARM: 0     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │ X POSITION   │ │ Y POSITION   │ │ ÇEVRİM DURUMU      │   │
│  │ 1245.3 mm    │ │ +8.42 mm     │ │ KESİM              │   │
│  └──────────────┘ └──────────────┘ └────────────────────┘   │
│                                                             │
│  Kesim İlerlemesi                                           │
│  ███████████████──────────────  34 %                       │
│                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐  │
│  │ BASKI     │ │ BIÇAK     │ │ VISION    │ │ BESLEME    │  │
│  │ AŞAĞI ●   │ │ AŞAĞI ●   │ │ VALID ●   │ │ KİLİTLİ    │  │
│  └───────────┘ └───────────┘ └───────────┘ └────────────┘  │
│                                                             │
│  [ START ]      [ STOP ]      [ RESET ]                     │
│                                                             │
│  [ MANUEL ] [ AYARLAR ] [ ALARMLAR ] [ KAMERA EKRANI ]     │
└─────────────────────────────────────────────────────────────┘
```

---

## 22. Buton renkleri

VisionCut temasına uygun:

```text
START
normal: #2F855A
text: #E8EAED

STOP
normal: #C53030
text: #E8EAED

RESET
normal: #D97706
text: #E8EAED

NAV / secondary
background: #243044
border: #33415C
active/accent: #F47C20

KAMERA EKRANI
accent: #00DDFF veya mevcut navigation standardı
```

Disabled:

```text
background: #243044
text: #68758A / mevcut muted token
```

---

## 23. Sayısal formatlar

```text
X Position       0.0 mm
Y Position       +0.00 mm
X Velocity       0.0 mm/s
Y Velocity       +0.000 mm/s
Confidence       0.000
Cycle Progress   0 %
```

Pozitif Y değerlerinde `+` işareti kullanmak debug sırasında faydalıdır.

---

## 24. Settings validation

Örnek aralıklar nihai PLC mekanik limitlerine göre kesinleşecek.

UI'da hard-code etme; config/tag metadata ile yönetmek daha iyi.

Geçici örnek:

```text
X Cut Velocity       > 0
X Cut End Position   0 .. mekanik strok
Y Software Min       mekanik limite uygun
Y Software Max       mekanik limite uygun
Y Max Velocity       > 0
Timeout              makul pozitif ms
```

Bir parameter write başarılı kabul edilmeden önce PLC'den geri okunarak doğrulanabilir.

---

## 25. İlk geliştirme kapsamı — Codex agent için görev sırası

### Faz 1 — UI skeleton

- mevcut repository ve navigation yapısını incele,
- “Makine Ekranı” navigation butonu ekle,
- MachinePage oluştur,
- tema ve mevcut komponentleri kullan,
- fake data ile ana ekranı çalıştır.

### Faz 2 — OPC UA infrastructure

- configurable endpoint,
- configurable node map,
- connection/reconnect,
- read snapshot,
- write command,
- diagnostics.

İlk test node:

```text
ns=4;s=|var|MAT LC-C07.Application.GVL.IPC_Y_POS
```

### Faz 3 — Live machine data

İlk etapta:

```text
X position
Y position
MachineReady
VisionReady
LineValid
CycleState
Alarm
```

bağla.

### Faz 4 — Commands

```text
Start
Stop
Reset
Auto/Manual
```

### Faz 5 — Manual / Service

```text
X/Y jog
Blade
Clamp
Y center
```

### Faz 6 — Settings / alarms

Parameter editing ve alarm history.

---

## 26. Agent için önemli “yapma” listesi

- Ayrı ikinci desktop app oluşturma.
- WPF/WinForms/.NET kullanma.
- Yeni bir tema sistemi yaratma.
- UI thread içinde OPC UA blocking read/write yapma.
- 60 Hz vision frame eventini doğrudan widget update'e bağlama.
- Safety mantığını UI'ya taşıma.
- PLC interlocklarını UI disable state'ine güvenerek bırakma.
- OPC UA NodeId'leri `ns=2;s=Brode.*` şeklinde hard-code etme.
- `ns=4` değerinin sonsuza kadar değişmeyeceğini varsayma.
- Connection error durumunda eski değerleri “canlı” gibi gösterme.
- Auto cycle sırasında manual jog komutlarını UI'dan gönderme.
- Her sayfada ayrı OPC UA client oluşturma; tek merkezi service kullan.

---

## 27. Agent için acceptance criteria

İlk teslim kabul kriterleri:

1. VisionCut ana ekranından “Makine Ekranı” açılıyor.
2. Ekran 1024×768 içinde taşmadan çalışıyor.
3. Görsel tasarım mevcut VisionCut theme ile uyumlu.
4. OPC UA endpoint config'den değiştirilebiliyor.
5. OPC UA node map config'den değiştirilebiliyor.
6. `IPC_Y_POS` test tagı okunabiliyor veya hata açıkça gösteriliyor.
7. PLC bağlantısı kaybolunca UI donmuyor.
8. Start/Stop/Reset command service altyapısı hazır.
9. Gerçek PLC tagları bağlanmadan fake/demo snapshot ile ekran test edilebiliyor.
10. Kod mevcut repo mimarisine uyuyor.
11. Makine ekranı mevcut Vision/kamera loop performansını düşürmüyor.
12. UI thread güvenli kalıyor.
13. Alarm ve connection status kullanıcıya açık şekilde görünüyor.

---

## 28. Kodlama sırasında bilinmesi gereken açık noktalar

Aşağıdaki noktalar PLC geliştirmesi devam ettikçe kesinleştirilecek:

- nihai X strok: 3500 mü 3600 mm mi,
- nihai Y software limit,
- bıçak/clamp feedback sensörlerinin kesin tagları,
- CycleState numeric kodlarının son hali,
- Start/Stop/Reset command handshake yapısı,
- alarm listesi ve alarm text mapping,
- PLC GVL tag adlarının son hali,
- OPC UA endpoint security configuration,
- actual CODESYS namespace table,
- parametre write yetkileri.

Agent bu değerleri kolay değiştirilebilir config/tag mapping yapısında tutmalı.

---

## 29. Entegrasyon açısından kritik yeni karar

Önceki dokümanda iki ayrı uygulama ve `ShowVisionScreen / VisionScreenRelease` foreground devri anlatılmıştı.

**Bu proje için güncel karar:**

```text
TEK UYGULAMA
Python + PySide6

Vision ekranı
   ↕
Makine ekranı
```

Dolayısıyla navigation uygulama içidir.

Makine ekranı mevcut uygulamaya “yabancı bir HMI” gibi değil, VisionCut'ın doğal bir bölümü gibi görünmelidir.

---

## 30. Codex agent'a kısa görev promptu

Aşağıdaki işi yap:

> Mevcut Operon VisionCut Python 3.13 / PySide6 6.11 projesini incele. Uygulamanın mevcut navigation, theme token, UI component, threading ve PLC service mimarisini bozmadan yeni bir “Makine Ekranı” sayfası ekle. Ekran 1024×768 dokunmatik panel için tasarlansın. Mevcut VisionCut renklerini ve Segoe UI fontunu kullan. Ana sayfada makine/PLC/Vision durumu, X/Y pozisyonları, çevrim durumu, kesim progress, bıçak, perde baskısı, Start/Stop/Reset ve navigation butonları olsun. Manual, Settings ve Alarms alt sayfaları için temiz bir yapı hazırla. PLC haberleşmesi OPC UA `asyncua` üzerinden merkezi bir service ile yapılsın; NodeId mapping hard-code edilmesin ve config üzerinden değiştirilebilsin. İlk gerçek test node'u `ns=4;s=|var|MAT LC-C07.Application.GVL.IPC_Y_POS`. Network çağrılarını UI thread'de bloklama. UI snapshot/timer mantığıyla yenilensin. Bağlantı kopması, stale data ve reconnect durumları kullanıcıya görünür olsun. Safety mantığı UI'da değil PLC'de kalacak. Kod mevcut repository naming/architecture standardına uysun ve var olan componentler mümkün olduğunca yeniden kullanılsın.

---

## 31. Referans — Tema tokenları

```python
COLORS = {
    "navy": "#1C2536",
    "page_bg": "#161D2B",
    "input_bg": "#243044",
    "accent_orange": "#F47C20",
    "brand_cyan": "#00DDFF",
    "danger": "#C53030",
    "warning": "#D97706",
    "success": "#2F855A",
    "text_primary": "#E8EAED",
    "text_secondary": "#9FADC4",
    "border": "#33415C",
}
```

Yeni duplicate token seti oluşturmak yerine mevcut proje tokenlarını bulup kullan.

---

## 32. Son hedef

Operatör tek uygulama içinde:

```text
Kamera
↔
Makine
```

ekranları arasında geçecek.

Vision uygulaması görüntü işleme ve çizgi takip verisini üretir.

PLC gerçek motion, sequence, interlock ve safety/process kontrolünü yürütür.

Makine ekranı ise PLC'nin durumunu sade ve güvenilir şekilde gösterir; operatör komutlarını PLC'ye iletir ve mühendislik/diagnostic erişimi sağlar.

UI, makineyi “kendi içinde kontrol eden ikinci bir otomasyon sistemi” olmamalıdır. Gerçek makine state'in tek kaynağı PLC'dir.
