# Geçici mühendislik diagnostic ekranı ve Vision veri simülatörü

Görev ID: PLC-HMI-20260917-02. Kullanıcı talebi: HMI agent bu planı faz sırasıyla uygulasın. Bu dosya uygulama görevidir; yalnız README/aday üretmek teslim değildir. Mevcut mimari korunacak. Gerçek PLC üzerinde test/çevrim başlatma bu geliştirme görevinin parçası değildir; kullanıcı CODESYS uygulamasını ve saha testini yapar.

## Amaç ve kesin kapsam
Bu sayfa GEÇİCİDİR. Yalnız mühendislerin eriştiği diagnostic görünümünde gerçek kamera uygulamasının PLC'ye göndereceği verileri üretir. HMI ana dinamikleri, mevcut operatör sayfaları, Start/Stop/Reset, jog, ayarlar, alarm ve gerçek PLC okumaları korunur. Mevcut DemoSimulator ile karıştırılmaz: DemoSimulator PLC olmayan ortamın sahte kaynağıdır; yeni özellik gerçek PLC'ye sınırlı Vision girdileri gönderir. Ana MachineSnapshot sahte verilerle doldurulmaz. Özellik kapalıyken hiçbir Vision yazısı, heartbeat, timer veya reconnect yan etkisi oluşmaz. Normal müşteri dağıtımında varsayılan kapalıdır; kaldırılabilir olmalıdır.

## Önce okunacak kaynaklar
- CLAUDE.md, .ai/memory/SESSION_BRIEF.md, .ai/RULES.md, .ai/Codex_Codesys.md.
- UI için .ai/skills/design/DESIGN.tr.md; mevcut theme/widgets bileşenlerini kullan.
- docs/BUFERA_HMI_PLC_ENTEGRASYON_GOREV_PLANI.md içindeki Vision bölümü.
- PLC kökü: C:/Users/agedik/Documents/ChatGPT/Bufera Tekstil PLC/BUFERA_TEKSTIL_MASTER_CONTEXT_PACK_2026-09-16.
- Bu kökte docs/05_VISION_PLC_CONTRACT_SUMMARY.md, docs/06_HMI_PLC_CONTRACT_SUMMARY.md ve references/BUFERA_PLC_VISION_TAG_SOZLESMESI.html.
- plc_export/Bufera_Perde_Kesme_20260917_1130.export: Communication_Control, Logic_Control, Trajectories_Calculate, GVL. Yeni export varsa önce farkını raporla.
- Kaynak/doküman farklarını sessizce düzeltme. HMI eski notlarının aksine pnömatik kabul timerları kaldırıldı, aşağı sensörleri gerçek DI'dan okunuyor. Sensör FALSE kesin yukarı demek değil.

## Bilinen saha durumu ve engeller
Jog ve CLAMP_DOWN -> WAIT_VISION -> WAIT_BLADE_REQUEST kullanıcı tarafından denenmiş. TargetX=0 / actual X≈0 nedeniyle trajectory fault görülmüş. xTrajectoryValid elle TRUE yapılması fault'u temizlemiyor. Bu sonuçlar tam çevrim doğrulaması değildir.
Kullanıcı Communication_Control'da xVisionHeartbeatOK := TRUE yaparak heartbeat kontrolünü GEÇİCİ kapattı. Bu, 1130 exportundan bilinen kaynak farkıdır. Simülatörün saha kabulü öncesi kullanıcı orijinal hesabı güvenli duruşta geri getirmeli:
GVL.xVisionHeartbeatOK := xHeartbeatSeen AND NOT tonHeartbeatTimeout.Q;
Agent PLC'yi değiştirmez, bypass eklemez. Aktif cycle sırasında heartbeat kesilmesi/Stop, STOPPING -> BLADE_UP -> RETURN_AXES akışına neden olabilir; bunlar hareket enerjisini kesme garantisi değildir. Reset FAULT'tan recovery hareketi başlatabilir. Yazılım simülatörü safety sistemi değildir.

## Yazma sözleşmesi — kapalı izin listesi
Yalnız aşağıdaki mevcut Vision->PLC alanları yazılabilir; NodeId config/tag_map ile çözülür, tahmin/hard-code yapılmaz:
- BOOL: VisionReady, LineValid, VisionFault, CutPermit, ZDownRequest.
- LREAL / OPC UA Double: TargetX_mm, TargetY_mm, Confidence (opsiyonel, 0..1).
- UDINT / OPC UA UInt32: Heartbeat, udiVisionSequence.
PLC'nin hesapladığı xVisionHeartbeatOK, xTrajectoryValid, xTrajectoryFault, MachineReady, ServoReady, state, gerçek pozisyonlar, sensörler, safety/DI/DO, motion execute ve valf komutlarına ASLA yazma. Simülatör Start/Stop/Reset veya mode/jog komutu üretmez; bunlar mevcut operatör yollarında kalır. Kalıcı makine parametrelerini değiştirmez.

## Faz 0 — İnceleme ve kayıt
- [ ] İlgili mevcut servis, OPC worker, tag/config, erişim kapısı ve testleri incele; kullanıcı değişikliklerini koru.
- [ ] Eksik Vision tag eşlemeleri, gerçek export tipleri, yazma izinleri ve doküman farklarını kısa tabloda raporla.
- [ ] Aktif ve example config uyumunu koru; endpoint/kimlik bilgilerini değiştirme veya rapora dökme.
- [ ] Yeni PLC tag/state/owner handshake gerekirse burada uydurma: ayrı karar olarak köprüye yaz ve PLC DECISION_LOG güncellemesini öner. Bağımsız UI/test işlerine devam et.

## Faz 1 — İzolasyon ve yazıcı sahipliği
- [ ] Ayrı, varsayılan FALSE feature flag; normal kullanımda sayfa ve servis aktif olmaz. Mevcut mühendislik erişimini incele; yalnız gizli menü veya hard-coded parola yetki kontrolü sayılmaz. Servis yazma kapısında da yetki/oturum kontrolü olsun.
- [ ] Açılış ve her reconnect sonrası DISARMED; önceki armed durumunu diske kaydetme, otomatik yeniden başlatma yok.
- [ ] REAL ve SIMULATOR kaynak seçimi birbirini dışlasın; gerçek kamera entegrasyon modunda simülatör sıfır yazı üretir. Gerçek kamera başka bir uygulama olduğundan HMI flag tek başına küresel kilit değildir. İlk saha kullanımında gerçek Vision yazıcısı durdurulmuş/izole edilmiş olmalı; bunu arayüz ve devreye alma rehberinde açıkla. Sahiplik bilinmiyorsa arm kapalı; heartbeat sessizliği tek başına sahiplik kanıtı değildir.
- [ ] Gerçek kameranın simülatör oturumu sırasında bağımsız bağlanmasını teknik olarak engelleyen mekanizma mevcut değilse bunu garanti edilmiş gösterme. Eşzamanlı kullanım yasak, dağıtım/erişim izolasyonu ön koşuludur. Ortak PLC owner handshake istenirse yeni sözleşme kararı olarak raporla.
- [ ] Kaynak değişimi yalnız cycle pasif ve eksenler durmuşken. Aynı HMI içinde iki simülatör oturumunu önle. Bekleyen yazılara oturum/generation kimliği koy; disarm/reconnect sonrası eski kuyruk veya retry çalışmasın.

## Faz 2 — Sıralı Vision üreticisi
- [ ] UI -> MachineService -> mevcut PLC katmanı sınırını koru. UI doğrudan OPC client kullanmaz. Özelliğe özel küçük modül olabilir; genel servis refactor yapma.
- [ ] Paket gönderimi tek sıralı async işlem: hedefler ve paket BOOL/Confidence alanları başarılı yazıldıktan SONRA udiVisionSequence. Arka arkaya fire-and-forget request_write çağrıları sıralama kanıtı değildir. Başarısız/kısmi pakette sequence artırma; hatayı göster, otomatik tekrar oynatma yok.
- [ ] Her paketin payload'ını başta sabitle; paralel paketleri serialize et. OPC yazıları atomik değildir: PLC bazı BOOL'ları sequence dışında okur; bunu gizleme ve arming/izin sırasını buna göre tasarla.
- [ ] İlk sequence ve heartbeat mevcut PLC değerinden alınır, UInt32 taşması tanımlı (mod 2^32), sayılar farklı amaçlarla bağımsız ilerler. Her UI refresh sequence artırmaz.
- [ ] Heartbeat otomatik periyodik üretim ayrı kontrol olsun; periyot gerçek tVisionHeartbeatTimeout değerinden kısa ve anlamlı paylı doğrulanır. Sabit 2 saniye varsayma. Watchdog durumu yalnız okunur.
- [ ] Başarılı write, readback ve PLC kabul/trajectory sonucu ayrı gösterilir; readback atomiklik veya global sahiplik kanıtı değildir. Bağlantı/veri stale ise yeni paket gönderme.

## Faz 3 — Geçici diagnostic sayfa
- [ ] Mevcut tema/servis erişimini kullan. Sayfada belirgin GEÇİCİ VISION SİMÜLATÖRÜ, kaynak, bağlı/disarmed/armed ve son yazma hatası göster.
- [ ] Varsayılanlar: VisionReady, LineValid, CutPermit, ZDownRequest FALSE. Açılışta PLC'ye varsayılan yazma bile yapma. Arm tek başına kesim izni/bıçak talebi üretmesin.
- [ ] X/Y mutlak hedef, opsiyonel Confidence, VisionReady/LineValid/VisionFault/CutPermit/ZDownRequest, Paket Gönder; bağımsız Heartbeat Başlat/Durdur. Bıçak talebi ayrı, açık operatör işlemi; sayfaya girişle oluşmaz.
- [ ] Salt okunur teşhis: state, cycle, actual X/Y, servo/machine/start readiness, sensörler, trajectory valid/fault, heartbeat OK, son sequence/target ve güncellik. Eksik/unmapped değerleri 0/FALSE gibi gösterme.
- [ ] İlk senaryo düz çizgi: Y sabit, ileri X hedefi. Her normal pakette hedefX-actualX>0.001, Y sınırları ve eğim limiti kontrol edilir; canlı değerler gösterilir. Follow sırasında PLC segment Y başlangıcı command setpoint olabilir; actual Y ile doğrulama tam eşdeğer diye sunulmaz. PLC nihai otoritedir.
- [ ] HedefX kesim strokunu belirlemez; X kesim mesafesi lrX_CutEndPos üzerinden gelir. Küçük kamera hedefinin kısa test hareketi anlamına gelmediğini arayüz/rehberde belirt.
- [ ] Önce tek paket modu. Periyodik düz çizgi üretimi ayrı açık başlatma ile; cycle başlangıcından sonra yeni sequence gerekir. ZDownRequest otomatik TRUE olmaz. Eğri/sinüs gibi ek kapsam yok.

## Faz 4 — Yaşam döngüsü ve gerçek kameraya geçiş
- [ ] Sayfadan ayrılma, yetki kaybı, uygulama kapanışı, bağlantı kaybı ve yazma hatasının davranışlarını açıkça tasarla/test et. Gizli arka plan Vision üreticisi bırakma. Aktif cycle içinde normal sayfa kapanışını koordinasyonsuz izin kesme gibi uygulama; kullanıcıya hareket etkisini göster ve planlı kapanış için cycle pasif koşulu koy. Ani kopma/kapanma yine mümkün; watchdog bunu ele alır, güvenli duruş garantisi verme.
- [ ] Planlı bırakma: cycle pasif/eksenler durmuşken, yazıcı sahipliği hâlâ simülatördeyken izin/ready/istek alanlarını kontrollü geri çek; paket/heartbeat görevlerini kapat, kuyruğu iptal et, sıfır yazı durumunu doğrula, sonra REAL moduna devret. Başka yazıcı devraldıktan sonra gecikmiş cleanup yazısı olmasın.
- [ ] Bağlantı kaybında temizleme yazıları garanti edilemez; reconnect sonrası otomatik replay/cleanup yok. Kullanıcı tekrar sahiplik ve arm sürecinden geçer.
- [ ] Gerçek kamera devreye alma: orijinal PLC heartbeat kontrolü, simulator feature flag kapalı, aktif timer/kuyruk yok, yeniden başlatmada sıfır Vision yazısı. Opsiyonel modülü kaldırma adımlarını belgele; ana HMI etkilenmesin.

## Faz 5 — İzole testler ve teslim
- [ ] Gerçek endpoint'e bağlanmadan fake worker ile: kapalı/disarmed/REAL/yetkisiz durumda sıfır yazı; yalnız izin listesindeki taglar; tipler; payload önce sequence son; kısmi hata; çift paket; reconnect ve eski kuyruk; UInt32 wrap; start/stop lifecycle; sınır/NaN/inf doğrulaması.
- [ ] Özellik kapalıyken mevcut HMI read, Start/Stop/Reset, jog, settings, alarm ve DemoSimulator regresyon testleri. Testleri gerçek config'e bağımlı yapma.
- [ ] Mevcut pytest çalıştır, UI'yi izole ortamda doğrula; gerçek PLC testini yapılmış sayma. Gerçek PLC'ye kendi kendine veri gönderme.
- [ ] Kullanıcı için kısa adım adım test: önce read-only, sonra cycle pasif sahiplik/heartbeat, sonra geçerli tek paket ve PLC hesaplarının doğrulanması; hareketli tam çevrim ayrı kullanıcı kontrollü aşama.
- [ ] Değişen dosyalar, test sonucu, kaldırma/devre dışı bırakma talimatı, kalan PLC kararları teslim et. .ai hafızası/RULES güncelle; .ai/Codex_Codesys.md sonuna HMI -> PLC yanıtı ekle.

## Bitiş ölçütü
İzole geçici ekran çalışır; normal HMI davranışı korunur; iç PLC durumlarına yazılmaz; paket sırası testlidir; feature kapalı veya REAL modunda sıfır simulator yazısı kanıtlanır. Harici gerçek kamera ile çakışmama koşulları ve mevcut teknik sınırlar açıkça belgelenir. PLC/gerçek makine testleri kullanıcı tarafından ayrıca doğrulanır.
