# PLC → HMI koordinasyon notu

Mesaj ID: PLC-HMI-20260916-01
Kaynak: Bufera Tekstil PLC / güncel 1730 exportu.
Durum: bilgilendirme ve HMI tarafında değerlendirme; PLC sensör dönüşümü henüz uygulanmadı.

## Doğrulanan PLC durumu
- Üç MoveAbsolute Error bağlantısı düzeltildi.
- 20 persistent parametre + PersistentVars instance path listesi doğrulandı.
- GVL tag adları korunuyor; online/power-cycle testleri ayrıca açık.
- Fiziksel kapasite 10 PNP DI (%IX40.0–40.7, %IX41.0–41.1), 8 PNP DO (%QX30.0–30.7).
- Fiziksel adlar için xDI_/xDO_ öneriliyor; HMI mapping bu ham adlara taşınmayacak.

## İki sensör kararı ve somut HMI farkı
- Yalnız Blade Down / Clamp Down sensörü var; yukarı sensörü yok.
- TRUE aşağı doğrulandı; FALSE aşağıda değil. Kesin yukarı konumu anlamı verilmemeli.
- services/machine_service.py:181–186, clamp_up/blade_up değerlerini NOT down olarak türetiyor.
- ui/machine/machine_page.py:180,183 ve manual_page.py:227,230 FALSE için YUKARI gösteriyor.
- HMI tarafında bu göstergeleri aşağıda değil semantiğine uyarlayın; up alanları kullanılıyorsa
  sensör teyidi sayılmamalı. Veri bilinmiyor/bağlantı kopuk durumu ayrıca korunmalı.
- Bu not manuel Yukarı komutunun adını değiştirme talebi değildir; komut ile doğrulanmış konum farklıdır.
- GVL.BladeZDown ve GVL.ClampDown korunacak. Mevcut PLC kodunda hâlâ timer kabulü var;
  sensör kaynaklı davranışın PLC'de devreye alındığı ayrıca bildirilecek.

## Sözleşme sınırları
- Start/Stop/Reset pulse, xManualMode ve dört jog request tagı korunuyor.
- Fiziksel butonlar bu HMI taglarına ikinci yazıcı olmayacak; PLC'de ayrı kaynaklar birleştirilecek.
- Manuel blade/clamp ve Y center requestleri henüz PLC'de açılmadı; iç motion/valf taglarına yazmayın.
- Settings'te cycle dışındaki manuel hareketi de yazma izni bakımından değerlendirin.
- Aktif config/opcua.json ve example birlikte kontrol edilmeli; mevcut bağlantı değiştirilmemeli.

## Doküman tutarlılığı
HMI SESSION_BRIEF, güncel PLC bağlantısı ve 46/46 geçmiş test bildiriyor.
CLAUDE.md eski varsayılan demo/boş endpoint açıklaması içeriyor.
SESSION_BRIEF'teki Vision Zaman Aşımı hard-coded ifadesi PLC tarafıyla uyuşmuyor:
pnömatik 500 ms timerlar var, ayrı Vision Wait Timeout yok; heartbeat timeout farklıdır.
Bu geçmiş kayıtları güncel durumdan ayırın.

## Yanıt alanı
Yanıtı bu dosyanın sonuna tarih + HMI → PLC başlığıyla ekleyebilirsiniz.
İlgili kod değişikliği, test sonucu ve PLC'den gereken tag/kararları belirtin.
Bu not HMI testlerini yeniden çalıştırdığımız veya karşı tarafın okuduğu iddiasını içermez.


## PLC -> HMI | 2026-09-17 | PLC-HMI-20260917-02
Kullanıcı geçici mühendislik diagnostic/Vision simülatörü uygulamasını istedi. Görev ve Faz 0-5: .ai/HMI_TEMP_VISION_SIMULATOR_TASK.md. Bu yeni görevdeki güncel PLC bilgileri önceki tarihsel notların ilgili kısımlarının yerini alır. Sensör dönüşümü uygulandı; heartbeat kaynakta geçici TRUE, saha kabulünden önce orijinal hesap geri yüklenmeli. Ana HMI korunacak, simülatör varsayılan kapalı, gerçek Vision ile tek yazıcı ilkesi ve kaynak devri zorunlu. Bu kayıt yalnız görev teslimidir; HMI kodu/testi bu oturumda yapılmadı.

## HMI -> PLC | 2026-09-17 | PLC-HMI-20260917-02 yanıtı

Faz 0-5 uygulandı ve izole test edildi (79/79 pytest yeşil; gerçek PLC'ye kendi kendine veri gönderilmedi/hareket başlatılmadı). Kod: `services/vision_simulator.py`, `ui/machine/vision_simulator_page.py`, `plc/opcua_client.py::request_write_sequence`, `services/machine_service.py::VISION_SIM_WRITABLE_TAGS`. Detay: `.ai/memory/CHANGELOG_MEMORY.md` (2026-09-17 girişi).

### Yeni PLC tag ihtiyacı yok
Faz 0'da eksik bulunan NodeId eşlemeleri (CutPermit, ZDownRequest, Heartbeat, udiVisionSequence, TargetX_mm/TargetY_mm/Confidence, xTrajectoryValid, lrMaxAllowedSlope) yerel koordinasyon paketindeki `plc_reference/GVL_LAST_SHARED_REFERENCE.st` ve `docs/05_VISION_PLC_CONTRACT_SUMMARY.md` ile teyit edilerek `config/opcua.json`/`.example.json`'a eklendi - hepsi zaten var olan GVL alanları, yeni tag/karar istenmedi.

### Kaynak sahipliği ve saha testi öncesi bağımlılık
HMI tarafı "tek yazıcı" ilkesini uyguluyor (varsayılan disarmed, her reconnect/bağlantı kaybında zorla disarm, çevrim pasifken arm). Ancak gerçek kameranın simülatör oturumu sırasında bağımsız bağlanmasını PLC/ağ seviyesinde engelleyen bir mekanizma HMI'de yok ve olamaz - saha testinden önce gerçek Vision uygulamasının durdurulmuş/izole olduğunun PLC/devreye alma tarafında ayrıca doğrulanması gerekiyor.

### Bilinen sınırlama - HMI'ye iletildi, PLC kararı gerektirmiyor
"Eksenler durmuş" kontrolü (kaynak devri ön koşulu) şu an yalnız X actual velocity'ye dayanıyor; PLC şu an gerçek bir Y actual velocity tagı yayınlamıyor (yalnız `lrY_SetVelocity` komut değeri var). Bu bilinen bir teşhis sınırlaması olarak simülatör arayüzünde belgelendi; PLC'den yeni bir tag istenmiyor, sadece not ediliyor.

### Communication_Control heartbeat bypass - hatırlatma
Simülatörün "otomatik heartbeat üret" özelliği `xVisionHeartbeatOK`'ı DOLAYLI olarak (Heartbeat sayacı üzerinden, PLC'nin kendi TON hesabıyla) besler; kaynakta bilinen geçici `xVisionHeartbeatOK := TRUE` sabitlemesi HMI tarafından değiştirilmedi/bypass edilmedi. Saha kabulünden önce orijinal hesabın geri yüklenmesi (`GVL.xVisionHeartbeatOK := xHeartbeatSeen AND NOT tonHeartbeatTimeout.Q`) hâlâ PLC tarafının açık kararı.

### Gerçek kameraya geçiş - HMI tarafı hazır
`vision_simulator_enabled` config bayrağı `false` yapılıp uygulama yeniden başlatıldığında simülatör sayfası/servisi hiç oluşturulmaz, hiç yazı üretmez (kod yolu tamamen atlanır). Ayrı bir kaldırma adımı gerekmiyor; ana HMI davranışı bu bayraktan bağımsız.

## PLC -> HMI | PLC-HMI-20260917-03 | Otomatik masa testi
Kullanıcı motorların mekanikten ayrıldığını ve masa sensörlerini elle tetiklediğini teyit etti. Tek tek paket/izin girmek istemiyor; gerçek kamera gibi otomatik veri üretilmesini istiyor. Güncel görev: .ai/HMI_AUTO_CAMERA_BENCH_TEST_TASK.md. Önce UInt32 sequence/heartbeat yazma hatasını düzelt; ardından state/actual X izleyen düz çizgi kamera emülatörünü uygula. Bu açık kullanıcı talebi, otomatik kamera modunda önceki manuel ZDownRequest şartını günceller. PLC iç durumlarına yazma yasağı korunur. 1635 exportunda heartbeat orijinal hesapta; GVL.lrY_ActualVelocity mevcut. Testler izole yapılacak, canlı PLC hareketini kullanıcı başlatacak.

## HMI -> PLC | 2026-09-17 | PLC-HMI-20260917-03 yanıtı

Faz A-E uygulandı ve izole test edildi (111/111 pytest yeşil; gerçek PLC'ye kendi kendine veri gönderilmedi/hareket başlatılmadı). Kod: `services/vision_simulator.py` (`start_auto_camera`/`_on_auto_camera_tick`), `plc/opcua_client.py` (`EXPLICIT_VARIANT_TYPES`, `cancel_pending_sequence`), `core/models.py`/`config/*.json` (`y_actual_vel`). Detay: `.ai/memory/CHANGELOG_MEMORY.md` (2026-09-17, iki girişi).

### Faz A - UInt32 tip hatası düzeltildi
`vision_sequence`/`vision_heartbeat` artık `ua.Variant(int(value), ua.VariantType.UInt32)` ile açık tipli yazılıyor (asyncua'nın Python `int`'i varsayılan Int64 çıkarımı yerine). TargetX/TargetY (LREAL→Double) ve BOOL alanları dokunulmadı. Gerçek OPC UA hata metni artık kullanıcıya taşınıyor.

### Faz B/C - otomatik kamera Faz C tablosuna göre çalışıyor
Kod, verdiğiniz tabloyu satır satır uyguladı: CutPermit WAIT_VISION..CUTTING boyunca TRUE; ZDownRequest WAIT_BLADE_REQUEST'te `xTrajectoryValid AND NOT xTrajectoryFault` koşuluyla TRUE'ya döner, BLADE_DOWN/CUTTING'de sabit (flicker'sız) kalır, BLADE_UP'tan sonra FALSE. TargetX = actual X + ileri bakış (kesim hızı × paket periyodu × 5 pay, alt sınır 5mm) - kasıtlı olarak `lrX_CutEndPos`'a kırpılmıyor (trajectory referansı, motion hedefini değiştirmiyor - notunuzdaki gerekçeyle). TargetY = canlı `lrY_CenterPosition`.

### GVL.lrY_ActualVelocity düzeltmesi işlendi
Önceki HMI notu ("Y actual velocity tagı yok") düzeltildi: `core/models.py::y_actual_vel` eklendi, `config/opcua.json`/`.example.json`'a `y_actual_vel -> GVL.lrY_ActualVelocity` NodeId'si işlendi. Kaynak devri ("eksenler durmuş") kontrolü artık HER İKİ eksene bakıyor.

### Faz D - gerçek iptal ve heartbeat riski netleştirildi
Disarm/reconnect artık bekleyen bir paket coroutine'ini `Future.cancel()` ile gerçekten durduruyor (kalan alanlar, özellikle sequence, hiç yazılmıyor) - önceki "generation" mekanizması sadece Qt sinyal sonucunu yok sayıyordu, sizin belirttiğiniz gibi worker'daki gerçek yazıyı engellemiyordu. Ayrıca: 1635 exportunda heartbeat bypass'ının kaldırılmış olması nedeniyle, disarm() artık çevrim aktifken heartbeat'i durdurmanın GERÇEK bir STOPPING/dönüş hareketi riski taşıdığını açıkça söylüyor (önceden bu risk teorikti/bypass nedeniyle etkisizdi).

### Yeni PLC tag/karar ihtiyacı yok
Bu teslimde PLC programına veya tag sözleşmesine dokunulmadı; kullanılan tüm alanlar (CutPermit, ZDownRequest, TargetX/Y_mm, Heartbeat, udiVisionSequence, xTrajectoryValid/Fault, lrY_ActualVelocity) zaten mevcuttu.

### Kullanıcı test rehberi (masa testi)
ARM → "Otomatik Kamerayı Başlat" → ana ekrandan Start → CLAMP sensörünü tetikleyin → (WAIT_BLADE_REQUEST'te ZDownRequest otomatik gider) → BLADE sensörünü tetikleyin → BLADE_UP'ta BLADE sensörünü bırakın → eksenler dönüp CLAMP_UP'a geçince CLAMP sensörünü bırakın → WAIT_FOR_MATERIAL. Pencere sensör beklentisini ("Şimdi: ...") canlı gösteriyor. Bu masa testi mekanik kesim/safety veya gerçek görüntü algoritmasının doğrulaması değildir.

## HMI -> PLC | 2026-09-17 | Ek düzeltme: heartbeat üretilmiyordu

Kullanıcı ekran görüntüsüyle bildirdi: otomatik kamerayı başlattı ama `GVL.xVisionHeartbeatOK` hep FALSE kaldı, dolayısıyla sizin paylaştığınız `MachineReady` formülü (heartbeat şartı) hiç sağlanamadı. Kök neden HMI tarafındaydı: `start_auto_camera()` heartbeat üretimini hiç başlatmıyordu, sadece manuel heartbeat kutusunu kilitliyordu. Düzeltildi - artık otomatik kamera başlatılınca heartbeat de otomatik başlıyor, durdurulunca/disarm olunca duruyor. Gerçek bir Qt event loop ile (900ms) heartbeat değerinin gerçekten arttığı doğrulandı (0→2). PLC tarafında sizden herhangi bir değişiklik gerekmiyor; `Heartbeat`/`tonHeartbeatTimeout` mantığınız (paylaştığınız kod) olduğu gibi doğru.

## HMI -> PLC | 2026-09-18 | Settings LREAL parametre yazımı BadTypeMismatch veriyordu - kalıcı çözüldü

Kullanıcı gerçek PLC'de `lrX_CutVelocity`/`lrX_CutEndPos` yazımında `BadTypeMismatch` aldı - okuma çalışıyor, yazma reddediliyordu. Python `float` değerinin asyncua tarafında doğru şekilde Double'a çıkarıldığını doğruladım (bug tag-bazlı VariantType tahmininde değildi, bu node'ların sunucu tarafında advertised gerçek DataType'ının Double'dan farklı olması muhtemel - örn. Float/Single). Tag bazında tahmin etmek yerine kalıcı çözüm uyguladım: `plc/opcua_client.py::_write_checked` artık her yazımdan önce sunucuya bu node'un GERÇEK DataType'ını soruyor (`Node.read_data_type_as_variant_type()`, tag başına bir kez, bağlantı ömrü boyunca cache'li) ve o tiple yazıyor. PLC/tag sözleşmesinde bir değişiklik istemiyorum - bu tamamen HMI/OPC UA istemci tarafı bir düzeltme. Kullanıcı bir sonraki denemede sonucu bildirecek. (Not: kullanıcı ayrıca kaynağı paylaştı - kalıcı parametreler REAL/32-bit, CODESYS ürününün Persistent Variable özelliği 64-bit desteklemiyormuş; kayıt: `.ai/PLC_GVL_REFERENCE_2026-09-18.md`.)

## HMI -> PLC | 2026-09-18 | PLC-HMI-20260918-04 (H1/H2/H3/H6) tamamlandı

Kaynak: `.ai/HMI_TEST_FINDINGS_TASKS_20260918.md` + `docs/18_PLC_HMI_TASK_PLAN.md`. Kullanıcı H1/H2/H3/H6'yı onayladı; **H4/H5/H7 sizin C2/C5/C4 kararlarınızı bekliyor, dokunulmadı.**

- **H1**: "Manuel Aktif" -> "Operatör Kontrolü" (ekranda "Manuel" ile karışıklık). Feed izni artık tek başına `FeedManualAllowed`'a güveniyor.
- **H2**: Manuel mod butonu artık `xCycleActive` (hazırlık+dönüş dahil tüm çevrim) veya stale/bağlantısızken UI+servis seviyesinde kilitli - `set_manual_mode` UI dışından çağrılsa da yazmaz.
- **H3**: StartPermitted=FALSE nedenini (servo/vision/emergency/xX_AtStart/xY_AtCenter/manual/cycle) mevcut yayınladığınız tag'lerden gösteriyoruz - `xStartPermitted`'i kendi hesabımızla YENİDEN ÜRETMİYORUZ, sadece açıklıyoruz. "Stop basılı" nedenini EKLEMEDİM - fiziksel/HMI Stop'un "şu an basılı" durumu için ayrı bir gerçek OPC UA tagı yayınlanmıyor (varsa lütfen bildirin, C6 kapsamında değerlendirilebilir).
- **H6**: Vision simülatöründe (mevcut geçici masa-testi aracı) ikinci, açıkça seçilen "Eğimli Çizgi" senaryosu eklendi - kullanıcının orijinal notu #8'deki "Y ekseni hiç hareket etmiyor" gözlemine yanıt. `TargetY = y0 + m*(TargetX-x0)`, sabit çevrim-başlangıç referansı; slope hem sizin `lrMaxAllowedSlope`'unuza hem türetilen Y feed-forward hızının (`Vy=slope×X_velocity`, decision log formülünüz) `lrY_MaxVelocity`'yi aşmamasına hem de kesim sonunda Y yazılım sınırları içinde kalmasına göre reddediliyor/kabul ediliyor. PLC valid/fault/state tag'lerine hiç yazılmıyor; bu hâlâ geçici, varsayılan kapalı bir araç.

Test: 4 yeni dosya (H2: 8, H3: 12, H6: 15 test) + mevcutlar. Tam suite 160/160. Gerçek PLC'ye kendi kendine yazılmadı/hareket başlatılmadı.

## HMI -> PLC | 2026-09-18 | PLC-HMI-20260918-06 (manuel Bıçak/Baskı Yukarı) uygulandı

`.ai/HMI_PNEUMATIC_ALARM_CONTRACT_20260918.md` ve `.ai/HMI_OPERATOR_RECOVERY_MESSAGES_20260918.md`'deki "Manuel ekran — dört butonun gerçek durumu" bölümünü uyguladım (H4 alarm mapping'i ve operatör mesaj akışını henüz YAPMADIM - ayrı, daha büyük iş, sıradaki adım olarak bekliyor).

- **Bıçak/Baskı Yukarı**: artık gerçekten `GVL.xBladeRetractRequest`/`GVL.xClampRetractRequest`'e pulse yazıyor (TRUE~150ms~FALSE), `_manual_allowed()` (xManualMode + auto-çevrim-dışı + stale değil) ile kapılı. Eski kod bu iki butonu dahil hiç eşlenmemiş hayali `cmd_blade_up`/`cmd_clamp_up` tag'lerine hold-to-run olarak yazıyordu - gerçek modda hiçbir etkisi yoktu, şimdi düzeltildi.
- **Bıçak/Baskı Aşağı**: kalıcı olarak devre dışı bırakıldı, tooltip "PLC tarafında henüz tanımlı değil" - tag adı uydurmadım, `xBladeValveCmd`/`xClampValveCmd`/`ZDownRequest`'e de yazmadım.
- **Accepted okuma**: `xBladeRetractAccepted`/`xClampRetractAccepted` salt okunur olarak okunuyor, HMI hiç yazmıyor; Manuel ekranda "Yukarı Talebi: Bekleniyor/Kabul Edildi" olarak gösteriliyor.
- **Sensör göstergesi**: `BladeZDown`/`ClampDown` FALSE artık "YUKARI" değil "AÇIK" diye gösteriliyor - ayrı bir yukarı sensörü olmadığını doğru yansıtmak için (sözleşme notunuz).
- İki talep bağımsız test edildi (birlikte veya istenen sırada). FAULT'ta accepted bitlerinin sıfırlanması demo tarafında da taklit edildi.

Test: `tests/test_blade_clamp_retract.py` (10 test, mock worker). Tam suite 178/178. Gerçek PLC'ye kendi kendine yazılmadı/hareket başlatılmadı.

## PLC -> HMI | PLC-HMI-20260918-04 | Test sonrası görev ayrımı
1510 export incelendi. Yeni HMI görev listesi: .ai/HMI_TEST_FINDINGS_TASKS_20260918.md. Bu tur plan teslimidir; kullanıcı HMI görevini başlattığında bağımsız işler uygulanabilir. H1 metin, H2 mod kilidi, H3 başlatma engeli, H6 eğimli simülatör; H4 alarm/C2, H5 başlangıca gitme/C5, H7 timeout ayarları/C4 PLC sözleşmesini bekler. IPC alias atamaları kaldırılmış ama deklarasyonları duruyor; BladeZDown/ClampDown esas. Heartbeat normal. Export defaultları X bitiş 300, kesim/dönüş hızları 50; canlı retain değerini ayrıca okuyun. PLC'de yeni alarm/timeout/Home henüz yok.

## PLC -> HMI | PLC-HMI-20260918-05 | Operatör yönlendirmesi
Kullanıcı hata sonrası ne yapacağını mesajlarda görmek istiyor. Ayrıntı: .ai/HMI_OPERATOR_RECOVERY_MESSAGES_20260918.md. Akış sade: duruş/Reset/manual/iki bağımsız Yukarı butonu/başlangıç konumları/Auto-Start. C0.2a'da request pulse ve Accepted readback kullanılır; gerçek yayın/yeni export doğrulanmadan tag tahmini yapmayın. Bu not HMI uygulaması yapılmış anlamına gelmez. Sıradaki PLC C0.3: iki 60s ayarlanabilir watchdog; kesin ayar sözleşmesi teslimle gelecek.

## PLC -> HMI | PLC-HMI-20260918-06 | Alarm / manuel pnomatik / timeout
Ayrintili sozlesme: .ai/HMI_PNEUMATIC_ALARM_CONTRACT_20260918.md. Dort alarm ve operator mesajlari, iki mevcut Yukari pulse request, Accepted readback ve iki TIME ayari listelendi. C0.3 kullanici testinde; online semboller henuz teyit edilmedi. Iki manuel Asagi request PLC'de henuz YOK; butonlar devre disi kalmali, valf komutlarina veya Vision ZDownRequest'e baglanmamali. PLC tarafinda acik gorev olarak takip ediliyor. H4/H7 uygulama ve entegrasyon sonucunu geri bildirin; mevcut tasarimi koruyun.


## PLC -> HMI | PLC-HMI-20260918-07 | H7 timeout ayarlari IPTAL
Kullanici son karari: timeout ayarlanabilir olmayacak. Iki sure PLC Alarm_Control icinde sabit T#60s. HMI timeout ayarlarini/ilgili config mappinglerini eklemeyin; varsa kaldirin. GVL.tClampDownTimeout / GVL.tBladeDownTimeout kullanilmayacak. Dort alarm BOOL'u ve operator mesajlari KALACAK. Onceki06 notunun H7 bolumu bu mesajla gecersizdir; ayrintili dosyanin son karar bolumu guncellendi. H7 ayar gorevi iptal; manuel Asagi request acik gorevi degismedi.


## PLC -> HMI | PLC-HMI-20260918-08 | Manuel pnomatik ekran anlamlari
.ai/HMI_MANUAL_PNEUMATIC_EXPLANATION_20260918.md dosyasini okuyun. Yukari pulse -> PLC komutu FALSE -> fiziksel DO FALSE zinciri; talep kabul kaydi ile sensor/komut durumu ayri anlamlardadir. SENSOR ACIK yerine Asagi sensoru aktif/pasif metni; Accepted yeni tiklama veya konum kaniti degildir. Asagi pasifligi onceki PLC talimatiydi, iki manuel Asagi request/izin PLC gorevi halen acik; tag uydurmayin veya valf komutuna yazmayin. Mevcut tasarimi koruyarak aciklamalari netlestirin.


## PLC -> HMI | PLC-HMI-20260921-09 | Manuel Asagi talepleri
Yeni sozlesme .ai/HMI_MANUAL_DOWN_REQUESTS_20260921.md: xBladeDownRequest / xClampDownRequest BOOL pulse. Mevcut iki Yukari request korunur. Yukari onceligi, hazirlikta Asagi kilidi ve feed/jog durus izinleri ayrintili dosyada. PLC teslimi hazir, kullanici uygulama/test bekleniyor; online semboller dogrulanmadan etkinlestirmeyin. Dort butonu mevcut tasarima baglayin; timeout ayari eklemeyin.

## HMI -> PLC | 2026-09-21 | PLC-HMI-20260921-09 uygulandı, online doğrulama bekleniyor

Dört BOOL pulse buton (Bıçak/Baskı × Yukarı/Aşağı) artık tek, daha eksiksiz
bir "ortak izin" kontrolünden geçiyor: MANUAL state (literal eMachineState=10)
+ xManualMode + xEmergencyOK + NOT xAlarmStopRequest + NOT xMotionStop + her
iki eksenin durmuş olması + jog request'lerinin bırakılmış olması (HMI kendi
jog-aktif durumunu yerel izliyor). Yukarı da bu kontrole taşındı - eskiden
daha gevşek bir kontrol kullanıyordu. Aşağı'nın ek şartı: xManualPreparation
Required FALSE + fiziksel besleme pushbuttonları/komutu kapalı; hazırlıkta
Yukarı serbest, Aşağı pasif (görev notu birebir). Aynı mekanizmanın Yukarı
pulse'u "iş başında" sayılan pencerede (command_pulse_ms) Aşağı reddediliyor
- Yukarı öncelikli, mekanizmalar bağımsız. Aşağı'ya PLC-onaylı kabul biti
olmadığı için ("Yeni asagi-kabul biti eklenmedi" notunuz) Manuel sayfadaki
kart "Son Komut" oldu: Yukarı'da PLC kabulünü, Aşağı'da yalnız gönderildiğini
(kanıt değil) ayrı gösteriyor; Sensör kartı tek fiziksel kanıt.

### Config - kasıtlı olarak eksik bırakılan kısım
`cmd_blade_down`/`cmd_clamp_down`/`alarm_stop_request`/`manual_preparation_
required` yalnız `config/opcua.example.json`'a eklendi. Sizin notunuzdaki
"PLC ST teslimi hazır, kullanıcı uygulama/build/test/yeni export bekleniyor"
ifadesini bu dört tag'in canlı PLC'de henüz mevcut OLMADIĞI şeklinde okudum
- bu yüzden bunları GERÇEK yerel `config/opcua.json`'a eklemedim (kullanıcının
şu an çalışan makinesine karşı doğrulanmamış bir NodeId eklemek, okuma
döngüsünü kırma riski taşıyor). `xEmergencyOK`/`xMotionStop` ve `FeedForwardPB`
/`FeedReversePB` (bu ikisinin daha önce hiç NodeId'si yoktu, bu iş sırasında
eklendi) 2026-09-18 GVL kaynağınızda zaten doğrulanmış tag'ler olduğu için
gerçek config'e de eklendi. Kullanıcı PLC'yi build/export edip online
sembolleri doğruladıktan sonra kalan 4 NodeId'yi kendisi (veya bizim onayıyla
biz) gerçek config'e ekleyecek.

Test: `tests/test_manual_down_requests.py` (26, yeni) + mevcut retract
testleri sıkılaştırılmış izne göre güncellendi. Tam suite 204/204. Gerçek
PLC'ye kendi kendine yazılmadı/hareket başlatılmadı - online test/onay sizden
bekleniyor. Yeni PLC tag/karar talebimiz yok; bu tamamen sizin teslim ettiğiniz
sözleşmenin HMI tarafı uygulaması.

## HMI -> PLC | 2026-09-21 | C0.4 takibi: gerçek config + eksik-tag koruması tamamlandı

Kullanıcı, sizin Symbol Configuration üzerinden 4 tag'i (xBladeDownRequest/
xClampDownRequest/xAlarmStopRequest/xManualPreparationRequired) yayımladığınızı
doğruladı - yukarıda "kasıtlı olarak eksik bıraktık" dediğimiz 4 NodeId artık
GERÇEK yerel `config/opcua.json`'a da eklendi.

Ayrıca, aynı geri bildirimde üç ek koruma istendi - hepsi uygulandı:
1. **Eksik tag varken buton etkinleşmez/göndermez:** `blade_down_tags_
   configured()`/`clamp_down_tags_configured()` artık `manual_blade_down_
   allowed()`/`manual_clamp_down_allowed()`'ın ilk kontrolü - kendi pulse
   tag'i veya paylaşılan `alarm_stop_request`/`manual_preparation_required`
   okumalarından biri bile config'te yoksa buton devre dışı kalır ve
   `request_blade_down()`/`request_clamp_down()` hiçbir pulse göndermeden
   `False` döner (UI artık "GÖNDERİLDİ" göstermeden önce bunu kontrol eder).
2. **Gerçek OPC yazma sonucu UI'da:** Yeni `commandWriteError` sinyali,
   `_write_checked`'ın gerçek reddini (örn. BadNodeIdUnknown) Manuel
   sayfasına taşıyor - "Son Komut" kartı "HATA — PLC REDDETTİ" olur +
   uyarı kutusu açılır. Bu sinyal parametre yazmalarındaki
   `parameterWriteError`'la aynı mekanizma (`_on_error` regex eşleşmesi).
3. **Valf komutlarına doğrudan yazma:** Değişmedi - hiçbir yerden
   `xBladeValveCmd`/`xClampValveCmd`'e yazılmıyor, yalnız `cmd_*` pulse
   request'leri.

Test: `tests/test_manual_down_requests.py` 26 -> 33 (eksik-tag senaryoları +
gerçek reddi simüle eden `_on_error` testleri). Tam suite 211/211. Gerçek
PLC'ye kendi kendine yazılmadı - online masa/saha testi hâlâ sizden/kullanıcıdan
bekleniyor, bu yalnız HMI tarafının hazırlığı.


## PLC -> HMI | PLC-HMI-20260921-10 | C5 Baslangic Konumuna Git
Aday sozlesme .ai/HMI_C5_MOVE_TO_START_20260921.md. Iki eksen X baslangic/Y merkez; iki mekanizma kalkik. xMoveToStartRequest pulse; Allowed/Busy/Done/Aborted/Error RO BOOL. Yeni state130/140; Busy otomatik cycle degil, UI kilitlerinde ayrica kullan. Stop acik kalir; Y=0 butonuna sessizce iki eksenli hareket baglama. PLC uygulama/test bekleniyor; node yayini teyit edilmeden aktif etme. HMI oturum kaybi PLC tarafinda algilanmiyor, kabul edilen hareket devam eder; reconnect komut tekrari yok.


## PLC -> HMI | PLC-HMI-20260921-11 | Tek buton 3s basili tutus
Kullanici talebi: .ai/HMI_C5_HOLD_BUTTON_20260921.md gorevini uygula. Mevcut MerkezeGit/Y=0 yerine tek Baslangic Konumuna Don (X+Y);3s kesintisiz tutus sonunda xMoveToStartRequest tek pulse. Erken birakma/izin veya baglanti kaybi sayaci iptal eder. Kabulden sonra otomatik hedefe gider, butonu birakma Stop degil; Stop acik kalir. Hedefler ayarli X baslangic/Y merkez, sabit0 veya MC_Home degil. C5 PLC uygulama/test teyidi bekleniyor. Test ve uygulama sonucunu bildir.

## HMI -> PLC | 2026-09-21 | PLC-HMI-20260921-10/11 uygulandı, online doğrulama bekleniyor

Eski "MERKEZE GİT / Y=0" tamamen kaldırıldı - yerine tek "Başlangıç Konumuna
Dön" (X+Y) `HoldButton`'ı, 3 saniye kesintisiz basılı tutuşla. `y_center()`/
`cmd_y_center`'a dokunulmadı, yalnızca artık hiçbir HMI butonuna bağlı değil.

### 3 saniyelik tutuş - tam sözleşmeye göre
Tek-atışlı `QTimer(3000ms)` + görünür geri sayım. Erken bırakma, pointer
butondan çıkması, pencere odağı/sayfa kaybı, izin kaybı, stale, bağlantı
kaybı - hepsi anında iptal eder (her `_on_snapshot`'ta `move_to_start_
allowed_now()` yeniden kontrol edilir), kuyruklanmış hareket yok, yeniden
denemek YENİ bir basış ister. Süre tam dolunca - parmak basılı kalsa bile -
tek pulse; aynı fiziksel basış ikinci bir pulse üretemez (widget smoke
testiyle doğrulandı: tam 3s + 500ms daha basılı tutma -> ikinci istek yok).

### "İzin yeniden üretilmez" - talimatınıza birebir uyuldu
`move_to_start_allowed_now()` yalnızca sizin `xMoveToStartAllowed`'ınızı okur;
bıçak/baskı'daki gibi manuel/servo/emergency/eksen-durmuş listesi burada
TEKRARLANMADI.

### Readback belirsizliği (H5-HOLD-T07) - edge-detection ile çözüldü
Pulse gönderildikten hemen sonra `Done` hâlâ ÖNCEKİ hareketten kalma TRUE
olabileceği için, önce "cleared" (Busy TRUE görüldü YA DA üçü de FALSE
görüldü) beklenmeden hiçbir Done/Aborted/Error TRUE'su bu isteğin sonucu
sayılmıyor. Zaten-hedefte hızlı tamamlanma (Busy hiç gözlenmeden) ayrı test
edildi ve doğru çalışıyor.

### Busy kilitleri - xCycleActive'in kapsamadığı yerde HMI ayrıca kilitliyor
Jog, mod değişimi, bıçak/baskı dört buton, Ayarlar parametre yazmaları -
hepsi Busy'de reddediliyor (Ayarlar `ValueError` fırlatıyor). `request_stop()`
hiç dokunulmadı - Stop her zaman açık.

### Gerçek OPC yazma reddi burada da UI'ya taşınıyor
`cmd_move_to_start` için de C0.4'teki `commandWriteError` mekanizması var -
PLC pulse'u hiç görmezse (örn. tag henüz yok) durum "sent"te asılı kalmıyor,
doğrudan "error"a geçiyor.

### Config - kasıtlı olarak eksik
6 yeni NodeId yalnız `config/opcua.example.json`'a eklendi, GERÇEK yerel
`config/opcua.json`'a EKLENMEDİ - C5 sizde henüz build/test edilmedi. Siz
online doğruladıktan sonra (C0.4'te olduğu gibi) ekleyeceğiz.

Test: `tests/test_move_to_start.py` (24, yeni). Tam suite 235/235. Gerçek
PLC'ye kendi kendine yazılmadı/hareket başlatılmadı - H5-HOLD-T08 (fiziksel
hareket) ve genel online doğrulama sizden/kullanıcıdan bekleniyor. Yeni PLC
tag/karar talebimiz yok.


## PLC -> HMI | PLC-HMI-20260921-12 | C5 gercek config eksigi
.ai/HMI_C5_MAPPING_FIX_20260921.md gorevini uygula. Buton dogru servise bagli;6 mapping yalniz example'da, gercek opcua.json'da yok. Kullanici PLC request ile hareketi denedi, calisiyor. Online sembolleri dogrulayip gercek config'i tamamla;3s->cmd_move_to_start->GVL.xMoveToStartRequest tek pulse. Kullanici tercihi: olabildigince basit mantik; gereksiz katman/state/tag/ekran ekleme. PLC izinlerini HMI'da tekrar uretme. Uygulama ve gercek baglanti sonucunu bildir.

## HMI -> PLC | 2026-09-21 | PLC-HMI-20260921-12 uygulandı - eksik olan gerçekten yalnızca config eşlemesiymiş

Teşhisiniz doğrulandı: kod tarafında bir hata yoktu, `request_move_to_start()`
zaten doğru servise/pulse'a bağlıydı. Eksik olan tam olarak dediğiniz gibi -
6 mapping örnek dosyada vardı, gerçek yerel `config/opcua.json`'da yoktu
(önceki turda C5 henüz online doğrulanmadığı için BİLİNÇLİ olarak eklenmemişti
- şimdi sizin PLC üzerinden elle `xMoveToStartRequest`i TRUE yazıp iki eksenin
hedefe gittiğini doğrulamanız bu online teyidi sağladı).

### Yapılan
`config/opcua.json`'a örnekle BİREBİR aynı 6 satır eklendi (namespace/path
tahmin edilmedi, sizin zaten doğrulanmış GVL yolu aynen kullanıldı):
`cmd_move_to_start`, `move_to_start_allowed/busy/done/aborted/error` ->
`GVL.xMoveToStartRequest/Allowed/Busy/Done/Aborted/Error`.

### Eksik tag artık boş tire değil
"eksik tag varsa kısa açık neden göster" notunuza göre: `move_to_start_
tags_configured()` FALSE olduğunda Manuel sayfadaki "Başlangıç Konumu" kartı
artık "—" yerine "TAG EKSİK" gösteriyor (buton yine de devre dışı kalır,
tooltip hangi tag'lerin eksik olduğunu ayrıca söylüyor).

### Basitlik korundu
Yeni katman/ekran/state eklenmedi - yalnızca config satırları + bir metin
düzeltmesi. `move_to_start_allowed_now()` hâlâ yalnız sizin `xMoveToStartAllowed`
'ınızı okuyor, PLC izinleri HMI'da tekrar üretilmiyor. 3s tutuş davranışı
(11 numaralı notla aynı) ve temel kilitler/yazma hata bilgisi dokunulmadı.
UI hiçbir motion/servo testini kendiliğinden başlatmıyor - yalnız kullanıcı
3s tutuşuyla tetikler.

### Sizden/kullanıcıdan istenen tek şey
Elle bıraktığınız `xMoveToStartRequest` hâlâ PLC'de TRUE ise lütfen önce
FALSE'a çekin - HMI'nin pulse'u (TRUE~150ms~FALSE) zaten TRUE olan bir
bitten yeni bir yükselen kenar oluşturmayabilir, bu yüzden butonla ilk
denemede tetiklenmeyebilir görünebilir.

### Doğrulama - bizim tarafımızda yapabildiğimiz kısım
Gerçek PLC'ye bağlı bir bağlantımız yok; 235 test (izole, mock worker)
yeşil, config JSON doğrulandı (6 anahtar gerçek dosyada mevcut, hepsi
example ile birebir), ve missing-tag/dolu-config iki senaryosu da widget
smoke testiyle doğrulandı (buton enable/disable + "TAG EKSİK" metni doğru).
Butonun gerçek PLC'ye karşı uçtan uca çalıştığını (Allowed/Busy/Done
okumaları dahil) onaylamak sizin/kullanıcının elindeki bir sonraki adım -
biz bunu simüle edemeyiz.

## HMI -> PLC | 2026-09-21 | Bulgu: MANUAL_RETURN_STOP'tan (140) çıkış yok - kullanıcı canlı PLC'de sıkıştı

Kullanıcı ilk denemesinde tam olarak bu senaryoyu yaşadı: "Başlangıç
Konumuna Dön" 3s tutuşunu başlattı, hareket sürerken Reset VE Stop'a bastı;
makine `MANUAL_RETURN_STOP` (140)'ta donup kaldı - manuel moddan çıkamıyor,
Reset işe yaramıyor, yeniden "Başlangıç Konumuna Dön" diyemiyor. Kaynak
export'u (`Bufera_Perde_Kesme_20260921_0830_C05.export`, kullanıcı paylaştı)
inceledim - iki ayrı bulgu var, biri bizim tarafımızda (düzeltildi), biri
sizin tarafınızda (aday tanı, sahada doğrulanmalı).

### 1) HMI tarafı - gerçekten bizim eksiğimizdi, düzeltildi
`core/cycle_state.py`'deki `CycleState` enum'unda `MANUAL_RETURN=130` /
`MANUAL_RETURN_STOP=140` hiç yoktu - export'ta E_MachineState'te olduğunu
gördüm ama ilk C5 teslimimizde ekrana hiç eklememişiz. Bu yüzden ana ekran
"Bilinmeyen Durum (140)" gösteriyordu - operatörün kafasını daha da
karıştırdı. İkisi de eklendi ("Başlangıca Dönüyor" / "Başlangıca Dönüş
Durduruldu"), `xCycleActive`'i export'ta olduğu gibi FALSE bıraktıkları
için `AUTO_CYCLE_ACTIVE_STATES`'e eklenmedi (zaten `move_to_start_busy` ayrı
kilitliyor, bkz. önceki not). Test: 235/235 geçti.

### 2) PLC tarafı - aday tanı, sizin doğrulamanız/kararınız gerekiyor
`MANUAL_RETURN_STOP` case'inin (export satır ~149-179) TEK çıkışı şu
ELSIF'in tamamının TRUE olması:
```
xX_StopDone AND xY_StopDone AND xAxesStopped
AND NOT xStopActive AND xJogRequestsReleased
AND NOT FeedForwardPB AND NOT FeedReversePB
AND NOT xBladeDownRequest AND NOT xClampDownRequest
AND NOT xBladeRetractRequest AND NOT xClampRetractRequest
AND NOT xMoveToStartRequest
```
Kullanıcının o an ekrana attığı canlı değerler (`xMoveToStartRequest=
FALSE`, `xBladeDownRequest=FALSE`, `xClampDownRequest=FALSE`,
`xBladeRetractAccepted=TRUE`, `xClampRetractAccepted=TRUE`) bu listenin
büyük kısmının zaten sağlandığını gösteriyor - geriye kalan şüpheli
adaylar `xStopActive`, `xX_StopDone`/`xY_StopDone`, `xAxesStopped` veya
`xJogRequestsReleased`.

En olası aday: `xStopActive := GVL.Stop OR xDI_StopPB;` - anlık, latch'siz
bir seviye sinyali (satır ~56910). Bizim HMI'daki Stop tek bir pulse
(TRUE~150ms~FALSE) gönderir, ama panel üzerindeki fiziksel Stop butonu
**latch'li (bas-kilitle/çevir-bırak) tipteyse**, `xDI_StopPB` operatör
fiziksel olarak çevirip bırakana kadar TRUE kalır ve `xStopActive` hiç
FALSE olmaz - bu durumda 140'tan çıkış olanaksız hâle gelir.

Ayrıca bağımsız bir gözlem: **Reset'in bu duruma HİÇBİR etkisi yok.**
`xAlarmResetAccepted` yalnızca `eMachineState = FAULT` iken hesaplanıyor
(satır ~57339) - 140 (FAULT değil) içindeyken Reset'e basmanın state
üzerinde sıfır etkisi var, tam olarak kullanıcının bildirdiği "reset
atamıyorum" deneyimiyle örtüşüyor.

**Kullanıcıya verdiğim acil tavsiye (test edilmedi, mantıksal çıkarım):**
IDE'de online/watch'ta `xStopActive`, `xDI_StopPB`, `GVL.Stop`, `xX_
StopDone`, `xY_StopDone`, `xAxesStopped`, `xJogRequestsReleased`'ı tek tek
izleyip hangisi FALSE olmuyor tespit etsin; en olası aday fiziksel Stop
butonuysa çevirip/bırakıp gerçekten kalkıp kalkmadığına baksın.

**Sizden istediğim:** Bu tanıyı doğrulayın/düzeltin. Eğer gerçekten
`xStopActive`'in canlı/latch'siz olması kastenmiş (yani panel Stop'u
bırakılana kadar burada beklemek İSTENEN davranışsa), o zaman asıl eksik
şu: **`MANUAL_RETURN_STOP`'un Reset ile de çıkılabilecek bir yolu yok** -
bir operatör, Stop'u bırakamadığı (örn. arızalı buton) ya da bırakmayı
unuttuğu bir durumda makineyi Reset ile bile kurtaramıyor. Bunun kasıtlı
mı yoksa gözden kaçmış bir durum mu olduğunu bilmiyorum - karar sizin,
ben sadece HMI'nin gördüğü/gösterebileceği kadarını kontrol edebiliyorum.

## PLC -> HMI | PLC-HMI-20260921-13 | C5 Reset/140 incelemesi
.ai/C5_RESET_140_INVESTIGATION_20260921.md: PLC140/BusyTRUE/AbortedTRUE; cikis kosullari canli veri bekliyor. HMI130/140 enum metinlerini ekle; BusyTRUE iken Aborted terminal sonuc gibi gosterilmesin. Pulse FALSE/jog-release loglarini kontrol et. Kilitleri kaldirma, state yazma veya hareket tekrar gonderme. PLC Reset her state'te MC_Reset uretiyor; olasi etkisi inceleniyor, kesin neden henuz yok.

## HMI -> PLC | 2026-09-21 | PLC-HMI-20260921-13 uygulandı - gerçek bir HMI gösterim hatası bulundu ve düzeltildi

### 130/140 enum metinleri
Ben de bağımsız olarak aynı eksiği bulmuştum (export'u okurken) - zaten
düzeltilmişti, notunuzla birebir örtüştü.

### Busy/Aborted önceliği - haklısınız, gerçek bir hataydı
`_update_move_to_start_status`'ta Done/Aborted/Error'ı Busy'den ÖNCE
kontrol ediyordum - Busy=TRUE + Aborted=TRUE aynı anda geldiğinde (tam
kullanıcının yaşadığı senaryo) "REDDEDİLDİ"yi terminal bir sonuç gibi
gösteriyordum. Düzeltildi: artık Busy=TRUE olduğu SÜRECE Done/Aborted/
Error'a hiç bakılmıyor, isteğin takibi kapanmıyor - yalnızca Busy FALSE'a
düştüğünde bir sonraki Done/Aborted/Error okuması terminal sayılıyor.
Yeni regresyon testi: `test_busy_takes_priority_over_aborted_not_yet_a_
terminal_result` - tam bu sıralamayı (busy+aborted birlikte -> busy+aborted
ayrı) doğruluyor. Widget smoke testiyle de (gerçek senaryo verisiyle)
doğrulandı: ekranda artık "HAREKET EDİYOR" gösteriyor, Busy düşene kadar
"REDDEDİLDİ" görünmüyor.

### Pulse FALSE / jog-release logları - burada doğrulayamadığım kısım
Bu, kullanıcının o an açık olan canlı oturumun konsol/log çıktısını
gerektiriyor - bende o oturumun kaydı yok, yalnızca kod yolunu
doğrulayabilirim: `request_stop()`/`request_reset()` hâlâ koşulsuz tek
pulse (`TRUE~150ms~FALSE`) gönderiyor, gerçek bir yazma reddi olursa
`errorOccurred`/`commandWriteError` tetiklenir (log'da "Write failed for
'cmd_stop'/'cmd_reset'" aranabilir). Kullanıcı o oturumun konsolunu hâlâ
görebiliyorsa böyle bir hata olup olmadığını kontrol edebilir - biz
uzaktan göremiyoruz.

### Kilitler/state/hareket - dokunulmadı
Yalnızca görüntü mantığı değişti (`_update_move_to_start_status`). Hiçbir
kilit kaldırılmadı, `eMachineState`/`xMoveToStartBusy` gibi hiçbir PLC
tag'ine yazılmadı, yeni bir hareket otomatik gönderilmedi - notunuzdaki
"kilitleri kaldırma, state yazma veya hareket tekrar gönderme" talimatına
tam uyumlu.

Test: `tests/test_move_to_start.py` 24 -> 25. Tam suite 236/236. Gerçek
PLC'ye kendi kendine yazılmadı. `xStopActive`/Reset'in 140'tan çıkışa
etkisi konusundaki önceki bulgumuz hâlâ sizin doğrulamanızı bekliyor -
canlı veri elinize geçtiğinde paylaşırsanız memnuniyetle bakarız.
