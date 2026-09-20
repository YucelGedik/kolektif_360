# PLC-HMI-20260917-03 — Tam otomatik masa testi için kamera emülatörü

Bu, kullanıcının yeni açık talebidir ve önceki görevdeki manuel paket / manuel ZDownRequest kısıtını yalnız bu açıkça etkinleştirilen test modu için günceller. Kullanıcı motorların mekanikten tamamen ayrıldığını, sensörlerin masasında olduğunu ve bunları mıknatısla tetiklediğini bildirdi. Amaç gerçek kamerayı beklemeden PLC otomatik çevrimini uçtan uca denemek. Mevcut manuel paket modu korunabilir; asıl teslim aşağıdaki otomatik kamera modudur. Ana HMI ve PLC mimarisi değişmez.

## Kullanıcı deneyimi / teslim
Kullanıcı bir kez ARM ve “Otomatik Kamera / Düz Çizgi Testini Başlat” seçer. Sonra normal HMI'dan Start verir ve sırayla clamp/blade sensörlerini fiziksel olarak tetikler/bırakır. Her adımda tekrar Paket Gönder, CutPermit veya ZDownRequest işaretlemez. Simülatör gerçek PLC durumunu okuyarak Vision girdilerini üretir; PLC state/sensör/valf/motion/readiness/trajectory sonuçlarına yazmaz. Start/Stop/Reset ve manuel/auto seçimini simülatör üretmez. Yeni çevrim için Start yine kullanıcıdan gelir.

## Faz A — Önce gerçek yazma hatasını düzelt
Ekranda “Yazma başarısız: vision_sequence”; hedefler ulaşmış, sequence/Heartbeat 0. plc/opcua_client.py::_write_checked çıplak node.write_value(value) kullanıyor. Heartbeat ve udiVisionSequence PLC'de UDINT -> açık OPC UA UInt32; LREAL -> Double; BOOL -> Boolean. Gerçek hata kodunu/tagı koruyarak UI/loga taşı (BadTypeMismatch olasılığı, henüz kesin hata kodu bilinmiyor). Mevcut HMI yazmalarını bozma. Bu çözülmeden otomatik paket üretimi çalışmış sayılmaz.

## Faz B — Otomatik kamera üreticisi
- Son export C:/Users/agedik/Documents/ChatGPT/Bufera Tekstil PLC/BUFERA_TEKSTIL_MASTER_CONTEXT_PACK_2026-09-16/plc_export/Bufera_Perde_Kesme_20260917_1635.export.
- 1635'te heartbeat orijinal hesaba GERİ DÖNDÜ; sabit TRUE yok. HMI'nin eski bypass açık notunu güncelle.
- Düz çizgi ilk senaryo: TargetY_mm = güncel tanımlı Y merkezi (lrY_CenterPosition). Geometri, güncel başlangıç/merkez/sınır değerleriyle önizlenir. İlk paket eğimi ve Y sınırları kontrol edilir; kullanıcı ayarlarını sırf geçsin diye değiştirme.
- Hedef X, güncel actual X + pozitif ileri bakış mesafesi. Mesafe, gerçek kesim hızı ve paket periyoduyla uyumlu pay içermeli; iletim gecikmesiyle hedef geride kalmamalı. TargetX PLC trajectory referansıdır, X motion hedefi değildir. Kesim motion hedefi lrX_CutEndPos'tur. Hedefi kesim sonunda min(CutEndX, actualX+lead) yapıp deltaX'i sıfıra düşürme. Düz çizgi sanal ileri hedefinin CutEndX'i aşması X hareket hedefini değiştirmez; bunu açıkla. Sonlu/geçerli aralıkları koru.
- Otomatik heartbeat bağımsız periyodik üretim; gerçek tVisionHeartbeatTimeout'tan güvenli payla kısa. Timeout birimi config/parametre katmanında doğrulanmalı. Herhangi bir timeout için kör max(200,timeout/3) kullanıp periyodu timeout üstüne çıkarma.
- Otomatik paket üretimi örneğin 100 ms başlangıç periyoduyla yapılandırılabilir, tek in-flight ve birikmeyen kuyruk. PLC 2 ms taskına HMI paket hızını eşitleme. Her pakette payload önce, sequence son; UDINT taşması tanımlı. Yalnız yeni yayınlanan pakette sequence artar.
- Başlangıç sayaçları PLC'nin güncel okumasından alınır. Stale/disconnected veriden hedef üretme. Hata varsa otomatik başarı varsayma, nedeni göster.

## Faz C — PLC state'e göre kamera davranışı
Tüm satırlarda etkin emülasyon oturumu boyunca VisionReady TRUE, VisionFault FALSE ve heartbeat canlı kalır. Bağlantı/üretici hatası ayrı işlenir. VisionFault hata enjeksiyonu bu ilk happy-path tesliminin kapsamında değil.

| PLC state | Kamera davranışı |
|---|---|
| INIT / WAIT_FOR_MATERIAL | VisionReady ve heartbeat üret; ZDownRequest FALSE, CutPermit FALSE. StartPermitted PLC'nin hesabıdır. Yeni çevrimi kendin başlatma. |
| CLAMP_DOWN | Heartbeat sürer; ZDownRequest FALSE. Kullanıcı clamp sensörünü gösterecek. |
| WAIT_VISION | Geçerli düz çizgi hedefi, LineValid TRUE ve CutPermit TRUE üret; bu çevrim Start'ından SONRA yeni sequence mutlaka gönder. ZDownRequest FALSE. |
| ALIGN_Y | Geçerli paketler/heartbeat ve CutPermit sürer; ZDownRequest FALSE. Y motion Done'u PLC üretir. |
| WAIT_BLADE_REQUEST | Paket üretimi sürer. PLC xTrajectoryValid TRUE ve xTrajectoryFault FALSE, doğru/güncel Vision alanları gözlenince ZDownRequest TRUE gönder. Valid'i kendin yazma. |
| BLADE_DOWN | ZDownRequest, LineValid, CutPermit ve heartbeat tutulur. Kullanıcı blade sensörünü gösterecek. |
| CUTTING | Actual X'e göre hedefleri sürekli yenile; LineValid/CutPermit/ZDownRequest TRUE kalır. Follow açıldığında PLC eğimi sıfırlayabildiği için kesim boyunca paket üretimi sürer. |
| BLADE_UP / RETURN_AXES / CLAMP_UP / CYCLE_COMPLETE | ZDownRequest ve CutPermit FALSE; yeni kesim talebi yok. Heartbeat/VisionReady sürer. İleri hedef paketlerini kesim dışı dönüş için gereksiz üretme; yeni WAIT_VISION'da taze paket oluştur. Kullanıcı blade sensörünü, sonra clamp sensörünü bırakır. |
| STOPPING / FAULT / RECOVERY | ZDownRequest/CutPermit FALSE; Start/Reset verme, state zorlaması yapma. Yeni kesim paketleri durur; etkin ve bağlı kamera oturumu heartbeat/ready üretmeye devam edebilir. Normal PLC recovery akışını kullanıcı yönetir. |
| MANUAL | ZDownRequest/CutPermit FALSE; otomatik kesim paketi yok. Kullanıcı mode değiştirir. |

Geçiş yarışlarını ele al: BLADE_DOWN'da aktif talebi kısa aralıklarla yanlışlıkla FALSE yapma; CUTTING'de permit/line gereksiz pulse üretme. Tek arbiter otomatik ve manuel kontrollerin aynı taglara zıt yazmasını önlesin. Otomatik mod etkinse manuel packet/izin kontrolleri pasif veya açık devir işlemiyle ayrılmış olsun. PLC state'e geçişi kontrol etmeye çalışma; yalnız kamera tarafı sözleşmesini üret.

## Faz D — Yaşam döngüsü ve görünür teşhis
- Varsayılan kapalı, yeniden açılış/reconnect DISARMED. Gerçek kamera ile tek yazıcı ön koşulu korunur; gerçek kamera modunda sıfır simulator yazısı.
- Ekranda Kamera otomatik aktif, yayın periyodu, son başarılı paket/sequence, heartbeat readback, actual X / ileri hedef / hedef Y, PLC valid/fault, state ve “şimdi kullanıcıdan beklenen sensör” göster.
- Yazma başarı ve gerçek readback ayrı; checkbox seçili olması yazma başarısı kanıtı değil.
- Aktif çevrim sırasında popup kapatılması/disarm heartbeat'i keserek STOPPING ve dönüş hareketine yol açabilir. Sadece bool cleanup atlamayı güvenli kapanış gibi anlatma. Planlı kapanışı cycle pasif koşuluna bağla; bağlantı kaybında üretimi durdur ve otomatik replay yapma.
- Generation yalnız eski sonucu yok saymak değil, worker'daki eski yazıları gerçekten iptal/engellemek için kullanılmalı. Gerçek kameraya devirden sonra eski paket/cleanup yazısı kalmasın.
- Eski nottaki “PLC'de Y actual velocity yok” ifadesi yanlış: GVL.lrY_ActualVelocity mevcut. OPC yayın erişimini kontrol et; lrY_SetVelocity actual değildir. Kaynak devrinde her iki eksen duruşunu doğrula.

## Faz E — Test ve kullanım rehberi
Gerçek PLC'ye kendi kendine bağlanıp hareket başlatma; izole fake worker ve state snapshotlarıyla test et:
1. Varsayılan/REAL/disarmed sıfır Vision yazısı; type mapping UInt32/Double/Boolean.
2. Tam state dizisinde heartbeat/paket ve izinlerin doğru üretimi; Start/Reset/internal komut yazısı sıfır.
3. WAIT_VISION'da Start sonrası taze sequence; valid yokken otomatik blade talebi yok.
4. CUTTING'de ilerleyen actual X'e göre ileri hedef; son noktada deltaX sıfır değil.
5. Stop/fault/recovery sırasında yeni kesim talebi yok; eski kuyruk reconnect/devirde çalışmıyor.
6. UI kapatma / aktif cycle ve arka planda etkin oturum davranışı; mevcut HMI regresyonları.

Kullanıcıya tek sayfalık rehber ver: ARM -> otomatik kamera başlat -> heartbeat/ready kontrol -> ana HMI Start -> clamp sensörü göster -> blade talebi ve çıkışı görünce blade sensörü göster -> BLADE_UP'ta blade sensörü bırak -> eksenler dönünce CLAMP_UP'ta clamp sensörü bırak -> WAIT_FOR_MATERIAL. Sensörleri state'ten önce sürekli TRUE bırakmamasını belirt. Bu masa testi, mekanik kesim/safety veya gerçek görüntü algoritmasının doğrulaması değildir.

Yalnız rapor üretmekle kalma; bu dar kapsamı uygula/test et, .ai hafızasını ve Codex_Codesys.md yanıtını güncelle. PLC programını veya tag sözleşmesini değiştirme.
