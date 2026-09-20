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

