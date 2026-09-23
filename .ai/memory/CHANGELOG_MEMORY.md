# Bufera Makine Ekranı - Degisiklik Hafizasi

Yeni girisleri en uste ekle. Eski ve uzun detaylari `CHANGELOG_ARCHIVE.md`
dosyasina tasi.

## 2026-09-23 - C8: gerçek PLC'ye salt-okunur browse ile doğrulama, "PLC henüz doğrulamadı" iddiam düzeltildi

Kullanıcı: "sana diğer ajan 23 nolu uyarı iletti önce ona bak. sıfırlama
ile ilgili." PLC tarafı (`.ai/HMI_C8_CONFIG_HANDOFF_20260923.md`,
PLC-HMI-20260923-23) haklı bir düzeltme yaptı: bir önceki turda yazdığım
"PLC tarafı tamamlanmadı" ifadem **kanıtsız bir çıkarımdı** - mesaj 21'deki
"kullanıcı henüz uygulamadı" notu C8E (ayrı bir EMG düzeltmesi) içindi, C8
sıfırlamayla ilgisi yoktu. Kullanıcı C8 kodunu ve Symbol Configuration'ı
gerçek PLC'ye zaten indirmişti.

**Yapılan doğrulama (gerçek `opc.tcp://192.168.0.2:4840`, `asyncua.
Client`, YALNIZ okuma - hiçbir yazma yapılmadı):**
- Bağlantı başarılı, `MachineReady` okundu (bilinen çalışan bir tag ile
  sağlık kontrolü).
- `Application` düğümünün çocukları browse edildi: standart cihaz bilgisi
  alanları + `Programs` (0 çocuk!) + `Tasks` + `GlobalVars` (1 çocuk:
  `GVL`).
- `GVL`'nin TÜM çocukları listelendi (155 değişken) - `xSetZeroRequest`
  ORADA, `read_data_type_as_variant_type()` → Boolean, `read_value()` →
  `False`. **Canlı ve doğru.**
- 10 aday RO NodeId'nin (`...Motion_Control.MC_Home_X/Y.Done/Busy/Error/
  ErrorID/CommandAborted`) hepsi doğrudan okundu - hepsi `ua.
  UaStatusCodeError`, kod `0x80340000` = **BadNodeIdUnknown**. `Programs`
  klasörünün 0 çocuklu olması bunu zaten destekliyordu - hiçbir POU/FB
  instance'ı şu an online sembol ağacında browse edilebilir değil.

**Yapılan değişiklik:**
- `config/opcua.json` yedeklendi (`config/opcua.json.bak_20260923_pre_c8`,
  `.gitignore`'a `config/opcua.json.bak*` eklendi).
- Yalnız doğrulanan `cmd_set_zero_request` → `xSetZeroRequest` gerçek
  config'e eklendi (85 mevcut eşleme dokunulmadan korundu).
- `services/machine_service.py`: `SET_ZERO_REQUIRED_TAGS` sınıf sabiti
  (tekrarı önlemek için `set_zero_tags_configured`/yeni `set_zero_missing_
  tags()` aynı kaynaktan besleniyor). `set_zero_missing_tags()` artık
  gerçekten eksik olan 10 alanı döndürüyor (`cmd_set_zero_request` listede
  değil).
- `ui/machine/set_zero_dialog.py` + `settings_page.py`: "TAG EKSİK - ...
  PLC ... henüz online doğrulamadı" metni, PLC'nin önerdiği nötr metinle
  değiştirildi: "HMI bağlantı ayarında sıfırlama alanları eksik. PLC
  sembollerinin erişimi kontrol edilip HMI eşlemesi tamamlanmalı." + eksik
  anahtar listesi (dinamik, `set_zero_missing_tags()`'ten). "PLC kodu
  yüklenmedi" gibi bir iddia artık YOK.

**Ders (kendi hatamdan):** "Online doğrulanmadı" gibi bir NEDEN iddia
etmeden önce ya salt-okunur browse ile kanıtla ya da PLC'ye sor - "tag
config'te yok" ile "PLC bunu yapmadı" FARKLI şeyler, ikincisini kanıtsız
söylemek yanlış bilgi yaymak oluyor (ve tam olarak böyle oldu).

Test: `test_set_zero_reference.py` (+3 - `set_zero_missing_tags`),
`test_set_zero_dialog.py` (1 test güncellendi - yeni metin). Tam suite
350/350. `.ai/Codex_Codesys.md`'ye ayrıntılı yanıt yazıldı - PLC'den
10 RO alanın gerçek sembol yolu/yayın durumu teyidi istendi.

## 2026-09-23 - C8 diyalogu yanlış "koşullar sağlanmıyor" mesajı gösteriyordu (kullanıcı sahada buldu)

Kullanıcı gerçek PLC'de C8'i test etti: "şartları sağladım ama buton aktif
olmuyor" - ekran görüntüleri Manuel mod açık, X/Y servo READY, bıçak/baskı
sensörü YUKARI gösteriyordu.

**Kök neden (beklenen, doğru davranış):** gerçek `config/opcua.json`'da
C8'in 11 aday tag'i hâlâ yok - PLC'nin `C08_2` kodu henüz gerçek cihaza
uygulanmadı (mesaj 21: "kullanıcı henüz uygulamadı"). `set_zero_tags_
configured()` bu yüzden hep False, buton doğru şekilde pasif.

**Gerçek HMI hatası:** `SetZeroReferenceDialog._on_snapshot`, tag'ler
eksikken de genel `_CONDITIONS_NOT_MET_TEXT` ("Manuel mod, servo hazır ve
mekanizmaların yukarıda olduğunu kontrol edin") gösteriyordu - operatörü
kendi kurulumunu sorgulamaya yönlendirip gerçek sebebi (PLC tarafı eksik)
hiç söylemiyordu. `set_zero_tags_configured()` artık `_on_snapshot`'ta
EN ÖNCE kontrol ediliyor; eksikse kırmızı "TAG EKSİK" metni (ManualPage'
deki C5/move-to-start "TAG EKSİK" deseniyle aynı disiplin) gösteriliyor.

Test: `test_set_zero_dialog.py::test_missing_tags_shows_honest_reason_
not_generic_conditions_text` (yeni). Gerçek render edilmiş ekran
görüntüsüyle doğrulandı. Tam suite 347/347. `.ai/Codex_Codesys.md`'ye
not düşüldü (PLC'yi ilgilendirmiyor, yalnız kayıt bütünlüğü için).

## 2026-09-23 - PLC-HMI-20260923-20: C8 "Sıfır Referansı Belirle" (sade sürüm) uygulandı

Kullanıcı: "C8 e geçelim o istekleri tamamlayalım." Kaynak: `.ai/HMI_C8_
SADE_SURUM_20260923.md` (19 numaralı, 10-tag/EMG-geçmişi/sonuç-sequence
paketi İPTAL edilmişti, bu sade sürüm yetkili sözleşme).

**Ne inşa edildi - mevcut fiziksel X/Y konumunu 0 yapan, şifreli, modal
bir servis penceresi:**
- `core/models.py`: 10 yeni RO alan (`x_home_done/busy/error/error_id/
  aborted`, `y_home_*`) - mevcut `Motion_Control.MC_Home_X/MC_Home_Y`
  FB'lerinin üyeleri, yeni GVL bool'ları DEĞİL. Config'te eşleme yok, hep
  False/0 (C0.4/C5 disiplini).
- `services/machine_service.py`: `_set_zero_common_allowed()` (erken izin
  kapısı - `_pneumatic_common_allowed` ile aynı disiplin, artı bıçak/baskı
  yukarıda olma şartı), `request_set_zero()` (LEVEL yazma - pulse değil,
  sonuç alınana kadar TRUE), `_update_set_zero_status()` (C5'teki
  "cleared" edge-detection deseni + iki YENİ kural: bağlantı kaybında
  durum donuyor/reconnect'te TRUE tekrar gönderilmiyor, 15sn sonuç
  bekleme zaman aşımı → HATA). `_manual_allowed()`'a jog kilidi eklendi
  (Request/Busy sürerken).
- `services/demo_simulator.py`: `_apply_set_zero()` - demo modda kısa bir
  Busy penceresinden sonra X/Y'yi gerçekten 0'a çeker.
- `ui/machine/set_zero_dialog.py` (yeni) - `SetZeroReferenceDialog`:
  talimat metni, canlı koşul durumu, 3sn `HoldButton`, sonuç etiketi
  (Mesaj/Uyarı/Hata metinleri görev dosyasından birebir). Uygulama-
  genelinde MODAL (`setModal(True)`) - işlem sürerken (`sent`/`busy`)
  `reject()`/`closeEvent()` override'ıyla normal yollarla kapatılamaz.
- `ui/machine/settings_page.py`: "SIFIR REFERANSI BELİRLE ⚙" düğmesi -
  Vision Simülatörle AYNI mühendislik şifresi (`VISION_SIM_PASSWORD`),
  her açılışta yeniden sorulur.
- `config/opcua.example.json`: 11 aday tag (`cmd_set_zero_request` +
  10 RO). NodeId yolu (`...Motion_Control.MC_Home_X.Done` vb.) TAHMİN -
  PLC'nin kendi notu: iç FB üyelerinin sembol yayını teyitli değil, PLC
  online doğrulayınca gerçek yol/config gelecek.

**Bilinçli kapsam kararları:**
- "Alarm Listesi" referans sekmesine bu 3 mesaj EKLENMEDİ (H-kodu her
  zaman kalıcı `ALARM_CATALOG` girişine karşılık gelir örtük kuralını
  bozmamak için) - PLC'ye bildirildi, istenirse eklenir.
- Pnömatik butonlar (bıçak/baskı) set-zero sürerken KİLİTLENMEDİ - görev
  dosyası yalnız `xManualJogAllowed`/`FeedManualAllowed`'a iki yeni AND
  koşulu ekliyor, pnömatik formülüne dokunmuyor; aynı ayrımı HMI'da da
  korunduk.
- Besleme (feed) butonu HMI'da yok (yalnız diagnostic gösterge) - PLC'nin
  kendi `FeedManualAllowed`'ı fiziksel pushbutton'ları zaten gatiliyor,
  HMI tarafında ek kod gerekmedi.

Test: `test_set_zero_reference.py` (26, yeni), `test_set_zero_dialog.py`
(14, yeni). Tam suite 346/346. Gerçek render edilmiş ekran görüntüsü +
demo modda gerçek 50ms tick döngüsüyle (hazır→basılı tutma→işlem
sürüyor→X/Y=0/başarı) uçtan uca doğrulandı - X/Y gerçekten 0'a döndü,
sonuç etiketi/renk/Kapat butonu durumu doğru. Gerçek PLC'ye kendi kendine
yazılmadı. `.ai/Codex_Codesys.md`'ye ayrıntılı yanıt yazıldı, PLC'den
NodeId yolu teyidi istendi.

**Yan not:** Aynı sırada PLC'den 21 numaralı YENİ bir mesaj daha düştü
(EMG basılınca bıçak/baskı otomatik geri çekilsin + H16 metin güncellemesi)
- bu oturumda dokunulmadı, alındı bildirimi yazıldı, ayrı ele alınacak.

## 2026-09-23 - VisionCut mimari kararı: ayrı süreç KABUL EDİLDİ + gerçek mesaj kanalı keşfi

Kullanıcı: "mesajın VisionCut'a gerçekten ulaşması için ne yapmamız gerek."
Bu soruyu araştırırken kritik bir bulgu çıktı: `gh` hesabımız
(`YucelGedik`) gerçek paylaşılan depoya (`muratturan19/Brode_Vision_PLC`)
**push yetkisiyle** collaborator - ve dün yazdığımız `06` mesajı (endpoint/
node haritası) o depoya HİÇ ulaşmamış, yalnız bizim yerel `visioncut_
message/` aynamızda kalmış. VisionCut bunu kendi `09` mesajında zaten
fark etmiş ("06'yı yalnızca kendi deponuza yazmıştınız, biz orayı
okumuyorduk"). Gerçek depoda ayrıca bizim hiç görmediğimiz 3 mesaj vardı:
`07`/`08`/`09` (VisionCut'tan, 20-21 Eylül) - **VisionCut zaten sahaya
gitmiş, programımızı kendisi PyInstaller ile paketleyip 4 gerçek hata
bulup yamalamış**, ve üç insan-kararı gerektiren açık soru bırakmış.

Kullanıcıyla birlikte 07-09'u değerlendirdik, kararlar:
- **07.1 KABUL:** İki program ayrı süreç/ayrı pencere olacak (VisionCut'ın
  ölçümle desteklenen önerisi - kare hızı, GIL paylaşımı, arıza izolasyonu).
  PLC tag'i gerekmiyor, karşılıklı öne getirme/küçültme ile geçiş.
  `visioncut_message/KARARLAR.md`'ye yazıldı (karar #1).
- **07.2:** Yer tutucu ilk kamera sayfası kaldırılabilir - onaylandı.
- **08.1:** 4 hatanın (a/b: config yoksa çökme + paketlenince yazılamayan
  yollar - mimariden bağımsız gerçek hatalar; c/d: yer tutucu sayfa/kamera
  butonu - 07.1'in sonucu) kodu henüz YAZILMADI - kullanıcı önce gerçek
  yama dosyasını istiyor, VisionCut'tan rica edildi. Kör kopyalamak yerine
  kendi testlerimizle doğrulamak istiyoruz.
- **08.2:** Pencere başlığı düzeltildi (`app/main.py`) - "Makine Ekran"
  korunur, "(dev shell)" kaldırıldı.
- **08.3 KABUL:** Bundan sonra ajanlar arası TEK kanal gerçek paylaşılan
  depo (`Brode_Vision_PLC`) - kendi `visioncut_message/` klasörümüz artık
  yalnız pasif yerel referans.
- **09.1:** VisionCut build'e devam ediyor (şimdilik) - onaylandı.

`INTEGRATION.md` yeni mimariyi yansıtacak şekilde güncellendi (eski
"tek süreç gömme" planı artık geçersiz olarak işaretlendi, kod
uygulaması `08.1`'deki yama dosyasını bekliyor). Yerel `visioncut_message/`
aynası gerçek depodaki `07`/`08`/`09`'u da içerecek şekilde senkronlandı.

Kullanıcı "push et" onayı verdi: mesaj `10` + `KARARLAR.md` karar #1,
gerçek depoya (`muratturan19/Brode_Vision_PLC`, `main` dalı) doğrudan
push edildi (commit `20b2d3f..c90fbba`) - `gh api` ile GitHub'da canlı
olduğu doğrulandı. Bu, "biz oraya doğrudan yazamayız" varsayımının
YANLIŞ olduğunu kanıtlıyor - bundan sonra ajanlar arası mesajlar
doğrudan bu depoya yazılabilir (karar `08.3`).

**Yan bulgu:** Aynı sırada `.ai/Codex_Codesys.md`'ye PLC tarafından iki
yeni mesaj düşmüş (19 - C8 sıfır referansı, sonradan İPTAL; 20 - C8 sade
sürüm, GÜNCEL/yetkili). Yeni bir HMI görevi - bu oturumda dokunulmadı,
ayrı ele alınacak.

Tam suite 306/306 (kod değişikliği yalnız pencere başlığı, davranış
etkilenmedi). `data/bufera.db` pollution temizlendi.

## 2026-09-22 - Gün sonu: master push'landı, VisionCut/PLC tarafına bildirim yazıldı (kullanıcı talebi)

Kullanıcı: "son halini commit push et. visioncut kısmınada mesaj gönder
yeni repoyu çeksin kullansın. plc tarafınada gerekli mesajları at
kendinede kayıtlarını al bugünlük mola."

- `git push origin master` - 15 commit (`d0c8f14..35d7aec`) GitHub'a
  (`kolektif_360`) gönderildi.
- `visioncut_message/mesajlar/2026-09-22_10_bufera.md` (yeni) - VisionCut'a
  repo güncellemesi bildirimi. Numaralandırma: son local mesaj `06`
  (bufera) idi ama VisionCut'ın `07`/`08`/`09` numaralı mesajları henüz bu
  yerel aynaya senkronlanmamış (gerçek kanal `muratturan19/Brode_Vision_
  PLC`, dış repo) - çakışmayı önlemek için yeni mesaj `10` numaralandı.
  İçerik: bugünkü değişikliklerin hiçbirinin OPC UA tag sözleşmesini
  etkilemediği (hepsi HMI-içi), yalnız bilgilendirme amaçlı repo güncelleme
  daveti. Bu dosya yalnız YEREL AYNAYA yazıldı - gerçek dış repoya
  ulaşması için kullanıcının elle senkronlaması gerekiyor (README'nin
  kendi kuralı: "Kaynak depoya yazma bu klasörden yapılmaz").
- `.ai/Codex_Codesys.md`'ye gün sonu özeti eklendi - push bildirimi +
  PLC tarafında açık kalan iki konunun (8 aday tag online testi,
  MANUAL_RETURN_STOP Reset kararı) hatırlatması.
- Hafıza dosyaları (bu dosya + SESSION_BRIEF.md) güncellendi, oturum
  "bugünlük mola" olarak kapatıldı.

## 2026-09-22 - Hız parametre sınırları gerçek mekaniğe göre revize edildi (kullanıcı talebi)

Kullanıcı: "HIZ SINIRLARINI BU ŞEKİLDE REVİZE ET MEKANİĞE BAĞLANDIK VE BU
SINIRLARA KARAR VERDİK." Artık tahmin değil, gerçek mekanik test sonrası
onaylanmış nihai sınırlar. `core/parameters.py`'de 6 hız alanının
`max_value`'su değişti:

- X Kesim Hızı (`lr_x_cut_velocity`): 1-500 -> **1-800**
- X Dönüş Hızı (`lr_x_return_velocity`): 1-800 -> **1-1060**
- Y Pozisyonlama Hızı (`lr_y_move_velocity`): 1-200 -> **1-50**
- Y Follow Maks. Hızı (`lr_y_max_velocity`): 1-200 -> **1-50**
- X Jog Hızı (`lr_x_jog_velocity`): 1-200 -> **1-400**
- Y Jog Hızı (`lr_y_jog_velocity`): 1-100 -> **1-50**

Tüm mevcut `default` değerleri (REAL_PLC_DEFAULTS) yeni aralıkların içinde
kalıyor, değiştirilmedi. Diğer parametreler (Acc/Dec, konum, timeout) bu
revizyonun kapsamı dışında. Testler: `test_parameters.py`'ye `test_
velocity_ranges_match_confirmed_mechanical_limits` eklendi (regresyonu
kilitler). Demo modda uç değerler (800/1060/50/50/400/50) elle doğrulandı,
bir üstü (801) doğru şekilde reddedildi. Tam suite 306/306.

## 2026-09-22 - PLC-HMI-20260922-18: C06_1 HMI kaynak denetimi (A01-A06), 6 gerçek bulgu düzeltildi

Kaynak: `.ai/HMI_C061_AUDIT_TASK_20260922.md` - başka bir ajanın HMI kod
tabanını PLC C06_1 export'uyla karşılaştıran bağımsız denetimi. Her madde
kodda DOĞRULANDI önce (hiçbiri uydurma değildi); ikisi (A06'daki state
140/510 etiketleri) benim ÖNCEKİ oturumlarda attığım gerçek hatalardı -
PLC'nin kendi 2026-09-18/09-21 talimatlarına aykırı yazılmışlardı.

**A01 (P1) - `set_parameter` ayar yazma izni eksikti:** yalnız `move_to_
start_busy` kontrol ediliyordu; `cycle_active`/stale/bağlantı/jog/eksen
hareketi HİÇ kontrol edilmiyordu (repro: cycle_active=True+stale=True+
DISCONNECTED iken yazma worker'a ulaşıyordu). Yeni `_settings_write_
allowed()` - `_pneumatic_common_allowed`'la aynı disiplin, ama stale/
bağlantı kontrolü yalnız GERÇEK modda (demo'da `.start()` çağrılmadığı
sürece `stale` varsayılanı hep True kalır - bu ayrım olmadan tüm demo-mod
testleri kırılıyordu, empirik olarak bulundu). UI zaten `ValueError`'ı
yakalayıp gösteriyor, yeni katman gerekmedi.

**A02 (P1) - Restart sonrası alarm uzlaştırması yoktu:** `_active_alarm_
events` RAM'de başlar, SQLite kalıcıdır - restart sonrası PLC FALSE okunan
eski bir aktif kayıt hiç kapanmıyordu (servis onun varlığından habersiz);
TRUE kalan bir koşul ikinci bir kopya kayıt açıyordu. `AlarmEvent`'e yeni
`catalog_id` sütunu (nullable ADD COLUMN migration, tablo yeniden kurmaya
gerek yok), `_reconcile_alarm_state_with_persisted_events()` ilk gerçek
okumada DB'deki açık kayıtları belleğe geri yüklüyor (eski kopyalar varsa
en yenisi tutulur, gerisi `clear_event` ile kapatılır - silinmez). Ayrı
bulgu: `active_alarm_count()`/"Güncel Alarmlar" `recent(limit=100)`
kullanıyordu - 100+ geçmiş kayıt birikince eski bir aktif HATA gizlenebi-
liyordu. Yeni sınırsız `AlarmRepository.active_events()`/`MachineService.
active_alarms()`.

**A03 (P2) - U10 sıralaması ters:** `compute_start_inhibit_reasons` `snap.
start_permitted`'i stale'DEN ÖNCE kontrol ediyordu - bağlantı koptuğunda
`start_permitted` PLC'den gelen SON (artık bayat) TRUE değerini taşımaya
devam ettiği için fonksiyon erken `[]` dönüyor, U10 hiç görünmüyordu.
Sıra değiştirildi (stale önce).

**A04 (P1 entegrasyon kapısı) - eksik tag'ler görünmüyordu:** 8 aday alan
(H12-H15/H20-H22/U06) config'te yoksa sessizce hep False kalıyordu - "sağ-
lıklı okuma" ile "hiç tetiklenemez" ayrımı operatöre hiç gösterilmiyordu.
Yeni `MachineService.pending_candidate_catalog_ids()` - config'ten CANLI
okur (statik metne bağlı değil), Alarmlar sayfasında dinamik bir banner
gösterir. İnce nokta: H06/H07'nin snapshot alanı (`x_fault`/`y_fault`)
config anahtarından (`x_power_error`/`y_power_error`) farklı isimlendiril-
miş - `_CATALOG_ATTR_TO_CONFIG_KEY` ile çözüldü (ilk taslak H06/H07'yi
YANLIŞLIKLA "eksik" listeliyordu, gerçek config'te render ederek yakalandı).

**A05 (P2) - MESAJ sınıfı hiç canlı değildi:** `core/notification_catalog.
py`deki M01-M09 yalnız statik referanstı, ana ekran tablosuna hiç yansımı-
yordu. Yeni `compute_active_state_message()` - `cycle_state`'e göre M01-
M07/M09'u (görev notundaki eşleme: 40/60/30-70/90-110/130/140/510/500)
cycle_state süresince gösterir; M08 ayrı - "yalnız yeni sonuç" (görev notu)
olduğu için `move_to_start_status()` İLK KEZ "done" olduğu tick'te bir kez
(edge-tracking), durum "done" kalsa bile tekrarlanmaz. Hepsi U-serisiyle
aynı desen: `AlarmRepository`'ye YAZILMAZ, canlı görünüp kaybolur.

**A06 - dört küçük düzeltme:** (1) `CycleState.MANUAL_RETURN_STOP` (140)
etiketi "Durduruldu" (tamamlanmış, YANLIŞ) yerine "Durduruluyor" - PLC'nin
kendi 13 numaralı bulgusu zaten "durduruluyor" diyordu, ben yanlış yazmı-
şım. `RECOVERY` (510) "Recovery" yerine "Manuel Hazırlık Bekleniyor" - PLC
2026-09-18'de açıkça "eski recovery ifadesi kullanılmamalı" demişti, yine
benim hatam. (2) `_pneumatic_common_allowed`'a `operator_stop_active`
kontrolü eklendi (aday tag, şimdilik inert). (3) U05'in bilinen sınırlaması
(`xBladeValveCmd` hiç yayınlanmamış bir tag - HMI yalnız `BladeZDown`
görüyor) yorumla netleştirildi, U11 genel yedeğin bu boşluğu zaten kapat-
tığı belirtildi. (4) "henüz build/export edilmedi" yorumları "export'ta
var, online node/erişim testi bekliyor" olarak düzeltildi (8 alanın da
export'ta VAR olduğu bu denetimle doğrulandı).

**Yan bulgu (test altyapısı):** `data/bufera.db`'deki eski numaralı-kod
alarmları (örn. 1201 "Vision Heartbeat Kayboldu") GERÇEK PLC verisi değil,
`DemoSimulator`'ın kendi `raise_alarm(1201, ...)` çağrısından - paylaşımlı
DB + izole olmayan demo-mod testleri yüzünden. Önceki oturumlarda "gerçek
geçmiş" sanılıp KORUNMUŞTU - yanlış varsayımdı, düzeltildi (bkz. SESSION_
BRIEF Kısa Notlar).

Test: `test_settings_write_permission.py` (8, yeni), `test_alarm_restart_
reconciliation.py` (6, yeni), `test_active_state_message.py` (10, yeni),
`test_machine_page_message_table.py` (5, yeni), `test_alarm_catalog.py`
(+4), `test_cycle_state.py` (+2), `test_manual_down_requests.py` (+1),
`test_start_inhibit_reasons.py` (+1, yorumlar güncellendi), `test_
parameter_write_confirmation.py`/`test_parameter_cross_validation.py`
(fixture'lara connection_state=CONNECTED/stale=False eklendi - A01'in
gerçek-mod gereksinimiyle tutarlı olmaları için). Tam suite 305/305.
`.ai/Codex_Codesys.md`'ye yanıt yazıldı.

## 2026-09-22 - Manuel sayfa: "Başlangıç Konumuna Dön" satırı X/Y kartları arasında yamuktu (kullanıcı ekran görüntüsü)

Kullanıcı: "sıfıra gönder butonu ile başlangıç konumu yanyana ama aynı
yükseklikte değil... genişliği farklı. Bu da sayfada yamukluk yaratıyor."

**Kök neden:** X kartındaki "Başlangıç Konumuna Dön" (`HoldButton`, sabit
`PRIMARY_ACTION_HEIGHT=64`) ile Y kartındaki karşılığı "BAŞLANGIÇ KONUMU"
(`ProcessStatusCard`, kendi içeriğine göre doğal yükseklik = 72px) 8px
farklıydı (geometri ölçümüyle doğrulandı: 64 vs 72). Kartların GENİŞLİĞİ
zaten birebir eşitti (656px, kullanıcının "genişlik" algısı aslında bu
8px'lik yükseklik farkının yarattığı görsel kaymaydı) - ama bu satırdan
SONRAKİ her şey (Actual Position, Servo) X/Y arasında 8px kaymış, sayfa
"yamuk" görünüyordu.

**Düzeltme** (`ui/machine/manual_page.py::_build_ui`): her iki axis kartı
kurulduktan hemen sonra, `_move_to_start_status.sizeHint().height()`
okunup hem butona hem duruma `setFixedHeight` ile uygulanıyor - artık
ikisi de garantili aynı (72px), aşağıdaki tüm satırlar piksel piksel hizalı.

Doğrulama: gerçek render edilmiş ekran görüntüsü + widget geometrisi
(`.geometry()`) karşılaştırması - önce (64,72) sonra (72,72), alttaki
Actual Position/Servo satırları da X/Y arasında birebir aynı y-koordinatında.
Kod-only fix, yeni test gerekmedi (saf layout/geometri, davranış değişmedi).
Tam suite 267/267 (değişmedi).

## 2026-09-22 - U01-U11 (Start engelleri) artık ana ekran alarm tablosuna da düşüyor - canlı, kalıcı DEĞİL

Bir önceki [Uxx] kod düzeltmesinden sonra kullanıcıya soruldu: "U-serisi de
tabloya (Uyarı filtresine) girsin mi?" Cevap: "tabloda yazılsın mutlaka ama
banner gibi kalıcı olmasın uyarı sonuçta... resete falan bağlı değil şu an
hangi mantıkla çalışıyorsa tablonun içinde de o mantıkla çalışsın... alarm
yağmuru olmasın hedefimiz aynen devam ediyor."

**Uygulama** (`ui/machine/machine_page.py`):
- `MachinePage.__init__`'e `self._live_warning_messages: list[str] = []`.
- `_on_snapshot` artık `compute_start_inhibit_reasons`'ın sonucunu (zaten
  `[Uxx]` önekli) bu listeye yazıp `_refresh_alarm_table()`'ı her snapshot
  tick'inde çağırıyor - banner ile TAM AYNI anda, aynı veriyle güncelleniyor.
- `_refresh_alarm_table`, "Uyarı" checkbox'ı işaretliyken bu canlı mesajları
  gerçek `AlarmEvent` satırlarıyla BİRLİKTE (aynı tabloda) gösteriyor - Saat
  sütununda "ŞİMDİ" (gerçek bir zaman damgası değil, canlı durum olduğunu
  belirtmek için), Kaynak "PLC". **`AlarmRepository`'ye hiç yazılmıyor** -
  DB'de iz bırakmıyor, Reset'ten etkilenmiyor, koşul kapanınca bir sonraki
  snapshot'ta satır anında kayboluyor (H-serisi gibi rising/falling-edge
  loglama YOK - bilinçli, "alarm yağmuru" hedefiyle tutarlı).

Testler: `tests/test_machine_page_warning_table.py` (5, yeni) - tablo
satırı görünürlüğü, koşul kapanınca geçmişsiz kaybolma, filtre checkbox'ı,
Reset'ten bağımsızlık, gerçek HATA ile aynı tabloda birlikte var olma. Gerçek
render edilmiş ekran görüntüsüyle doğrulandı (ŞİMDİ/Uyarı/PLC/[U10] satırı
doğru göründü). Tam suite 267/267.

## 2026-09-22 - Start engelli banner'ına UYARI kodu ([Uxx]) eklendi (kullanıcı sorusu)

Kullanıcı: "U10 sa bu bir uyarı ? o zaman tabloda olması gerekmezmi ? ek
olarak uyarıda U10 diye de belirtilmemiş operatöre kodu sorsam söyleyemez."

**Doğru gözlem, iki ayrı bulgu:**
1. Ana ekrandaki turuncu "Start engelli: ..." banner'ı hiçbir zaman kodunu
   (U01-U11) göstermiyordu - operatör metni "Alarm Listesi" referans
   sekmesindeki satırla eşleştiremezdi. **Düzeltildi:** `compute_start_
   inhibit_reasons` artık her nedeni `"[U0x] ..."` önekiyle döndürüyor
   (`ui/machine/machine_page.py`). Kod, karşılık gelen `if` bloğunun
   yanındaki mevcut yorumla (`# U01` vb.) aynı yerde, tek elden yazıldı.
2. **Ayrı, daha büyük bir bulgu (henüz karar bekliyor):** U01-U11 hiçbir
   zaman `AlarmRepository`'ye yazılmıyor (yalnız canlı banner) - bu yüzden
   ana ekrandaki "Göster: Hata/Uyarı/Mesaj" filtre tablosundaki "Uyarı"
   kutusu şu an PRATİKTE HİÇBİR ZAMAN dolu satır göstermiyor (kod altyapısı
   var - `SEVERITY_WARNING`, filtre, renk - ama hiçbir yerden gerçekten
   loglanmıyor). Bu, mesaj 15'teki bilinçli "alarm yağmuru olmasın" kararının
   (aktif çevrimde/sürekli değişen U-koşullarını geçmişe yazma) bir sonucu,
   ama tabloda boş bir "Uyarı" filtresi bırakıyor - kullanıcıya karar
   soruldu: U-serisini de (rising-edge ile, H-serisi gibi) geçmişe
   yazalım mı, yoksa canlı-only mi kalsın?

Testler: `test_start_inhibit_reasons.py` güncellendi (tüm literal string
eşleşmeleri `[Uxx]` önekiyle). Tam suite 262/262.

## 2026-09-22 - PLC-HMI-20260922-17: C6 toplu teslim, 3 yeni aday HATA (H20/H21/H22)

Kaynak: `.ai/HMI_C6_FINAL_TASK_20260922.md` (PLC tarafı C6 export'unu
teslim etti, henüz build/online doğrulama yapmadı - kod/test hazır).

Üç yeni latched HATA, H12-H15 ile birebir aynı disiplinle eklendi:
- H20 `xAlarmModeChangedDuringCycle`: "Çalışan çevrimde mod değiştirme
  talebi alındı; makine durduruldu."
- H21 `xAlarmClampLostDuringCycle`: "Çevrim sırasında baskı aşağı sensörü
  kayboldu; makine durduruldu." (mevcut H01 `alarm_clamp_lost_during_cut`
  ile KARIŞTIRILMAMALI - H01 yalnız CUTTING durumunu, H21 baskının aşağı
  tutulması gereken daha geniş bir durum kümesini - WAIT_VISION/ALIGN_Y/
  WAIT_BLADE_REQUEST/BLADE_DOWN/BLADE_UP/RETURN_AXES - kapsıyor, görev
  notundaki C6.2 açıklamasına göre).
- H22 `xAlarmBladeNotClearDuringReturn`: "Eksenler dönerken bıçak açıklığı
  kayboldu; makine durduruldu."

`MachineSnapshot` alanları (`alarm_mode_changed_during_cycle`/`alarm_
clamp_lost_during_cycle`/`alarm_blade_not_clear_during_return`) varsayılan
False; `ALARM_CATALOG`'a H20-H22 eklendi (aynı rising/falling edge
motoru); 3 tag yalnız `config/opcua.example.json`'a (gerçek config'e PLC
online doğrulayana kadar girmiyor, C0.4/C5 disiplini); "Alarm Listesi"
referans sekmesine H20-H22 "henüz build/online doğrulama yapılmadı"
notuyla eklendi.

Testler: `test_alarm_catalog.py` +2 (üç yeni alarm için initial-TRUE/
rising/falling/history + reset-reddi, parametrik), `test_notification_
catalog.py` H01-H22 kapsamına güncellendi. Tam suite 262/262. `.ai/
Codex_Codesys.md`'ye yanıt yazıldı; C6.2'deki PLC-içi Reset/FAULT
yönlendirme kararları HMI kapsamı dışı (yalnız okur).

## 2026-09-22 - Alarmlar sayfasına "Alarm Listesi" referans sekmesi + sekme metni okunmuyordu (kullanıcı ekran görüntüsü)

Kullanıcı: "geçmiş alarmlar ve güncel alarmlar yanına birde alarm liste
ekle. Operatör alarm listesine bakıp alarmların anlamlarını okuyabilsin...
Birde bu sekmelerin yazıları ile arka fon rengi aynı... okunmuyor."

**Sekme metni görünürlük hatası (gerçek bug):** `theme.py`'nin `STYLESHEET`
'inde `QTabWidget`/`QTabBar` için HİÇ kural yoktu - bu yüzden Qt'nin
varsayılan (açık renkli) OS sekme çizimi kullanılıyordu, uygulamanın koyu
temasındaki açık metin rengiyle üst üste binip seçili olmayan sekmelerde
metin okunmuyordu. Artık hem seçili (koyu lacivert zemin, turuncu metin/
kenarlık) hem seçili olmayan (koyu gri zemin, açık gri metin, hover'da
belirginleşir) durumlar için açık kurallar var.

**Yeni "Alarm Listesi" sekmesi:** `core/notification_catalog.py` - CANLI
veri okumayan, statik bir referans sözlüğü. `services/machine_service.py::
ALARM_CATALOG` (H01-H19) ve `ui/machine/machine_page.py::compute_start_
inhibit_reasons` (U01-U11) içinde GERÇEKTEN kullanılan metinlerin birebir
kopyası + M01-M09 (durum mesajları, mevcut `cycle_state_label` etiketleriyle
eşleştirilmiş). Dört sütun: Kod, Tür, Ne Zaman Görünür, Anlamı/Yapılacak.
Operatör bir alarmla karşılaştığında buradan anlamına bakıp geri bildirim
verebilir (kullanıcının asıl amacı). H12-H15/U06 (PLC'nin henüz build/
export etmediği aday tag'ler) satırlarında bunun açıkça belirtildiği bir
not var - "şu an hiç tetiklenmez."

Kod: `ui/machine/theme.py` (QTabWidget/QTabBar stil kuralları),
`core/notification_catalog.py` (yeni), `ui/machine/alarm_page.py` (üçüncü
sekme, `_build_catalog_table`).

Test: `tests/test_notification_catalog.py` (4, yeni - ID benzersizliği,
geçerli severity, boş metin yok, H01-19/U01-11/M01-09'un TAMAMININ mevcut
olduğu). Tam suite 260/260. Gerçek render edilmiş ekran görüntüsüyle
(sekme metni + katalog tablosu) doğrulandı.

## 2026-09-21 - Hata/Uyarı/Mesaj kataloğu, Reset bug fix, çoklu Start engelleri (PLC-HMI-20260921-14/15/16)

Kullanıcı: "Sana yeni görevler iletildi sanırım 11 16 arası kontrol et
bakalım alarmlarla ilgili görevler gönderildi." -> "tamam bunları uygula."
Kaynak: `.ai/Codex_Codesys.md` (mesaj 14/15/16) + `.ai/HMI_C5_ALARM_
MESSAGES_20260921.md` + `.ai/HMI_C6_NOTIFICATION_CLASSES_20260921.md` +
`.ai/C6_ALARM_WARNING_MESSAGE_CATALOG_20260921.md`. Bu oturumun en büyük
tek paketi - üç mesajı birlikte kapsıyor.

**1) Gerçek bug düzeltildi:** `MachineService.request_reset()` gerçek
modda artık `_alarms.clear_active()` çağırmıyor - Reset PLC tarafından
kabul edilmeden aktif HATA ekrandan kaybolmuyor. Temizlik yalnız PLC'nin
kendi okuması (ilgili GVL biti gerçekten FALSE) ile olur.

**2) Yeni HATA edge-detection motoru:** `MachineService._update_alarm_
conditions` - `ALARM_CATALOG` (H01-H18, veri odaklı `_AlarmCondition`
listesi) her `_on_raw_snapshot`/demo tick'te taranır; bir koşul ilk kez
TRUE görüldüğünde (rising edge) `AlarmRepository`'ye BİR KEZ yazılır
(`_active_alarm_events: dict[katalog_id -> event.id]` ile takip edilir),
koşul FALSE'a dönünce (falling edge) yalnız O kayıt (`AlarmRepository.
clear_event`, yeni - `clear_active()`'ın aksine tek kaydı etkiler) kapatılır.
H19 (FAULT + bilinen neden yok) jenerik yedek - bilinen bir HATA zaten
varsa AYRICA sayılmaz. H12-H15 (5 yeni aday tag - `xOperatorStopActive`,
`xX_StopError`, `xY_StopError`, `xX_AxisError`, `xY_AxisError`) kod olarak
hazır ama yalnız `config/opcua.example.json`'da - PLC henüz build/export
etmedi, gerçek config'e eklenmedi (C0.4/C5 disiplini). Diğer 8 tag (4
pnömatik alarm + 4 motion hatası) gerçek PLC export'unda (`Bufera_Perde_
Kesme_20260921_0830_C05`) zaten var olduğu doğrulanarak hem gerçek hem
example config'e eklendi.

**3) Ana ekran ALARM sayacı gerçek hale geldi:** Yeni `MachineService.
active_alarm_count()` - hayali `snap.alarm_count`'a (GVL'de karşılığı yok)
değil, gerçek aktif HATA (severity=ALARM) kayıtlarına dayanıyor; Uyarı/
Mesaj sayılmıyor.

**4) `compute_start_inhibit_reasons` tamamen yeniden yazıldı - artık
İLK engelde return etmiyor:** Eskiden manuel mod/çevrim aktif TEK BİR
nedenle erken dönüyordu (diğer geçerli nedenler gizleniyordu). Şimdi tüm
U01-U09 birlikte listeleniyor (X/Y konum, manuel mod, hazırlık - somut
eksik listesiyle, bıçak aşağı, servo, Vision heartbeat/ready). Stale artık
sessizce boş liste değil, kendi UYARI'sını gösteriyor (U10 - "izin/konum
bilgisi doğrulanamıyor"). Aktif çevrimde hiç UYARI üretilmiyor (görev
notu: normal durum, alarm yağmuru değil). Emniyet ve gerçek servo/motion
arızaları burada TEKRAR gösterilmiyor - zaten HATA panosunda var.

**5) Manuel sayfa - C5 arıza mesajları (mesaj 14):** Genel "HATA - PLC
REDDETTİ" kaldırıldı. Yeni "stopping" durumu (Busy+Aborted birlikte ->
"DÖNÜŞ DURDURULUYOR") salt Busy'den ("HAREKET EDİYOR") ayrıldı - biri
MANUAL_RETURN (130, hedefe hareket), diğeri MANUAL_RETURN_STOP (140,
durduruluyor). Terminal sonuçta Error önceliklidir ("BAŞLANGICA DÖNÜŞ
ARIZASI"); yalnız Aborted -> "TALEP REDDEDİLDİ VEYA DÖNÜŞ İPTAL EDİLDİ"
(kaynakta tek bit, ayrıştırılamıyor - ikisi birlikte söylenir). H05'in
alarm mesajı tam mesaj 14'teki yönlendirme metnini içeriyor (Reset->
Manuel->iki Yukarı->3sDön).

**Yan bulgu, bizim tarafımızda (kaynakta değil):** Alarm kaydını
`code=None` ile yazmaya başlayınca, yerel `data/bufera.db`'nin eski
şemasında `code`'un hâlâ fiziksel olarak NOT NULL olduğu ortaya çıktı
(model her zaman nullable tanımlıydı ama SQLite `ALTER TABLE` ile bunu
gevşetemiyor - `create_all()`'ın da yapamadığı bir sınıf sorun). Yeni
`persistence/db.py::_migrate_alarm_events_code_nullable` tabloyu veri
kaybı olmadan yeniden kuruyor (rename+create+copy+drop), regresyon
testiyle kilitlendi.

Kod: `core/models.py` (13 yeni alan), `config/opcua.json`/`.example.json`
(8 confirmed + 5 aday tag), `services/machine_service.py` (`ALARM_CATALOG`,
`_update_alarm_conditions`, `active_alarm_count`, Reset fix, move-to-start
"stopping"/Error-önceliği), `persistence/alarms.py` (`clear_event`),
`persistence/db.py` (code-nullable migration), `ui/machine/machine_page.py`
(`compute_start_inhibit_reasons` yeniden yazıldı, `_manual_preparation_
reason`, ALARM sayacı), `ui/machine/manual_page.py` (yeni durum metinleri).

Test: `tests/test_alarm_catalog.py` (11, yeni), `tests/test_start_inhibit_
reasons.py` (19, yeniden yazıldı), `tests/test_alarm_severity.py` (+1,
migration), `tests/test_move_to_start.py` (+1, Error önceliği, 1 test
"stopping" için güncellendi). Tam suite 256/256. Gerçek PLC'ye kendi
kendine yazılmadı - kullanıcı sonucu bildirecek.

`.ai/Codex_Codesys.md`'ye HMI -> PLC yanıtı (14/15/16 birleşik) eklendi.

## 2026-09-21 - Gerçek gösterim hatası: Busy sırasında "REDDEDİLDİ" yanlış terminal sonuç gösteriyordu (PLC-HMI-20260921-13)

PLC tarafı, az önceki 140-sıkışma bulgusuna bağımsız incelemeyle yanıt
verdi (`.ai/C5_RESET_140_INVESTIGATION_20260921.md`) ve HMI tarafında
gerçek bir gösterim hatası buldu: `MachineService._update_move_to_start_
status`, Done/Aborted/Error'ı Busy'den ÖNCE kontrol ediyordu. Gerçek PLC'de
`MANUAL_RETURN_STOP`'ta dururken `Busy=TRUE` ile AYNI ANDA `Aborted=TRUE`
de tutulabiliyor (ara/duruş evresi) - bu HMI'da "REDDEDİLDİ" olarak
BİTMİŞ bir sonuç gibi gösteriliyordu, tam kullanıcının yaşadığı ekran
görüntüsündeki durum.

**Düzeltme:** Busy=TRUE olduğu SÜRECE artık Done/Aborted/Error'a hiç
bakılmıyor (isteğin takibi de kapanmıyor, `_move_to_start_sent=True`
kalıyor) - yalnızca Busy FALSE'a düştüğünde bir sonraki Done/Aborted/Error
okuması terminal (kesin) sonuç sayılıyor. Önceki "stale latched Done"
koruması (freshness/"cleared" kontrolü) aynen korundu, yalnızca Busy'nin
önceliği düzeltildi.

Kod: `services/machine_service.py::_update_move_to_start_status`. Test:
yeni `test_busy_takes_priority_over_aborted_not_yet_a_terminal_result`
(tam bu senaryoyu - busy+aborted birlikte, sonra busy düşünce terminal -
doğruluyor); mevcut 24 test değişmeden geçti (yeniden izlendi, hepsi aynı
sonuca varıyor, yalnızca Busy geçişi üzerinden). Widget smoke testiyle de
gerçek senaryo verisiyle doğrulandı: ekran artık "HAREKET EDİYOR"
gösteriyor, Busy düşene kadar "REDDEDİLDİ" görünmüyor. Tam suite 236/236.

Kilitler/state/hareket-gönderme dokunulmadı - yalnızca görüntü mantığı
değişti, PLC tarafının "kilitleri kaldırma, state yazma" talimatına uygun.

`.ai/Codex_Codesys.md`'ye HMI -> PLC yanıtı eklendi. `xStopActive`/Reset'in
140'tan çıkışa etkisi konusundaki asıl bulgu PLC tarafının doğrulamasını
bekliyor - bu ayrı, hâlâ açık.

## 2026-09-21 - Kullanıcı canlı PLC'de MANUAL_RETURN_STOP (140)'ta sıkıştı - kök neden bulundu

Kullanıcı: "Sıfır noktasına gönderirken resete ve stopa bastım bu şekilde
program kaldı. manuel moddan çıkamıyorum tekrar reset atamıyorum..." +
ekran görüntüleri (ana ekranda "Bilinmeyen Durum (140)", Manuel sayfada
"BAŞLANGIÇ KONUMU: REDDEDİLDİ") + gerçek PLC export dosyasının yolu
(`Bufera_Perde_Kesme_20260921_0830_C05.export`, proje dışında,
`C:\Users\agedik\Documents\ChatGPT\Bufera Tekstil PLC\...\plc_export\`).

**HMI tarafı bulgusu (gerçek eksiklik, düzeltildi):** `core/cycle_state.py`
'deki `CycleState` enum'unda `MANUAL_RETURN=130`/`MANUAL_RETURN_STOP=140`
hiç yoktu - C5 export'unda (`E_MachineState`) olduğu doğrulandı ama ilk C5
teslimimizde ekrana hiç eklenmemiş. Bu yüzden "Bilinmeyen Durum (140)"
gösteriliyordu. İkisi de eklendi, Türkçe etiketlerle ("Başlangıca
Dönüyor"/"Başlangıca Dönüş Durduruldu"); `xCycleActive` export'ta FALSE
kaldığı için `AUTO_CYCLE_ACTIVE_STATES`'e eklenmedi (zaten `move_to_start_
busy` ayrı kilitliyor, davranışta değişiklik yok, yalnızca doğru etiket).

**PLC tarafı bulgusu (aday tanı, export incelemesiyle):** `MANUAL_RETURN_
STOP`'un TEK çıkış koşulu (export satır ~149-179) uzun bir AND zinciri;
en olası donma nedeni `xStopActive := GVL.Stop OR xDI_StopPB` - anlık,
latch'siz bir seviye sinyali. Fiziksel panel Stop butonu latch'li
(bas-kilitle/çevir-bırak) tipteyse, operatör bırakana kadar bu asla FALSE
olmaz ve 140'tan çıkış imkansızlaşır. Ayrıca bağımsız doğrulandı: **Reset
bu duruma hiçbir etki yapmıyor** - `xAlarmResetAccepted` yalnızca
`eMachineState=FAULT` iken hesaplanıyor, 140 FAULT olmadığı için Reset
etkisiz kalıyor (kullanıcının "reset atamıyorum" deneyimiyle birebir
örtüşüyor). Bu, PLC tarafına bulgu olarak iletildi - HMI'den düzeltilecek
bir şey değil, PLC state machine'inin kendi tasarım kararı/muhtemel gap'i.

Kod: `core/cycle_state.py` (2 yeni enum değeri + etiket). Test: 235/235
aynen geçti (yeni state'ler mevcut hiçbir kontrolü etkilemiyor - `move_to_
start_busy` zaten ayrı kilitliyordu).

`.ai/Codex_Codesys.md`'ye PLC tarafına yönelik yeni bir bulgu raporu
eklendi (yanıt bekleniyor - bu bir PLC->HMI görev teslimine yanıt değil,
HMI'nin kendi başlattığı bir bug bulgusu).

## 2026-09-21 - C5 gerçek config eksiği tamamlandı (PLC-HMI-20260921-12)

Kullanıcı: "HMI'ya 11 numaralı görevi iletildi kontrol et eksikler yazıyor
oradan tedarik et." Kaynak: `.ai/Codex_Codesys.md` (mesaj 12) + `.ai/HMI_
C5_MAPPING_FIX_20260921.md`. PLC tarafı kod incelemesi yaptı: buton mantığı
zaten doğru (`request_move_to_start()` -> `request_pulse("cmd_move_to_
start")`), eksik olan tek şey önceki turda BİLİNÇLİ olarak eklenmeyen 6
NodeId'nin gerçek `config/opcua.json`'a hâlâ girmemiş olmasıydı - kullanıcı
PLC üzerinden elle `xMoveToStartRequest`i TRUE yazıp iki eksenin hedefe
gittiğini doğruladığı için artık online teyit sağlanmış oldu.

**Config tamamlandı:** `cmd_move_to_start`, `move_to_start_allowed/busy/
done/aborted/error` -> `GVL.xMoveToStartRequest/Allowed/Busy/Done/Aborted/
Error`, `config/opcua.example.json` ile BİREBİR aynı satırlar (namespace/
path tahmin edilmedi - zaten örnekte duran, şimdi kullanıcının kendi PLC
denemesiyle dolaylı doğrulanan yol kullanıldı).

**"Eksik tag varsa kısa açık neden göster; boş tireyle bırakma" (PLC notu):**
`move_to_start_tags_configured()` FALSE olduğunda "Başlangıç Konumu" kartı
artık "—" yerine "TAG EKSİK" (fault) gösteriyor - buton yine devre dışı,
tooltip hangi tag'lerin eksik olduğunu ayrıca söylüyor.

**Basitlik korundu (PLC notu, açıkça istendi):** Yeni katman/ekran/state
eklenmedi - yalnızca 6 config satırı + bir metin dallanması. `move_to_
start_allowed_now()` hâlâ yalnız PLC'nin `xMoveToStartAllowed`'ını okuyor.

**Kullanıcıya/PLC tarafına iletildi:** PLC üzerinde elle TRUE bırakılan
`xMoveToStartRequest` varsa önce FALSE'a çekilmeli - HMI'nin pulse'u
(TRUE~150ms~FALSE) zaten TRUE olan bir bitten yeni bir yükselen kenar
oluşturmayabilir, ilk denemede tetiklenmeyebilir.

Kod: `config/opcua.json` (6 yeni satır, gitignore'lu - gerçek dosya), `ui/
machine/manual_page.py` (eksik-tag durumunda "TAG EKSİK" gösterimi).

Test: mevcut 235 test aynen geçti (config değişikliği test edilen kod
yolunu etkilemiyor). Gerçek config'in 6 anahtarı içerdiği + dolu/eksik
config'te buton enable/disable ve "TAG EKSİK" metni widget smoke testiyle
doğrulandı. Gerçek PLC'ye bağlı bir bağlantımız yok - butonun uçtan uca
çalıştığını (Allowed/Busy/Done okumaları dahil) onaylamak kullanıcının
elindeki sıradaki adım.

`.ai/Codex_Codesys.md`'ye HMI -> PLC yanıtı eklendi.

## 2026-09-21 - Manuel sayfa düzeni: buton yerleşimi, hizalama, jog hızı girişi (kullanıcı UI geri bildirimi)

Kullanıcı ekran görüntüsüyle 4 istek iletti: (1) "Başlangıç Konumuna Dön"
butonunu sol (X) karttaki boş kutuya taşı, boyut/hizalamayı düzelt; durum
bilgisi sağda (Y kartı) kalsın, "3 sn basılı tutun" bilgisini butonun içine
bir köşeye koy. (2) X+/- ile Y+/- aynı hizaya gelsin (X kontrollerini
yukarı taşı). (3) "JOG Yavaş/JOG Hızlı" butonları yerine iki eksen için
ayrı jog hızı girişi - zaten var olan `lr_x_jog_velocity`/`lr_y_jog_
velocity` ayar parametrelerine bağlı, yanına yanlışlıkla değiştirmeyi
önleyen bir "Düzenle" tik kutusu.

**Buton taşındı:** "Başlangıç Konumuna Dön" artık X Ekseni kartında (eski
boş spacer'ın yerinde); "BAŞLANGIÇ KONUMU" durum kartı Y Ekseni kartında
kalıyor. Hint metni artık ayrı bir satır değil, `HoldButton`'ın kendi
içine yerleştirilmiş bir `QVBoxLayout` (ana etiket ortada, "3 saniye basılı
tutun — X=.. Y=.. mm" sağ-alt köşede, küçük punto) - buton tıklama/basılı
tutma davranışı değişmedi, yalnızca görünüm.

**Hizalama kök nedeni düzeltildi:** X ve Y kartlarının içerikleri farklı
yükseklikte olduğu için (`QHBoxLayout` iki kartı eşit yüksekliğe zorluyor,
ama hiçbir kart kendi içinde `addStretch` kullanmıyordu) üst kısımlar
hizasız görünüyordu. Her iki kartın `body_layout()`'unun SONUNA `addStretch
(1)` eklendi - artık boşluk her zaman EN ALTTA kalıyor, X-/X+ ile Y-/Y+
pixel-hizalı (ekran görüntüsüyle doğrulandı).

**JOG Yavaş/Hızlı kaldırıldı - gerçek jog hızı parametresine bağlı giriş
geldi:** Bu iki buton gerçek modda zaten hiçbir PLC etkisi yaratmıyordu
(brif §28 açık notu: "jog hız seçimi için PLC tag'ı yok"; yalnız demo'nun
kendi sabit 30/90 ve 10/30 mm/s değerlerini seçiyordu). Kullanıcının
belirttiği gibi jog hızı zaten gerçek bir ayar parametresi olarak var
(`lr_x_jog_velocity`/`lr_y_jog_velocity`, GVL.lrX_JogVelocity/lrY_
JogVelocity) - şimdi Manuel sayfasında doğrudan bu parametreye bağlı bir
`QDoubleSpinBox` var, varsayılan kilitli (disabled); yanındaki "Düzenle"
tik kutusu işaretlenmeden değiştirilemez. Kilit açıkken `editingFinished`'da
`MachineService.set_parameter()` (Ayarlar sayfasıyla AYNI yol - aralık
doğrulama, `move_to_start_busy` kilidi, gerçek PLC yazma onayı/reddi dahil)
çağrılır; kilit kapatılınca yarım kalmış bir düzenleme atılır, canlı PLC
değerine geri dönülür. Ayarlar sayfasındaki "dirty" deseni (`valueChanged`
sadece gerçek kullanıcı düzenlemesinde işaretlenir, programatik `setValue`
`blockSignals` ile korunur) birebir tekrarlandı. Demo simülatörü de artık
jog hareketinde sabit hız yerine bu aynı parametreyi kullanıyor - Ayarlar'da
görülen değerle tutarlı.

`MachineService.jog_x`/`jog_y` ve `DemoSimulator.set_jog_x`/`set_jog_y`'den
artık hiçbir zaman etkisi olmayan `fast` parametresi tamamen kaldırıldı
(yarım bırakılmış bir soyutlama olarak tutulmadı).

Kod: `ui/machine/manual_page.py` (kart yeniden düzenleme, `_build_move_to_
start_button`, `_build_jog_velocity_row`, `_on_jog_edit_toggled`, `_commit_
jog_velocity`), `services/machine_service.py` + `services/demo_simulator.py`
(`fast` parametresi kaldırıldı, demo jog hızı gerçek parametreye bağlandı).

Test: mevcut 235 test aynen geçti (jog `fast` parametresinin kaldırılması
hiçbir testi bozmadı - zaten hiçbiri `fast=` geçmiyordu). Yeni davranış
(kilit aç/kapa, dirty-commit, geçersiz değer reddi, hizalama) widget smoke
testi + gerçek render edilmiş ekran görüntüsüyle doğrulandı - bu projede
UI widget davranışı için süregelen desen (servis katmanı pytest, ekran
davranışı smoke test).

## 2026-09-21 - "Başlangıç Konumuna Dön" tek buton, 3s basılı tutuş (PLC-HMI-20260921-10/11, C5)

Kullanıcı: "Sana 11 numaralı görevi iletti ajan kontrol et. HMI manuel
sayfasına koyacağımız bir buton olacak 0'a göndermek için." Kaynak: `.ai/
Codex_Codesys.md` (mesaj 10 aday sözleşme, mesaj 11 kullanıcı UI talebi) +
`.ai/HMI_C5_MOVE_TO_START_20260921.md` + `.ai/HMI_C5_HOLD_BUTTON_20260921.md`
(H5-HOLD-T01..T08 test listesi dahil).

**Yeni tag'ler (6, YENİ - C5 PLC tarafında henüz build/test edilmedi):**
`GVL.xMoveToStartRequest` (BOOL pulse, HMI yazar) + 5 salt okunur:
`xMoveToStartAllowed/Busy/Done/Aborted/Error`. X hedefi `lrX_CutStartPos`,
Y hedefi `lrY_CenterPosition` (ayarlar parametresi - sabit 0 veya MC_Home
DEĞİL). Yalnız `config/opcua.example.json`'a eklendi - C0.4'teki aynı
disiplinle GERÇEK `config/opcua.json`'a EKLENMEDİ (online doğrulanmamış
node canlı bağlantıyı bozabilir riski); PLC build/export edip online
sembolleri doğruladıktan sonra kullanıcı (veya onayıyla biz) ekleyecek.

**UI - eski buton tamamen kaldırıldı:** "MERKEZE GİT / Y=0" (yalnız Y) yerine
tek "Başlangıç Konumuna Dön" (X+Y) `HoldButton`'ı geldi, alt metin hedefleri
(ayarlar onaylıysa "X=.. Y=.. mm", değilse jenerik) gösterir. `MachineService.
y_center()`/`cmd_y_center` koda dokunulmadı - hâlâ geçerli bir PLC komut
kapasitesi, yalnızca artık hiçbir HMI butonuna bağlı değil (silmek ayrı,
istenmeyen bir karar olurdu).

**3 saniye kesintisiz basılı tutuş (kullanıcı talebi, H5-HOLD-T01-T05):**
`ManualPage` içinde tek-atışlı `QTimer(3000ms)` + 100ms'lik ikinci bir
timer'la görünür geri sayım ("Basılı tutun… 2.4s"). Erken bırakma, pointer
butondan çıkması (`HoldButton.leaveEvent` zaten `held(False)` üretiyordu),
pencere odağı kaybı (`applicationStateChanged`), sayfa değişimi
(`hideEvent`), izin kaybı/stale/bağlantı kaybı (her `_on_snapshot`'ta
`move_to_start_allowed_now()` yeniden kontrol edilir) - hepsi timer'ı
durdurup sıfırlar; kuyruklanmış gecikmeli hareket yok, yeniden denemek YENİ
bir basış+3s ister. Süre TAM dolduğunda (T02) - parmak hâlâ basılı kalsa
bile - tek pulse: `_move_to_start_holding` bayrağı yalnız gerçek bırakışta
(`held(False)`) sıfırlanır, bu yüzden aynı fiziksel basış ikinci bir
sayaç/pulse asla üretemez (auto-repeat/gecikmiş timer/UI disable-enable
döngüsü de dahil - hepsi widget smoke testiyle doğrulandı).

**"İzin HMI'da yeniden üretilmez" (görev notu, bilinçli tasarım farkı):**
Bıçak/baskı'nın aksine burada ayrıntılı bir ön koşul listesi (manuel+servo+
emergency+eksen durmuş...) TEKRARLANMAZ - `MachineService.move_to_start_
allowed_now()` yalnızca PLC'nin kendi `xMoveToStartAllowed`'ını okur (+ tag
varlığı/stale/bağlantı kontrolü).

**"Yeni isteğin readback geçişlerini izle, belirsizse tamamlandı iddia
etme" (H5-HOLD-T07, en kritik parça):** Bir pulse gönderildikten hemen sonra
`xMoveToStartDone` hâlâ ÖNCEKİ başarılı hareketten kalma TRUE (latched)
olabilir - bunu yeni komutun sonucu saymak yanlış bir "TAMAMLANDI" gösterirdi.
`_update_move_to_start_status`: gönderim sonrası önce "cleared" (ya Busy
TRUE görüldü ya da Done/Aborted/Error'ın ÜÇÜ DE FALSE görüldü - PLC eski
latch'i gerçekten temizledi) beklenir; ancak o noktadan sonraki bir
Done/Aborted/Error TRUE'su BU isteğin sonucu sayılır. Zaten-hedefte hızlı
tamamlanma (Busy hiç gözlenmeden, done/aborted/error'ın FALSE görülmesi tek
başına yeterli) da doğru işleniyor - ayrı test edildi.

**Gerçek OPC UA yazma reddi UI'ya taşınıyor (C0.4'teki aynı mekanizma,
genişletildi):** `MOTION_COMMAND_TAGS = {"cmd_move_to_start"}`, `_on_error`
bunu da `commandWriteError`e yönlendirir VE doğrudan `_move_to_start_status`u
"error"a çeker - aksi halde PLC pulse'u hiç görmediyse (örn. BadNodeIdUnknown)
Busy/Done/Aborted/Error asla değişmeyeceği için durum sonsuza dek "sent"te
asılı kalırdı.

**Busy, `xCycleActive` DEĞİL - HMI AYRICA kilitler (görev notu):** `_manual_
allowed()` (jog), `_mode_change_allowed()` (mod), `_pneumatic_common_
allowed()` (bıçak/baskı dört buton) hepsine `not snap.move_to_start_busy`
eklendi; `set_parameter()` Busy'de `ValueError` fırlatır ("Başlangıç
konumuna dönüş sürüyor - ayar değişikliği şu an kilitli."). `request_stop()`
hiçbir zaman kilitlenmedi - "Stop açık" şartı korundu.

**Eksik tag/bağlantı/stale'de buton hiç etkinleşmez** (`move_to_start_tags_
configured()`, C0.4 emsaliyle aynı desen) - dinamik tooltip hangi tag(ler)in
online doğrulanmadığını söyler.

Kod: `core/models.py` (5 yeni MachineSnapshot alanı), `services/machine_
service.py` (`MOTION_COMMAND_TAGS`, `_update_move_to_start_status`, `move_
to_start_tags_configured`/`move_to_start_allowed_now`/`move_to_start_status`/
`request_move_to_start`, dört gating fonksiyonuna+`set_parameter`'a Busy
kilidi), `services/demo_simulator.py` (`_apply_move_to_start` - Allowed'ı her
tick yeniden hesaplar, kısa simüle hareket), `ui/machine/manual_page.py`
(eski buton kaldırıldı, 3s hold-to-confirm mantığı, durum kartı).

Test: `tests/test_move_to_start.py` (24, yeni - izin, gönderim, edge-
detection, busy-kilitleri, demo tam döngü). UI'daki gerçek-zamanlı 3s sayaç
davranışı (erken bırakma, tam 3s, basılı kalırken ikinci pulse yok, eksik-tag
guard) widget smoke testiyle ayrıca doğrulandı. Tam suite 235/235. Gerçek
PLC'ye kendi kendine yazılmadı/hareket başlatılmadı - H5-HOLD-T08 (fiziksel
hareket) ve C5'in genel online doğrulaması kullanıcıyı bekliyor.

`.ai/Codex_Codesys.md`'ye HMI -> PLC yanıtı eklendi.

## 2026-09-21 - C0.4 takibi: gerçek config eşlemesi + eksik-tag koruması + gerçek yazma reddi UI'da

Kullanıcı: "C0.4 aşağı butonlarının bağlantısı gerçek config/opcua.json
dosyasında eksik. PLC'de yeni request'lerin Symbol Configuration üzerinden
yayımlandığını doğrulayarak ... eşlemeleri tamamla. ... Eksik tag varken
butonu etkinleştirme veya 'gönderildi' gösterme. Gerçek OPC yazma sonucunu
göster; yalnız demo testi yeterli değil. Valf komutlarına doğrudan yazma."

**Gerçek config tamamlandı:** PLC tarafı 4 tag'i (`xBladeDownRequest`,
`xClampDownRequest`, `xAlarmStopRequest`, `xManualPreparationRequired`)
Symbol Configuration'da yayımladığını doğruladı - `cmd_blade_down`,
`cmd_clamp_down`, `alarm_stop_request`, `manual_preparation_required`
NodeId'leri artık gerçek yerel `config/opcua.json`'a da eklendi (önceki
turda kasıtlı olarak yalnız `example.json`'da bırakılmıştı).

**Eksik-tag koruması (yeni):** `MachineService.blade_down_tags_configured()`
/ `clamp_down_tags_configured()` - demo modda her zaman True, gerçek modda
kendi pulse tag'i VE paylaşılan `alarm_stop_request`/`manual_preparation_
required` okumalarının HEPSİ `config.nodes` içinde mi diye bakar. `manual_
blade_down_allowed()`/`manual_clamp_down_allowed()` bu kontrolü ilk sıraya
aldı - eksikse buton hem devre dışı kalır hem `request_blade_down()`/
`request_clamp_down()` hiç pulse göndermeden `False` döner. Yukarı (Retract)
tag'leri zaten doğrulanmış olduğu için bu kontrole tabi değil; bir mekanizma
eksik olsa bile diğerini ve Yukarı'yı etkilemez (test: `test_missing_down_
tags_do_not_affect_retract_which_stays_allowed`).

**"Gönderildi" artık iyimser değil:** `request_blade_retract`/`request_
clamp_retract`/`request_blade_down`/`request_clamp_down` hepsi `bool` döner
(gönderim gerçekten kalktı mı). `manual_page.py`'deki dört click handler
yalnız `True` dönerse `_blade_last_cmd`/`_clamp_last_cmd`'yi günceller -
izin/tag eksikliği yüzünden reddedilen bir tıklama artık asla "GÖNDERİLDİ"
göstermez.

**Gerçek OPC UA yazma reddi UI'ya taşınıyor:** Yeni `MachineService.
commandWriteError` sinyali (`str tag, str reason`) - `_on_error` artık
`PNEUMATIC_COMMAND_TAGS` (`cmd_blade_retract`/`cmd_clamp_retract`/`cmd_
blade_down`/`cmd_clamp_down`) ile eşleşen gerçek bir `errorOccurred` (örn.
`BadNodeIdUnknown`, `BadUserAccessDenied`) gördüğünde bunu emit eder -
parametre yazmalarındaki `parameterWriteError` ile aynı prensip, artık pulse
komutları için de var. `manual_page.py::_on_command_write_error` "Son Komut"
kartını "HATA — PLC REDDETTİ" (fault) yapar ve `QMessageBox.warning`
gösterir - demo testi tek başına bunu doğrulayamazdı, bu artık gerçek bir
OPC UA reddini temsil eden senaryoyla (`_on_error` çağrısıyla) test ediliyor.

**Değişmeyen:** Valf komutlarına (`xBladeValveCmd`/`xClampValveCmd`) hâlâ
hiçbir yerden yazılmıyor - yalnız `cmd_*` request pulse'ları.

Kod: `services/machine_service.py` (`PNEUMATIC_COMMAND_TAGS`,
`commandWriteError`, `_tags_configured`/`blade_down_tags_configured`/
`clamp_down_tags_configured`, dört `request_*` artık bool döner), `ui/
machine/manual_page.py` (`_on_command_write_error`, click handler'lar bool
kontrolü, devre dışı Aşağı butonlarında dinamik tooltip), `config/opcua.json`
(4 yeni NodeId, gerçek).

Test: `tests/test_manual_down_requests.py` 26 -> 33 (eksik-tag + `command
WriteError` testleri). Tam suite 211/211. Gerçek PLC'ye kendi kendine
yazılmadı - online test kullanıcıyı bekliyor.

`.ai/Codex_Codesys.md`'ye HMI -> PLC yanıtı eklendi.

## 2026-09-21 - Manuel Bıçak/Baskı Aşağı talepleri eklendi (PLC-HMI-20260921-09)

Kullanıcı: "Manuel durumda bıçak ve baskı kontrolü için sistemin nasıl
olması gerektiğine dair ... 09 numaralı bağlantı notunu ilettim." Kaynak:
`.ai/Codex_Codesys.md` (mesaj 09) + `.ai/HMI_MANUAL_DOWN_REQUESTS_20260921.md`.
PLC ST teslimi hazır; `xBladeDownRequest`/`xClampDownRequest` PLC'de henüz
build/export/online doğrulanmadı.

**Yeni tag'ler (2 yazma, YENİ - GVL'de henüz online doğrulanmadı):**
`GVL.xBladeDownRequest` / `GVL.xClampDownRequest` (BOOL pulse, mevcut
`command_pulse_ms` mekanizmasıyla, 100-250ms TRUE->FALSE). Var olan Yukarı
(`xBladeRetractRequest`/`xClampRetractRequest`) korunuyor.

**Ortak izin sıkılaştırıldı (dört buton da):** `MachineService.
_pneumatic_common_allowed()` artık MANUAL state (literal eMachineState=10,
eskisi gibi yalnızca "AUTO_CYCLE_ACTIVE_STATES dışı" değil) + xManualMode +
xEmergencyOK + NOT xAlarmStopRequest + NOT xMotionStop + her iki eksenin
durmuş olması (|vel| <= 0.5 mm/s, vision_simulator.py'deki aynı toleransla
tutarlı) + jog request'lerinin bırakılmış olması (HMI kendi jog-aktif
durumunu yerel izliyor, PLC'ye geri-okuma yapmıyor) kontrol ediyor. Yukarı
(Retract) da bu daha eksiksiz kontrole taşındı - eskiden yalnız `_manual_
allowed()` (manual_mode + cycle_state not in AUTO_CYCLE_ACTIVE_STATES)
kullanıyordu.

**Aşağı'ya özel ek şart:** `xManualPreparationRequired` FALSE + fiziksel
besleme pushbuttonları (`FeedForwardPB`/`FeedReversePB`) ve besleme motoru
kapalı. Hazırlıkta (`xManualPreparationRequired`=TRUE) Yukarı serbest kalır,
Aşağı pasif kalır - görev notundaki "Hazırlıkta Yukarı kullanılabilir, Aşağı
pasif kalır" birebir uygulandı.

**Yukarı önceliği:** Aynı mekanizmanın Yukarı pulse'u hâlâ "iş başında"
sayılan pencerede (command_pulse_ms) Aşağı reddedilir - `MachineService`
içinde `_blade_retract_pulse_until`/`_clamp_retract_pulse_until` zaman
damgasıyla takip edilir. İki mekanizma (bıçak/baskı) birbirinden bağımsız.

**Aşağı'ya PLC-onaylı kabul biti YOK (görev notu, bilinçli tasarım - "Yeni
asagi-kabul biti eklenmedi").** Demo tarafında Aşağı kabul edilince ilgili
`blade_retract_accepted`/`clamp_retract_accepted` FALSE'a çekiliyor (gerçek
PLC'nin davranışını taklit eder). Manuel sayfada "Yukarı Talebi" kartı "Son
Komut" olarak yeniden adlandırıldı: Yukarı için PLC kabulünü ("YUKARI: KABUL
EDİLDİ"), Aşağı için yalnızca gönderildiğini ("AŞAĞI: GÖNDERİLDİ" - kanıt
DEĞİL) ayrı ayrı gösteriyor; Sensör kartı (BladeZDown/ClampDown) tek fiziksel
kanıt olarak duruyor.

**Config:** `cmd_blade_down`/`cmd_clamp_down`/`alarm_stop_request`/`manual_
preparation_required` yalnızca `config/opcua.example.json`'a eklendi - PLC
henüz deploy etmediği için GERÇEK yerel `config/opcua.json`'a EKLENMEDİ
(online doğrulanmamış bir NodeId, canlı okuma döngüsünü bozabilir riski).
`emergency_ok`/`motion_stop`/`feed_forward_input`/`feed_reverse_input` ise
2026-09-18 GVL kaynağında zaten doğrulanmış (var olan) tag'ler olduğu için
hem example hem gerçek config'e eklendi - ayrıca `feed_forward_input`/
`feed_reverse_input` daha önce hiç NodeId'si olmayan, sessizce hep varsayılan
kalan iki alandı; bu iş sırasında fark edilip düzeltildi.

Kod: `core/models.py` (4 yeni MachineSnapshot alanı), `services/
machine_service.py` (`_pneumatic_common_allowed`, `_manual_down_extra_
allowed`, `manual_pneumatic_allowed`/`manual_blade_down_allowed`/`manual_
clamp_down_allowed`, `request_blade_down`/`request_clamp_down`, jog-aktif
takibi), `services/demo_simulator.py` (Aşağı taklip + Yukarı-öncelik +
kabul-sıfırlama), `ui/machine/manual_page.py` (Aşağı butonları etkinleştirildi,
"Son Komut" kartı, tek-kaynak izin kontrolü UI'da tekrar edilmiyor).

Test: `tests/test_manual_down_requests.py` (26, yeni) + `tests/
test_blade_clamp_retract.py` (10, sıkılaştırılmış ortak izne göre güncellendi
- artık `stale=False`/`connection_state=CONNECTED`/`cycle_state=MANUAL`
açıkça set ediliyor). Tam suite 204/204. Gerçek PLC'ye kendi kendine
yazılmadı/hareket başlatılmadı - online test kullanıcıyı bekliyor.

`.ai/Codex_Codesys.md`'ye HMI -> PLC yanıtı eklendi.

## 2026-09-18 - Manuel Bıçak/Baskı Yukarı gerçek PLC request'lerine bağlandı (PLC-HMI-20260918-06)

Kullanıcı, PLC notlarında `xBladeRetractRequest`/`xClampRetractRequest`
GVL değişkenlerini gördüğünü bildirdi. Araştırma (subagent, PLC koordinasyon
paketi + `.ai/HMI_PNEUMATIC_ALARM_CONTRACT_20260918.md` ve `.ai/HMI_
OPERATOR_RECOVERY_MESSAGES_20260918.md` - zaten mirror'lanmış, önceden
uygulanmamış tam bir sözleşme) doğruladı: 4 gerçek tag - `xBladeRetractRequest`/
`xClampRetractRequest` (HMI pulse-write) + `xBladeRetractAccepted`/
`xClampRetractAccepted` (PLC-üretimli, salt okunur). Manuel "Aşağı" için
PLC'de HENÜZ bir request tanımlı değil - ayrı, açık bir PLC görevi; tag adı
uydurulmadı.

### Kök sorun
`ui/machine/manual_page.py`'deki 4 Bıçak/Baskı butonu (Aşağı+Yukarı, HoldButton,
hold-to-run) `MachineService.set_blade/set_clamp` üzerinden `cmd_blade_down/up`,
`cmd_clamp_down/up` diye TAMAMEN HAYALİ, config'de hiç eşlenmemiş tag'lere
yazıyordu - gerçek modda bu yazılar hiçbir yere gitmiyordu (yalnız demo modda
görünür bir etkisi vardı).

### Düzeltme
- `config/opcua.json`/`.example.json`: 4 yeni NodeId - `cmd_blade_retract`,
  `cmd_clamp_retract` (yazma), `blade_retract_accepted`, `clamp_retract_
  accepted` (okuma).
- `core/models.py`: `MachineSnapshot.blade_retract_accepted/clamp_retract_
  accepted` (salt okunur).
- `services/machine_service.py`: `set_blade`/`set_clamp` (hayali, hold-to-run)
  TAMAMEN KALDIRILDI; yerine `request_blade_retract()`/`request_clamp_
  retract()` - `_manual_allowed()` ile kapılı, gerçek `request_pulse` (TRUE~
  150ms~FALSE) ile yazıyor. `_on_raw_snapshot` iki accepted bitini okuyor.
- `services/demo_simulator.py`: hold-based `blade_cmd`/`clamp_cmd` kaldırıldı;
  `request_blade_retract()`/`request_clamp_retract()` bir sonraki tick'te
  ilgili ekseni "yukarı/açık" yapıp `*_retract_accepted=True` yapıyor - PLC'nin
  gerçek FAULT'ta bu bitleri sıfırlama davranışı da taklit edildi.
- `ui/machine/manual_page.py`: 4 buton yerine 2 buton ("Bıçağı/Baskıyı Geri
  Çek (Yukarı)", pulse-click) + kalıcı DEVRE DIŞI "Aşağı" butonu (tooltip:
  "PLC tarafında henüz tanımlı değil") + 2 durum kartı (Sensör: AŞAĞI/AÇIK -
  "YUKARI" değil, çünkü ayrı bir yukarı sensörü yok, görev notu; Yukarı
  Talebi: BEKLENİYOR/KABUL EDİLDİ, PLC'nin accepted bitinden).
- `tests/test_blade_clamp_retract.py` (10 test): pulse gönderimi + manual/
  cycle-active gating, accepted bitlerinin direkt okunması, demo simülatörün
  tick sonrası doğru state'e geçmesi, iki talebin bağımsızlığı, FAULT'ta
  accepted sıfırlanması. Widget-seviyesi smoke test ile de doğrulandı. Tam
  suite: **178/178 yeşil**. Gerçek PLC'ye kendi kendine yazılmadı.
- `.ai/Codex_Codesys.md`'ye HMI->PLC yanıtı eklendi.

### Kapsam dışı (bilinçli, bu turda yapılmadı)
H4 (4 alarm BOOL mapping + tarihçe), operatör state-mesaj akışı (doc 05),
Başlangıca Git (H5) - hepsi ayrı, daha büyük iş; kullanıcı isterse sıradaki
adım olarak yapılabilir.

### Düzeltme (aynı gün): "AÇIK" -> "YUKARI"
Kullanıcı "AÇIK" yerine "YUKARI" istedi (ekran görüntüsüyle). Sensör
mantığı/okunan tag değişmedi - `manual_page.py`'deki metin geri alındı.

## 2026-09-18 - Düzeltme: temizlenen alarm ana ekrandan gitmiyordu + Alarmlar sayfası 2 sekme

Kullanıcı ekran görüntüsüyle bildirdi: Reset sonrası "TEMİZLENDİ" durumundaki
kayıtlar hâlâ ana ekran panosunda görünüyordu (panoyu sadece severity'e göre
filtreliyordum, `active` durumuna bakmıyordum). Ayrıca ayrı ALARMLAR
sayfasının tek, karışık bir tablo yerine "Güncel Alarmlar" (aktif) / "Geçmiş
Alarmlar" (tümü) şeklinde iki sekme olmasını istedi.

- `ui/machine/machine_page.py::_refresh_alarm_table`: artık önce
  `event.active` (cleared_at yok) ile filtreleyip SONRA severity filtresini
  uyguluyor - temizlenen bir kayıt Reset'ten sonra panoda kalmıyor.
- `ui/machine/alarm_page.py`: `QTabWidget` ile iki sekme - "Güncel Alarmlar"
  (yalnız aktif) ve "Geçmiş Alarmlar" (tümü, temizlenmiş dahil - tam
  denetim izi). Aynı `alarmsChanged` sinyalinde her ikisi birlikte yenilenir.
- Widget-seviyesi smoke test: clear_active() sonrası ana ekran panosu VE
  "Güncel Alarmlar" sekmesi 2->0 satıra düşüyor, "Geçmiş Alarmlar" sekmesi
  2 satırda (TEMİZLENDİ etiketiyle) kalıyor - beklendiği gibi. Tam suite
  değişmedi (168/168, bu saf UI/görüntüleme mantığı, yeni pytest gerekmedi
  - mevcut `filter_alarm_events`/severity testleri davranışı zaten kapsıyor).

## 2026-09-18 - Ana ekrana Alarm/Uyarı/Mesaj panosu (H4'ün canlı-tag-
bağımsız kısmı, kullanıcı isteği)

Kullanıcı ana ekranda Start/Stop/Reset altındaki boş alana filtre edilebilir
bir Alarm/Uyarı/Mesaj tablosu istedi ("sadece uyarı/mesaj/hata gibi ama
defaultda hepsi gözüksün, onları dolduracağız"). Bu, H4'ün zaten onaylanmış
"ekran/tarihçe modeli hazırlanabilir; canlı alarm tagları tahmin edilmez"
kapsamına giriyor - canlı PLC alarm bağlanmadı, sadece ekran+veri modeli.

- `persistence/alarms.py`: `AlarmEvent.severity` alanı (ALARM/UYARI/MESAJ,
  varsayılan ALARM - geriye uyumlu). `code` artık nullable (Uyarı/Mesaj'ın
  sabit bir kod tablosu olmak zorunda değil). Yeni `log_event(severity,
  source, message, code=None)`; `raise_alarm` davranışı değişmeden buna
  delege ediyor.
- `persistence/db.py::_migrate_alarm_events_severity`: `create_all()`
  yalnız EKSİK TABLOLARI oluşturur, mevcut tabloya sütun eklemez - kullanıcının
  gerçek `data/bufera.db`'sindeki 10 eski satır `severity` sütunu olmadan
  duruyordu. `ALTER TABLE ... ADD COLUMN severity DEFAULT 'ALARM'` ile
  otomatik yükseltildi; gerçek dosya üzerinde doğrulandı, veri kaybı yok.
- `ui/machine/machine_page.py`: `_build_alarm_panel` - 3 checkbox (Hata/
  Uyarı/Mesaj, hepsi varsayılan işaretli) + 4 sütunlu (Saat/Tür/Kaynak/
  Mesaj) tablo, `alarmsChanged` sinyalinde yenileniyor. Saf `filter_alarm_
  events()` fonksiyonu Qt'siz test edilebilir.
- `ui/machine/alarm_page.py`: ayrı tam-ekran Alarmlar sayfasına da "Tür"
  sütunu eklendi (filtre eklenmedi, istenmedi).
- `tests/test_alarm_severity.py` (8 test): filtre fonksiyonu, log_event/
  raise_alarm severity davranışı, migration'ın eski şemalı bir tabloyu
  veri kaybetmeden yükselttiği - hepsi İZOLE bir tmp_path DB'sinde (test
  sonunda global engine varsayılana geri döndürülüyor - bkz. bilinen
  SettingsStore izolasyon sorunu, henüz kalıcı çözülmedi).
- Widget-seviyesi smoke test: filtre kutuları gerçekten satır sayısını
  değiştiriyor (3 -> 1 -> 3). Tam suite: **168/168 yeşil**.

## 2026-09-18 - H1/H2/H3/H6 (PLC-HMI-20260918-04, kullanıcı onaylı liste)

Kaynak: `.ai/HMI_TEST_FINDINGS_TASKS_20260918.md` + `docs/18_PLC_HMI_TASK_
PLAN.md` (PLC tarafı koordinasyon paketinde). Kullanıcı H1/H2/H3/H6'yı onayladı;
H4/H5/H7 PLC C2/C5/C4 sözleşmesini bekliyor, DOKUNULMADI.

### H1 - Metin/state tutarlılığı
`ui/machine/machine_page.py`: "MANUEL AKTİF" -> "OPERATÖR KONTROLÜ" (ÇEVRİM
DURUMU kartındaki "Manuel" ile karışıklık yaratıyordu). Gösterge artık
`snap.feed_manual_allowed`'a tek başına güveniyor (`cycle_active` ile ikinci
kez kapatılmıyor) - PLC "Auto çevrimde FALSE olacak" diyor, MANUAL modda VEYA
WAIT_FOR_MATERIAL'da (cycle_active öncesi) izinli olabilmesi gerekiyordu.
ÇEVRİM DURUMU zaten doğrudan `eMachineState`'ten geliyordu (doğrulandı,
değişiklik gerekmedi).

### H2 - Mod değiştirme kilidi
`ui/machine/manual_page.py`: "Manuel Modu Etkinleştir" butonu `cycle_active`
VEYA stale iken disable (yalnız CUTTING değil, hazırlık/dönüş dahil tüm
çevrim - `cycle_active` zaten çevrimin tamamını kapsıyor).
`services/machine_service.py::_mode_change_allowed`/`set_manual_mode`: aynı
engel SERVİS seviyesinde de var - UI dışından çağrı da yazı üretmez;
stale/disconnected/bilinmeyen durumda fail-closed. `tests/
test_mode_change_guard.py` (8 test).

### H3 - Başlatma engeli bilgisi
`ui/machine/machine_page.py::compute_start_inhibit_reasons` (yeni, saf
fonksiyon): StartPermitted=FALSE nedenini PLC'nin zaten yayınladığı alt
bileşenlerden (emergency/servo/vision/x_at_start/y_at_center, manual_mode,
cycle_active) açıklar - `xStartPermitted`'i yeniden hesaplamaz, sadece
bilgilendirir. X/Y nedenlerinde sıfır yerine gerçek `lrX_CutStartPos`/
`lrY_CenterPosition` değeri gösterilir, ikisi birlikte gösterilebilir.
"Stop basılı" nedeni YOK - gerçek bir "şu an basılı" tagı yayınlanmıyor,
bulunmayan tag için tahmin yapılmadı (görev notu). `tests/
test_start_inhibit_reasons.py` (12 test).

### H6 - Eğimli otomatik kamera senaryosu
`services/vision_simulator.py`: varsayılan "straight" (düz çizgi, TargetY=
canlı lrY_CenterPosition) değişmedi. Yeni "tilted" senaryosu:
`set_camera_scenario("tilted", slope)` - yalnız auto_camera PASİFKEN
değiştirilebilir (referans cycle ortasında sıçramasın, görev notu). Üç
katmanlı ön-kontrol: `abs(slope) <= lrMaxAllowedSlope` (gerçek PLC okuması),
türetilen Y feed-forward hızı (`|slope|*lrX_CutVelocity <= lrY_MaxVelocity`,
PLC decision log formülü), kesim sonunda (`lrX_CutEndPos`) hedef Y'nin
Y yazılım sınırları içinde kalması. Referans (x0,y0) `start_auto_camera`'da
BİR KEZ yakalanır (`_tilt_reference`), tick'lerde TargetY = y0+m*(TargetX-x0)
olarak üretilir - sabit artış YOK. `send_packet`'e AYRICA, senaryo bağımsız,
gerçek zamanlı bir Y-sınır kontrolü eklendi ("sınır dışı yolun reddi" -
referans kabul edilse de anlık hedef sınır dışına çıkarsa paket reddedilir).
Diagnostic panelde senaryo + son hedef X/Y gösteriliyor. `tests/
test_tilted_camera_scenario.py` (15 test): pozitif/negatif/sıfır eğim,
3 ayrı red senaryosu, son nokta ileri hedefi, referansın sıçramaması,
disarm/reconnect'in referansı temizlemesi, düz çizginin etkilenmemesi.

### Yan bulgu: paylaşımlı SettingsStore testleri kirletiyor
`persistence/settings_store.py`/`db.py` tek bir sabit dosyaya
(`data/bufera.db`) yazıyor - `config_path` gibi izole edilebilir değil.
Bu oturumdaki testler (ve smoke script'ler) gerçek yerel DB'ye `lr_x_cut_
end_pos=300`, `t_vision_heartbeat_timeout=900` gibi değerler yazmış; DEMO
modda gerçek PLC yokken bunlar "gerçek" gibi görünebilirdi. `data/bufera.db`
içindeki `engineering_settings` tablosu TEMİZLENDİ (alarm_events'e
dokunulmadı). **Kalıcı düzeltme yapılmadı** - `MachineService`'e
`config_path` gibi bir `settings_db_path` enjeksiyonu + ~10 test dosyasının
güncellenmesi gerekir; bu H1-H6 kapsamı dışında, kullanıcıya soruldu.

Tam suite: **160/160 yeşil** (test çalıştırma DB'yi tekrar kirletir - bilinen,
zararsız/kozmetik bir yan etki, gerçek PLC bağlıyken ~100ms içinde ezilir).

## 2026-09-18 - Ayarlar tablosuna "Sınır" sütunu (kullanıcı isteği)

Kullanıcı: "Ayarlar ekranına bir sütun koyarak sınırları gösterelim...
adam hızı 20000 yapamaz sonuçta." `ui/machine/settings_page.py`: grid'e
Birim ile Uygula arasına `spec.min_value`/`max_value`'dan üretilen bir
"Sınır" sütunu eklendi (örn. "1 — 500"). Sadece görüntüleme; spinbox
`setRange` zaten aynı sınırı uyguluyordu (davranış değişmedi, sadece artık
görünür). Demo modda tüm 16 parametrenin gösterdiği aralık gerçek
`PARAMETER_SPECS` değerleriyle karşılaştırılıp doğrulandı. Tam suite
etkilenmedi (125/125).

## 2026-09-18 - Vision simülatörü butonuna şifre kapısı (kullanıcı isteği)

Kullanıcı: "kamera sim butonuna bir şifre koyabilir misin? şifre 90327
olsun. 5 haneli. sim tarafını açmak için şifre istesin... kapattım tekrar
girdim yine şifre istesin."

- `ui/machine/settings_page.py`: `VISION_SIM_PASSWORD = "90327"` (kaynak
  kodda düz metin - kullanıcı bilerek istedi; gerçek güvenlik sınırı değil,
  önceki görev notunun da belirttiği gibi hard-coded parola "yetki" sayılmaz
  - bu yüzden mevcut Mühendislik Erişimi kapısı KALDIRILMADI, üzerine
  eklendi). `_open_vision_simulator`, dialog'u oluşturmadan/göstermeden
  önce her çağrıda `_prompt_vision_sim_password()` çağırır - hiçbir yerde
  "bu oturumda zaten girildi" önbelleği yok, pencere kapatılıp tekrar
  açılsa (hatta aynı SettingsPage örneğinde defalarca) her seferinde sorar.
  Yanlış/iptal → dialog açılmaz.
- `tests/test_settings_vision_sim_password.py` (5 test, demo mod): yanlış
  şifre reddediyor, iptal reddediyor, doğru şifre açıyor, kapat-aç tekrar
  soruyor (call_count ile doğrulandı), kapat sonrası yanlış şifreyle tekrar
  açılamıyor. Tam suite: **125/125 yeşil**.

Not: repo public (`kolektif_360`), şifre commit edilirse kaynak kodda düz
metin olarak herkese görünür olacak - bu turda kullanıcıya ayrıca iletildi.

## 2026-09-18 - Kullanıcı güncel GVL kaynağını paylaştı - kayıt edildi

Kullanıcı, sorunu çözüldükten sonra ek bilgi olarak PLC'nin TAM güncel GVL
kaynağını paylaştı. Ham kaynak + doğrulanan bulgular:
`.ai/PLC_GVL_REFERENCE_2026-09-18.md`. Öne çıkanlar:
- Kalıcı makine parametreleri gerçekten `REAL` (32-bit) - `LREAL` değil.
  Bu, aynı gün düzeltilen `BadTypeMismatch` hatasının kesin kök nedenini
  doğruluyor (bkz. `.ai/memory/DECISIONS.md` 2026-09-18 girişi).
- `tVisionHeartbeatTimeout` tipi `TIME` (`T#2s`) - HMI bunu düz ms `float`
  olarak okuyor/gösteriyor; şimdiye kadar bir hata bildirilmedi ama
  izlenmesi gereken bir alan olarak not edildi.
- PLC'nin GÜNCEL varsayılanları `core/parameters.py`'deki 3 alanla
  (lrX_CutVelocity, lrX_ReturnVelocity, lrX_CutEndPos) farklı - muhtemelen
  motorlar mekanikten ayrıyken masa testi için düşürülmüş. Kod tarafı
  BİLEREK değiştirilmedi (Ayarlar ekranı zaten bu local varsayılanları
  gerçek değer gibi göstermiyor, gerçek PLC okumasıyla ezilir); kullanıcı
  netleştirirse güncellenebilir.
Kod değişikliği yapılmadı - bu tamamen referans/kayıt amaçlı bir giriştir.

## 2026-09-18 - Kalıcı çözüm: OPC UA yazımı sunucudan gerçek tipi soruyor

Önceki turda eklediğimiz `parameterWriteError` sayesinde kullanıcı gerçek
hatayı gördü: **BadTypeMismatch** - X Kesim Hızı (LREAL/float, doğru şekilde
Double'a çıkarılıyordu) ve X Kesim Bitiş için de. Bu, `EXPLICIT_VARIANT_
TYPES` yaklaşımının (tag başına tahmin) ölçeklenmediğini kanıtladı: Python
float'ın Double'a çıkarılması TEKNİK OLARAK DOĞRU olduğu halde sunucu
reddetti - yani bu node'un gerçek advertised DataType'ı Double değil
(muhtemelen Float/Single). Tag bazında tahmin etmek yerine kalıcı çözüm.

### Düzeltme (`plc/opcua_client.py`)
- `_write_checked` artık `EXPLICIT_VARIANT_TYPES`'ta olmayan HER tag için
  sunucuya SORUYOR: `Node.read_data_type_as_variant_type()` (asyncua 2.0.1'de
  mevcut bir helper) - node'un gerçek advertised DataType'ını okur, tag
  başına bir kez, sonucu bağlantı ömrü boyunca cache'ler (reconnect'te
  temizlenir). Sunucu farklı bir tip bildirirse (örn. Float, Double değil)
  ONUNLA yazılır - artık HER LREAL/Double parametre, jog/manual_mode BOOL'u,
  ileride eklenecek her yeni tag için otomatik doğru; tag bazında tahmin/
  liste büyütme gerekmiyor.
- Sunucu sorgusu başarısız olursa (ör. okuma da reddedilirse) eski davranışa
  (asyncua'nın Python tipinden çıkarımı) düşülür - regresyon riski yok.
- `EXPLICIT_VARIANT_TYPES` (vision_sequence/heartbeat) öncelik olarak kalıyor
  - kaynak kodundan zaten kesin bilinen 2 tag için sıfır-round-trip hızlı yol.
- `tests/test_opcua_variant_types.py`'ye 3 yeni test: sunucu farklı tip
  bildirince o kazanıyor, sonuç tag başına cache'leniyor (tekrar sorgu yok),
  sorgu hatası eski davranışa düşüyor. Tam suite: **120/120 yeşil**.

Gerçek PLC'ye kendi kendine yazılmadı; kullanıcı bir sonraki denemede
sonucu bildirecek.

## 2026-09-18 - Settings "HATA — PLC onaylamadı" gerçek sebebi gizliyordu

Kullanıcı gerçek PLC'de X Kesim Hızı ve X Kesim Bitiş için Uygula'ya bastı,
her ikisi de 2s sonra "HATA — PLC onaylamadı" verdi - gerçek sebep hiçbir
yerde görünmüyordu (aynı sınıf sorun Vision paket yazımı için zaten
düzeltilmişti, Settings parametre yazımı yolu için ATLANMIŞTI).

### Düzeltme
- `services/machine_service.py`: yeni `parameterWriteError(key, reason)`
  sinyali. `_on_error`, worker'ın `"Write failed for '<tag>': <sebep>"`
  mesajını regex ile ayrıştırır; `<tag>` o an `_param_pending` içindeyse
  gerçek OPC UA sebebini bu sinyalle taşır (örn. BadUserAccessDenied,
  BadOutOfRange).
- `ui/machine/settings_page.py`: `_on_write_error` bu gerçek sebebi
  `_param_last_error` içinde tutar; 2s timeout sonrası `_on_write_failed`
  bunu görürse status "HATA — PLC yazmayı reddetti" + tooltip + bir
  `QMessageBox.warning` ile GERÇEK OPC UA hatasını gösterir. Gerçek bir
  hata görülmediyse (yazma OPC UA seviyesinde başarılı ama PLC değeri geri
  değiştiriyor olabilir) eski jenerik mesaj + açıklayıcı tooltip kalır -
  iki durum artık ayırt edilebiliyor.
- `tests/test_parameter_write_confirmation.py`'ye 3 yeni test: pending
  yazmayla eşleşen hata doğru sinyale dönüşüyor, eşleşmeyen tag/mesaj yok
  sayılıyor. Tam suite: 117/117.

Not: Bu düzeltme "neden" sorusuna GERÇEK bir OPC UA reddi varsa cevap verir.
Kullanıcı tekrar denediğinde gerçek mesaj gelirse kök nedeni netleştirir;
hiçbir OPC UA hatası görülmüyorsa (yazma kabul edilip PLC mantığı değeri
geri değiştiriyor olabilir) bu, PLC tarafında ayrıca araştırılmalı.

## 2026-09-17 - Bug: otomatik kamera heartbeat üretmiyordu (kullanıcı ekran görüntüsü)

Kullanıcı gerçek PLC'de otomatik kamerayı başlattı; ekran görüntüsünde
`xVisionHeartbeatOK: False` kalıcı görünüyordu ve PLC'nin `MachineReady`
formülü (`... AND GVL.xVisionHeartbeatOK ...`) bu yüzden hiç sağlanamıyordu.

### Kök neden
İki ayrı mekanizma yanlışlıkla birbirinden bağımsız kalmıştı: manuel
"Heartbeat Otomatik Üret" kutusu `auto_camera_active` iken UI'da devre dışı
bırakılıyordu (doğru - tek arbiter kuralı), AMA `VisionSimulatorService.
start_auto_camera()` heartbeat'i **hiçbir zaman kendisi başlatmıyordu**.
Sonuç: otomatik kamera modunda heartbeat üretimi tamamen duruyordu, kutu da
kilitli olduğu için kullanıcı bunu manuel de açamıyordu.

### Düzeltme (`services/vision_simulator.py`)
- `start_auto_camera()` artık `self.set_heartbeat_enabled(True)` çağırıyor -
  heartbeat, otomatik kameranın kendisi tarafından başlatılıyor.
- `_stop_auto_camera_internal()` (stop/disarm/force_disarm'ın hepsinin ortak
  yolu) artık `_heartbeat_timer.stop()` da yapıyor - tutarlı kapanış.
- `ui/machine/vision_simulator_page.py`: heartbeat kutusu artık otomatik
  kamera aktifken gerçek `heartbeat_active` durumunu senkron gösteriyor
  (salt-gösterge); etiket ve açıklama metni güncellendi.

### Test
- `tests/test_auto_camera.py`'ye 3 yeni test: `start_auto_camera` heartbeat'i
  gerçekten başlatıyor (manuel tick ile write doğrulandı), `stop_auto_camera`
  ve `disarm` heartbeat'i durduruyor.
- Bu testlerin `isActive()` doğru çalışması için modül başına bir
  `QApplication` eklendi - QTimer.isActive() bir QCoreApplication olmadan
  hep False dönüyor (deneyerek doğrulandı), bu mevcut testleri etkilemedi.
- Ekstra: gerçek dönen bir Qt event loop ile (900ms `app.exec()`) elle
  doğrulama - heartbeat değeri 0'dan 2'ye çıktı, mock değil gerçek zamanlayıcı
  ateşlemesiyle. Tam suite: **114/114 yeşil**.

## 2026-09-17 - Tam otomatik masa testi kamera emülatörü (PLC-HMI-20260917-03)

Görev: `.ai/HMI_AUTO_CAMERA_BENCH_TEST_TASK.md`. Kullanıcı: motorlar
mekanikten ayrı, sensörler masada mıknatısla tetikleniyor, manuel paket/
CutPermit/ZDownRequest tıklamak istemiyor - ARM edip "otomatik kamerayı
başlat" dedikten sonra PLC state + actual X'e göre her şeyin kendiliğinden
üretilmesini istiyor.

### Faz A (tekrar teyit)
Önceki turda yapılan UInt32 tip düzeltmesi bu görevin de ilk şartıydı;
değişiklik yok, sadece doğrulandı.

### Faz B/C - `services/vision_simulator.py::start_auto_camera/
_on_auto_camera_tick`
- `start_auto_camera()`: VisionReady=True/VisionFault=False/LineValid=True
  oturum başında BİR KEZ yazılır (her tick'te değil - gereksiz pulse yok).
- Her ~100ms tick'te (yapılandırılabilir, `AUTO_CAMERA_MIN/MAX_PERIOD_MS`
  arası, sadece durmuşken değiştirilebilir): PLC `cycle_state` okunur,
  CutPermit `_CUT_PERMIT_STATES` (WAIT_VISION..CUTTING) kümesine göre,
  ZDownRequest WAIT_BLADE_REQUEST'te `xTrajectoryValid AND NOT
  xTrajectoryFault` koşuluyla TRUE'ya döner, BLADE_DOWN/CUTTING'de sticky
  (flicker'sız) TRUE kalır - hepsi yalnız DEĞİŞTİĞİNDE yazılır.
- Paket (TargetX/TargetY/Ready/LineValid/Fault→Sequence) yalnız
  `_PACKET_STATES` (WAIT_VISION..CUTTING) içinde ve (state değiştiyse VEYA
  actual X ≥0.5mm ilerlediyse) üretilir - dönüş/idle state'lerinde
  ("kesim dışı") yeni ileri hedef paketi üretilmez (görev notu).
- TargetY_mm = canlı `lr_y_center_position` parametresi. TargetX = actual X +
  ileri bakış mesafesi (`lr_x_cut_velocity * paket_periyodu * 5`, alt sınır
  5mm) - BİLEREK `lrX_CutEndPos`'a kırpılmıyor: TargetX bir trajectory
  referansıdır, gerçek X motion hedefi `lrX_CutEndPos`'tur ve bu paketten
  etkilenmez (görev notunun açıkça izin verdiği/istediği davranış).
- Stale/disconnected snapshot'tan hiçbir şey üretilmez (booleans dahil).
- Manuel paket/CutPermit/ZDownRequest/Heartbeat kontrolleri otomatik kamera
  aktifken UI'da devre dışı ("tek arbiter" - aynı tag'e zıt yazı gitmesin).

### Faz D - yaşam döngüsü sıkılaştırması
- **Gerçek iptal** (önceden sadece "sonucu yok say" idi):
  `OpcUaWorker.cancel_pending_sequence()` bekleyen `request_write_sequence`
  coroutine'ini fiilen `Future.cancel()` ile keser - kalan alanlar (özellikle
  sequence) artık PLC'ye hiç yazılmaz. `MachineService.
  request_vision_cancel_pending()` üzerinden `VisionSimulatorService.disarm()`
  ve `_force_disarm()` içinde çağrılıyor.
- `disarm()`/`_force_disarm()` artık otomatik kamerayı da durduruyor
  (`_stop_auto_camera_internal`), `autoCameraChanged` sinyaliyle UI senkron
  tutuluyor (kullanıcı tıklamadan da kapanabilir - disarm/reconnect).
- disarm() uyarı metni güncellendi: PLC'nin 1635 exportunda heartbeat
  bypass'ı kaldırıldığı için (orijinal hesaba dönüldü) heartbeat'i durdurmak
  artık GERÇEK bir STOPPING/dönüş hareketi riski - "bool cleanup atlamak
  güvenli kapanış değildir" açıkça belirtiliyor.
- `can_arm()`: "Y actual velocity tagı yok" notu YANLIŞTI (PLC teyidi) -
  `GVL.lrY_ActualVelocity` zaten mevcut, `core/models.py::y_actual_vel` +
  config `y_actual_vel` node'u eklendi, "eksenler durmuş" kontrolü artık
  HER İKİ eksene bakıyor.

### Faz E - test
- `tests/test_auto_camera.py` (20 test): Faz C tablosunun her satırı,
  happy-path booleanların bir kez yazılması, CUTTING'de actual X'e göre
  gerçek paket/sequence artışı, BLADE_DOWN sticky/flicker'sız ZDownRequest,
  stale'den üretim yapılmaması, disarm/reconnect'in auto camera'yı
  durdurması, periyodun aktifken değiştirilememesi, lead mesafesi hesabı.
- `tests/test_opcua_cancel_pending.py` (3 test): gerçek iptal - kalan alan
  hiç yazılmıyor, iptal edilen işlem sonuç sinyali göndermiyor, tamamlanmış
  bir yazı iptalden etkilenmiyor.
- Tam suite: **111/111 yeşil**. Ayrıca demo modda tam widget-seviyesi smoke
  script ile doğrulandı (ARM→auto camera başlat→state dizisi→manuel
  kontroller pasif→durdur→kapat→disarm), sıfır beklenmeyen uyarı popup'ı.
- Gerçek PLC'ye kendi kendine bağlanılmadı/yazılmadı (görev notu).

## 2026-09-17 - Gerçek PLC bug: udiVisionSequence/Heartbeat UDINT tip uyumsuzluğu

Kullanıcı gerçek PLC testinde: TargetX/TargetY yazılıyor ama
`udiVisionSequence`/`Heartbeat` 0 kalıyor, "Yazma başarısız: vision_sequence"
hatası (neden görünmüyor). Kullanıcının kendi teşhisi doğru: bu iki tag
PLC'de UDINT, asyncua Python `int`'i varsayılan olarak `Int64` VariantType
ile gönderiyor, PLC `BadTypeMismatch` ile reddediyor.

### Düzeltme (`plc/opcua_client.py`)

- `EXPLICIT_VARIANT_TYPES = {"vision_sequence": UInt32, "vision_heartbeat":
  UInt32}` - yalnız bu iki doğrulanmış tag için `ua.Variant(int(value),
  ua.VariantType.UInt32)` ile açık tipli yazım; her şey (BOOL/Double
  yazımları, `cmd_start` gibi mevcut HMI komutları, Settings parametreleri)
  eskisi gibi örtük (inferred) tiple gidiyor - dokunulmadı.
- `_write_checked` artık `tuple[bool, str]` döndürüyor (gerçek OPC UA hata
  metnini de taşıyor); `_write_sequence` bunu `sequentialWriteResult`
  mesajına ekliyor: `"Yazma başarısız: vision_sequence (<gerçek sebep>)"` -
  artık hangi tag değil, NEDEN başarısız olduğu da görünür.
- `tests/test_opcua_sequential_write.py`: mock `_write_checked` artık
  `(bool, str)` döndürüyor (imza değişikliği nedeniyle güncellendi).
- `tests/test_opcua_variant_types.py` (yeni, 6 test): vision_sequence/
  vision_heartbeat açık UInt32 `ua.Variant` ile yazılıyor; vision_target_x/
  vision_ready/cmd_start/lr_x_cut_velocity DEĞİŞMEDEN (plain value, Variant
  sarmalanmadan) gidiyor; gerçek OPC UA hata metni (`UaStatusCodeError`
  içeriği) çağırana döndürülüyor; sıralı yazma hata mesajı gerçek sebebi
  içeriyor. Tam suite 88/88 yeşil. Gerçek PLC'ye kendiliğinden yazılmadı.

## 2026-09-17 - Düzeltme: cycle_active kilidi ARMED Vision simülatörünü kapatıyordu

Kullanıcı geçici Vision simülatörünü ilk denemesinde: "otomatik çevrimi
başlattığımda kameradan veri almam gerekiyor... şu an oto moda geçtiğim an
kapanıyor" diye bildirdi. Amaç: motorlar fiziksel olarak boşta, gerçek kamera
entegre değil - operatör ARM edip Start'a bastığında simülatörün TAM OLARAK
o andan (cycle_active=TRUE) itibaren veri beslemeye devam etmesi bekleniyor
(gerçek kamera entegre olunca bu araç tamamen silinecek, geçici test amaçlı).

### Kök neden

`SettingsPage._on_snapshot`'taki 2026-09-16 tarihli "cycle_active iken
Mühendislik erişimi zorla kilitlenir" güvenlik kuralı, `_close_vision_
simulator()` çağrısını da içeriyordu - yani zaten ARMED olan, aktif paket
gönderen bir Vision simülatör penceresini, tam olarak operatörün Start'a
bastığı an (cycle_active TRUE olduğu an) otomatik olarak kapatıp disarm
ediyordu. Bu, mekanik PARAMETRE düzenlemesi için doğru bir kural ama Vision
simülatörünün asıl kullanım amacıyla (arm ET, sonra cycle boyunca besle)
doğrudan çelişiyordu - iki farklı endişe yanlışlıkla aynı tetikleyiciye
bağlanmıştı.

### Düzeltme

`ui/machine/settings_page.py::_on_snapshot`: cycle_active kilidi artık
yalnız parametre satırlarını/endpoint alanını kilitler ve YENİ bir Vision
simülatör penceresi açılmasını engeller (`_vision_sim_btn.setEnabled(False)`).
Zaten açık/ARMED olan pencereye artık dokunmuyor - `_close_vision_
simulator()` çağrısı buradan kaldırıldı. Uyarı mesajına, pencere açıksa
"beslemeye devam edebilirsiniz" notu eklendi. `VisionSimulatorService`'in
kendi disarm/reconnect mantığı (bağlantı kaybında zorla disarm, kullanıcının
DISARM butonu veya pencereyi kapatması) değişmedi - hâlâ tek gerçek kapanış
yolları bunlar.

Not: Ayarlar sayfasındaki "Mühendislik Erişimini Aç" kutusunun kullanıcı
tarafından MANUEL olarak kapatılması (`_on_unlock_toggled(False)`) hâlâ
Vision simülatörünü kapatıyor - bu kasıtlı bir erişim iptali, otomatik bir
yan etki değil, o davranış korunuyor.

### Doğrulama

Elle yazılan bir smoke script ile (QMessageBox.warning mock'lanarak):
ARM edildi -> `cycle_active=True` simüle edildi -> pencere `isVisible()`
True, `sim.armed` True, buton disabled, tek bir uyarı popup'ı gösterildi,
ve mid-cycle `send_packet` başarıyla dispatch edildi. `pytest` 79/79
(mevcut testler bu senaryoyu zaten kapsamıyordu - Settings<->VisionSim UI
entegrasyonu, servis seviyesi testlerin kapsamı dışında).

## 2026-09-17 - Geçici mühendislik Vision veri simülatörü (PLC-HMI-20260917-02)

Görev: `.ai/HMI_TEMP_VISION_SIMULATOR_TASK.md`, Faz 0-5, kullanıcı talebiyle
uçtan uca uygulandı. Koordinasyon notu: `.ai/Codex_Codesys.md`.

### Kapsam ve amaç

Gerçek kamera uygulaması gelene kadar, mühendisin gerçek Vision->PLC
alanlarını elle tetiklediği GEÇİCİ bir diagnostic/simülatör aracı. Ana HMI
dinamiklerini (Start/Stop/Reset/Jog/Settings/Alarm/DemoSimulator) değiştirmez;
`DemoSimulator` ile karıştırılmaz (o PLC yokken TÜM snapshot'ın sahte
kaynağıdır, bu servis armed iken sadece Vision alanlarını gerçek PLC'ye
yazar). Varsayılan KAPALI ve kaldırılabilir.

### Faz 0 - inceleme bulguları

- `config/opcua.json` / `opcua.example.json`'da `vision_target_x/y`,
  `vision_confidence` zaten `MachineService._on_raw_snapshot` tarafından
  okunuyordu ama NodeId eşlemesi hiç eklenmemişti (her zaman 0.0 kalıyordu) -
  bu görevle birlikte eklendi.
- `CutPermit`, `ZDownRequest`, `Heartbeat`, `udiVisionSequence`, `xTrajectoryValid`,
  `lrMaxAllowedSlope` HMI tarafında hiç yoktu. Tüm tag adları tahmin edilmedi;
  kullanıcının yerel PLC koordinasyon paketindeki (`C:/Users/agedik/Documents/
  ChatGPT/Bufera Tekstil PLC/.../plc_reference/GVL_LAST_SHARED_REFERENCE.st`
  ve `docs/05_VISION_PLC_CONTRACT_SUMMARY.md`) GVL kaynağıyla teyit edildi.
- Vision paket sırası (TargetX/TargetY önce, sequence en son) ve
  "hedefX-actualX>0.001 + eğim limiti" trajectory kuralı aynı pakette
  `docs/reports/2026-09-17_06_PARTIAL_AUTO_TEST.md`'den doğrulandı.
- Communication_Control'da `xVisionHeartbeatOK` kaynağında GEÇİCİ olarak
  TRUE'ya sabitlenmiş durumda (kullanıcı saha testi için); bu HMI'nin değil
  PLC'nin bilinen, ayrı bir geçici durumu - HMI dokunmadı, sadece not edildi.

### Faz 1-4 - mimari

- `plc/models.py`: `OpcUaConfig.vision_simulator_enabled: bool = False`
  (config'de yoksa varsayılan False - "normal dağıtımda kapalı" gereksinimi
  ayrı kod değişikliği gerektirmeden sağlanıyor).
- `config/opcua.json` + `.example.json`: 9 yeni NodeId (`trajectory_valid`,
  `lr_max_allowed_slope`, `vision_target_x/y`, `vision_confidence`,
  `vision_cut_permit`, `vision_z_down_request`, `vision_heartbeat`,
  `vision_sequence`) + `vision_simulator_enabled: false`. Gerçek endpoint
  değiştirilmedi.
- `services/machine_service.py`: `VISION_SIM_WRITABLE_TAGS` kapalı izin
  listesi (yalnız gerçek Vision->PLC alanları - PLC-hesaplı state/sensör/
  motion/valf tagları asla değil) + `request_vision_write`/
  `request_vision_sequential_write` gateway metodları (izin listesi dışı tag
  için `ValueError`). `visionSequentialWriteResult` sinyali worker'a bağlandı.
- `plc/opcua_client.py`: `request_write_sequence` - tek bir coroutine
  içinde her alanı SIRAYLA `await` ederek yazar (back-to-back
  fire-and-forget `request_write()` çağrılarının OPC UA seviyesinde sıralama
  garantisi OLMADIĞI için - görev notu); ilk başarısızlıkta durur, kalan
  alanları (özellikle sequence'i) yazmaz.
- `services/vision_simulator.py` (yeni): `VisionSimulatorService`. Sahiplik
  modeli: `armed=False, source="REAL"` varsayılan/her bağlantı değişiminde
  zorunlu (`_force_disarm`, temizlik yazısı denemez); `arm()` yalnız
  `cycle_active=False` ve X ekseni durmuşken izin verir (Y actual velocity
  tagı yok - bilinen sınırlama, raporlandı); `disarm()` çevrim pasifken
  VisionReady/LineValid/VisionFault/CutPermit/ZDownRequest'i FALSE'a geri
  çeker, çevrim aktifken bu yazıları ATLAR ve kullanıcıyı uyarır (hareket
  ortasında izin çekmek STOPPING/dönüş hareketi doğurabilir). `generation`
  sayacı eski/gecikmiş paket sonuçlarını sessizce yok sayar. `send_packet`
  NaN/Inf ve confidence 0..1 doğrular, hedefX-actualX>0.001 kontrolü yapar,
  aynı anda tek paket (in-flight guard). Heartbeat periyodu
  `t_vision_heartbeat_timeout/3`'ten türetilir, sabit 2s değil.
- `ui/machine/vision_simulator_page.py` (yeni): `VisionSimulatorDialog`,
  modeless (`show()`, `exec()` değil) - kullanıcı isteği: ana ekran paralel
  kullanılabilsin. Açılışta hiçbir yazı yok; ZDownRequest ayrı onay ister.
- `ui/machine/settings_page.py`: "VISION SİMÜLATÖR ⚙" butonu yalnız
  `vision_simulator_enabled` VE Mühendislik Erişimi açıkken görünür/aktif -
  ayrı gizli menü/parola yerine mevcut yetki kapısı yeniden kullanıldı.
  Erişim kapanınca (kullanıcı kilitler veya cycle_active nedeniyle zorla
  kilitlenir) pencere kapatılır ve simülatör disarm edilir.

### Faz 5 - test ve doğrulama

- `tests/test_opcua_sequential_write.py` (4): sıralı yazma, ilk hatada
  durma, gerçek await sırası (yavaş yazı hızlıdan önce tamamlanır), loop yok.
- `tests/test_vision_simulator.py` (27): feature flag, varsayılan disarmed,
  arm reddi (cycle_active/eksen hareketli/flag kapalı), reconnect/disconnect
  zorla disarm, izin listesi dışı tag reddi, paket alan sırası, NaN/Inf/
  confidence sınır reddi, çift paket serileştirme, stale generation göz ardı,
  UInt32 wrap (sequence + heartbeat), heartbeat periyot hesap, disarm
  cycle-pasif/aktif davranışı, demo mod. Tümü sahte/mock worker ile - gerçek
  PLC'ye yazma yok.
- Tam suite: 79/79 yeşil (46 eski + 33 yeni).
- `python -m app.main` (gerçek config, endpoint dolu) 6s smoke-run: sadece
  read-only bağlantı/okuma döngüsü çalıştı, hata yok (flag false olduğu için
  buton hiç görünmedi).
- Demo modda widget seviyesinde el ile doğrulama (ayrı script): kilitliyken
  buton gizli/disabled, unlock ile aktif, popup açılıyor, arm+paket
  gönderimi başarılı, tekrar kilitlenince popup kapanıp simülatör disarm
  oluyor - hepsi beklenen davranış.

### Kapsam dışı bırakılanlar (bilinçli, görev notunda da işaretli)

- Periyodik "düz çizgi" otomatik paket üretimi (yalnız tek-paket modu
  yapıldı; görev notu bunu ayrı/opsiyonel bıraktı).
- Gerçek kameraya devreye alma adımının PLC tarafı (Communication_Control
  heartbeat bypass'ının geri alınması) - PLC/kullanıcı tarafı iş.
- Gerçek PLC üzerinde uçtan uca doğrulama - kullanıcı yapacak.

## 2026-09-16 - Parametre yazma "sessiz geri donme" hatasi (gercek PLC bug report)

Kullanici Faz 4'u gercek PLC'de test ederken: X Kesim Hızı'nı 175'ten
180'e degistirip Uygula'ya bastiginda deger sessizce 175'e geri donuyordu,
"✓ UYGULANDI" yaziyor olsa bile.

### Kok neden

`SettingsPage._apply_parameter`, `MachineService.set_parameter` cagirdiktan
HEMEN sonra yerel `_param_cache`'i (henuz PLC'ye hic ulasmamis olabilecek
degeri) okuyup "✓ UYGULANDI" gosteriyordu - kodun kendi yorumu bile bunun
"best-effort, gercek PLC'ye karsi guvenilir degil" oldugunu itiraf ediyordu.
Bagimsiz calisan 100ms okuma dongusu, yazma henuz PLC'ye ulasmadan once
gelen bir okumayi "gercek deger buymus" sanip `_param_cache`'i sessizce eski
degere donduruyordu - ve status etiketi hicbir zaman guncellenmiyordu, o
yuzden "basarili" yazisi ekranda asili kaliyordu.

### Duzeltme

- **`services/machine_service.py`**: yeni `_param_pending: dict[str,
  (value, written_at)]`. `set_parameter` artik yazdigi degeri PLC'den bir
  okumada gormeden "onaylanmis" saymiyor. `_on_raw_snapshot`'ta her
  parametre okunuşunda: pending deger varsa VE okunan deger yazilanla
  eslesirse -> `parameterWriteConfirmed` sinyali + cache guncellenir;
  eslesmiyor ama `PARAM_WRITE_CONFIRM_TIMEOUT_S` (2s) henuz gecmediyse ->
  hicbir sey yapilmaz (cache optimistik degerde kalir, UI titremez);
  timeout gectiyse -> `parameterWriteFailed` sinyali + cache PLC'nin
  gercek degerine dondurulur (artik dogru sebeple).
- **`ui/machine/settings_page.py`**: Uygula artik aninda "✓ UYGULANDI"
  yazmiyor, "Yazılıyor…" gosterip yeni `parameterWriteConfirmed`/
  `parameterWriteFailed` sinyallerini bekliyor. Basarisizlikta
  "HATA — PLC onaylamadı" gosteriliyor (ve spin zaten canli-senkron
  mekanizmasiyla PLC'nin gercek degerine geri donuyor).
- Build/Test: `pytest` **37/37** yesil - 5 yeni test
  (`tests/test_parameter_write_confirmation.py`): onay-oncesi, gec-gelen-
  stale-okuma sirasinda geri donmeme, gercek onay, timeout-sonrasi HATA,
  demo modda aninda onay.
- **Gercek PLC'de tekrar test kullanicida** - bu sefer "Yazılıyor…"dan
  sonra ✓ UYGULANDI mi yoksa HATA — PLC onaylamadı mi cikacagi, yazmanin
  PLC tarafinda gercekten kabul edilip edilmedigini dogru sekilde
  gosterecek (onceki turdaki gibi yanlis "basarili" mesaji degil).

## 2026-09-16 - Faz 2 gercek PLC'de dogrulandi + Faz 4: Ayarlar ekrani gercek parametrelerle

Kullanici Faz 2'yi gercek PLC'de test etti: "ayarlar haric her sey tamam
gibi". Ardindan Ayarlar ekranini gercek GVL parametreleriyle eslestirme
istendi (16 parametre, kullanicinin PLC GVL + Logic_Control kontrolunden
gelen kesin liste).

### Mimari analiz (once yapildi, sonra uygulandi)

`ui/machine/settings_page.py` zaten tamamen data-driven: hicbir parametre
UI'da hardcode degil, `core/parameters.py::PARAMETER_SPECS` listesinden
QGridLayout satiri olarak uretiliyor. Yani parametre listesini degistirmek
layout kodunu degistirmeyi gerektirmiyor. **Kok sorun**: `SettingsPage`
`service.snapshotUpdated`'a hic abone degildi, degerleri yalnizca
`_build_ui()`'da BIR KEZ (yerel SQLite/`SettingsStore` veya `spec.default`'tan)
okuyordu - gercek PLC'den asla, ve sonradan PLC verisi gelse bile ekran hic
guncellenmiyordu. Kullanicinin "UI default gostermeyecek" sikayeti buydu.

### Degisiklikler

- **`core/parameters.py`**: 16 parametre tamamen yeniden yazildi (asagidaki
  harita). Eski 16 kurgusal `par_*` kaldirildi. `X İvme`+`X Yavaşlama` tek
  `X Kesim Acc/Dec` oldu; `Vision Zaman Aşımı` kaldirildi (GVL'de yok);
  `Y Max Hız` -> `Y Follow Maks. Hızı` yeniden adlandirildi; `X Dönüş
  Acc/Dec`, `Y Pozisyonlama Hızı`, `Y Pozisyonlama Acc/Dec` eklendi.
  Pnomatik gecikmeler (4 adet) listeden tamamen cikarildi - GVL'de hala yok
  (Logic_Control T#500ms hard-coded), kullanicinin yeni listesinde de yoktu.
  `lrMaxAllowedSlope`/`lrStopAccDec`/`lrPositionTolerance`/
  `lrStopVelocityTolerance` bilincli olarak eklenmedi (kullanici istegi).
- **`config/opcua.json` + `opcua.example.json`**: 16 yeni `lr*`/`t*` tag,
  eski 16 `par_*` kaldirildi.
- **`services/machine_service.py`**: yeni `_param_confirmed: set[str]` -
  demo modda hepsi bastan onayli, gercek modda yalnizca `_on_raw_snapshot`'ta
  bir parametre fiilen `raw` icinde gorulunce onaylanir. Yeni
  `is_parameter_confirmed(key)`. Progress hesabindaki anahtar
  `par_x_cut_start_pos` -> `lr_x_cut_start_pos` (isim tutarliligi).
- **`ui/machine/settings_page.py`**: `snapshotUpdated`'a abone oldu. Her
  satir onaylanana kadar "Okunuyor…" gosterip kilitli kaliyor (Muhendislik
  acik olsa bile); onaylandiktan sonra her tick'te PLC'den canli senkron
  oluyor (`spin.hasFocus()` iken dokunmuyor - kullaniciyla yarismiyor).
- Build/Test: `py_compile` temiz, `pytest` **32/32** yesil (6 yeni test:
  parametre listesi tam/eksiksiz kontrolu x4, confirmed-tracking x2). Ayrica
  `services/demo_simulator.py` icindeki tum eski `par_*` anahtar
  referanslari (`_apply_manual_controls`, `CUTTING`, `RETURN_AXES`,
  `_return_axes`) yeni isimlere tasindi - degistirilmeseydi demo cevrimi
  `KeyError` ile cokerdi (testler bunu yakaladi).
- **Gercek PLC read/write testi kullanicida** (AI'nin PLC agina erisimi yok).

## 2026-09-16 - Faz 1 duzeltmeleri + Faz 2: yazma tarafi gercek PLC'ye baglandi

Kullanici gercek PLC'ye bagli (`opc.tcp://192.168.0.2:4840`, UaExpert ile
dogrulanmis). Bu oturumda uc ayri asama var: (1) Faz 1'e 5 duzeltme, (2)
canli config dosyasindaki iki ayri kopyalama-eksikligi hatasi, (3) Faz 2
(write binding).

### Faz 1 duzeltmeleri (kullanici onayi ile)

- **`xStartPermitted` artik dogrudan PLC'den okunuyor**, HMI kendi
  formulunu (MachineReady AND NOT xManualMode AND NOT xCycleActive AND
  xX_AtStart AND xY_AtCenter) tekrarlamiyor. `x_at_start`/`y_at_center`
  diagnostic olarak eklendi (`core/models.py`, `services/machine_service.py`).
- **`xCycleActive` da dogrudan okunuyor**, eMachineState'ten turetilmiyor.
- **`services/demo_simulator.py` gercek PLC akisiyla birebir**: MANUAL
  sadece `manual_mode=True` iken gosteriliyor (auto-mod dinlenme durumu
  WAIT_FOR_MATERIAL); normal STOP artik RECOVERY'den GECMIYOR (STOPPING ->
  BLADE_UP direkt); RECOVERY sadece FAULT+Reset sonrasi giriliyor. Eski 5
  parcali `_advance_recovery` yardimcisi tamamen kaldirildi (artik gereksiz).
- Kesim ilerlemesi formulu (ActualX-CutStart)/(CutEndX-CutStart) demo'nun
  kendi CUTTING hesabina da tasindi (tutarlilik).
- **Guvenlik**: 13 kurgusal `cmd_*` yazma tag'i `config/opcua.example.json`'dan
  kaldirildi - Faz 2 gelene kadar gercek PLC'de kullanilirlarsa sessizce
  no-op olup loglanacak sekilde.

### Canli config dosyasi hatalari (kullanicinin kendi PLC testi sirasinda bulundu)

1. Ayarlar ekranina girilen endpoint'te port eksikti (`opc.tcp://192.168.0.2`
   -> `:4840` olmadan `asyncio.create_connection` aninda OSError veriyordu,
   sonsuz reconnect donguyor). Deneyerek dogrulandi, port eklendi.
2. `config/opcua.json` (aktif/canli dosya) hicbir zaman `opcua.example.json`
   sablonundan kopyalanmamisti - sadece eski tek bir orphan tag
   (`ipc_y_pos`) vardi. PLC baglaniyordu ama okunan tek tag oydu, gerisi hep
   varsayilan degerde donuyordu ("veri gelmiyor" hissi). Sablon nodes'u
   endpoint korunarak aktif dosyaya islendi.

### Faz 2: yazma tarafi (kullanici onayi ile, gercek GVL tag'leriyle)

- **`config/opcua.json` + `config/opcua.example.json`**: `cmd_start` ->
  `GVL.Start`, `cmd_stop` -> `GVL.Stop`, `cmd_reset` -> `GVL.Reset`,
  `jog_x_plus_request`/`jog_x_minus_request`/`jog_y_plus_request`/
  `jog_y_minus_request` -> `GVL.xX/Y_Jog*Request`. `manual_mode` zaten
  vardi (`xManualMode`), hem okuma hem yazma icin ayni key kullaniliyor.
- **`plc/opcua_client.py`**: `request_pulse` artik ayni komut icin ikinci
  pulse'u SENKRON olarak (schedule etmeden once) engelliyor
  (`_pulses_in_flight` set'i). **Gercek bir hata yakalandi+duzeltildi**: ilk
  yazimda guard `_pulse()` coroutine'i icinde (async) isaretleniyordu, iki
  `request_pulse()` cagrisi arka arkaya (await olmadan) geldiginde ikinci
  cagri ilkinin daha baslamadigini goruyor, guard calismiyordu. Test
  (`tests/test_opcua_pulse_guard.py`) bunu yakaladi.
- **`services/machine_service.py`**: `request_start/stop` degismedi (zaten
  dogru pulse deseni), sadece config'teki NodeId'ler gercek oldu.
  `set_auto_mode` kaldirilip yerine `set_manual_mode(manual: bool)` geldi -
  duz yazma (pulse degil), `xManualMode`'a. Jog metodlari yeni
  `jog_x_plus_request` vb. tag'lere yaziyor. Yeni `release_all_jog()`:
  `_manual_allowed()` kontrolune tabi DEGIL (birakma/guvenlik her zaman
  calismali), 4 jog request tag'ini FALSE'a cekiyor.
- **`ui/machine/manual_page.py`**: basliga "MANUEL MODU ETKİNLEŞTİR"
  checkable butonu eklendi (`xManualMode`'a yazar, PLC onayini
  `_on_snapshot`'ta `blockSignals` ile senkron gosterir - optimistic degil).
  `hideEvent` (sayfadan cikis) ve `QApplication.applicationStateChanged`
  (pencere odak kaybi) her ikisi de `release_all_jog()` cagiriyor.
- **Dokunulmayanlar (kasitli)**: `y_center`/`set_blade`/`set_clamp` hala eski
  kurgusal taglara yaziyor (config'te yok, no-op) - Faz 3'un isi. Ayarlar,
  Vision Simulator'a hic dokunulmadi.
- Build/Test: `py_compile` temiz, `pytest` **26/26** yesil (6 yeni test:
  pulse-guard x3, set_manual_mode/release_all_jog demo davranisi x2,
  OpcUaConfig izolasyon testi x1). **Gercek PLC'ye karsi buton testi
  (Start/Stop/Reset pulse, Jog press/release, Manual/Auto write, write
  failure) AI'nin erisemedigi kullanicinin PLC agi uzerinde yapilmali.**

## 2026-09-16 - Faz 1: Ana Ekran PLC->HMI read binding (onayli)

Kaynak: `docs/BUFERA_HMI_PLC_ENTEGRASYON_GOREV_PLANI.md` + kullanicinin
2026-09-16 tarihli duzeltmeleriyle onaylanan tag/formul/enum spesifikasyonu.
Sadece okuma yonu; START/STOP/RESET/JOG/manuel yazma islemlerine dokunulmadi.

- **`core/cycle_state.py`** (tam yeniden yazim): `CycleState` enum'u artik
  gercek PLC `eMachineState` degerleri (INIT=0, MANUAL=10, ...,
  CYCLE_COMPLETE=120, STOPPING=500, RECOVERY=510, FAULT=900). Eski enum
  numaralari (IDLE=10, CLAMP_DOWN=50, BLADE_UP=100 ...) gercek degerlerle
  cakisiyordu, tamamen degistirildi. `AUTO_CYCLE_ACTIVE_STATES`/
  `RECOVERY_STATES` yeni uyelere gore guncellendi.
- **`services/demo_simulator.py`**: tum `CycleState.*` referanslari yeni
  enum'a tasindi; ALIGN_Y ve WAIT_BLADE_REQUEST icin yeni kisa fazlar
  eklendi (gercek PLC'de var, eskiden demo'da yoktu); 5 parcali eski
  recovery zinciri (RECOVERY_BLADE_UP/RETURN_X/CENTER_Y/CLAMP_UP) tek
  `RECOVERY(510)` kodu altinda internal `_recovery_step` ile birlestirildi
  (gercek PLC de tek kod donuyor). Davranis/zamanlama korunuyor.
- **`core/models.py`**: kullanilmayan `estop_ok`/`safety_ok` kaldirildi
  (hicbir UI onlari okumuyordu); `cut_active`, `emergency_active`,
  `trajectory_fault`, `feed_complete` eklendi (yeni sozlesmenin tag'leri,
  henuz hicbir widget'ta gosterilmiyor - ileri faz icin hazir).
- **`services/machine_service.py::_on_raw_snapshot`**: `x_servo_ready`/
  `y_servo_ready` artik `PowerStatus AND NOT PowerError` turetmesi;
  `clamp_up`/`blade_up` artik `NOT clamp_down`/`NOT blade_down` turetmesi
  (PLC'de ayri sensor tagi yok); `auto_mode = NOT manual_mode`;
  `cycle_active = eMachineState in AUTO_CYCLE_ACTIVE_STATES`;
  `start_permitted = machine_ready AND NOT cycle_active AND NOT manual_mode`
  (plan SS4 formulu); kesim ilerlemesi artik PLC'den okunmuyor, kullanicinin
  onayladigi duzeltilmis formulle turetiliyor:
  `%clamp(100*(ActualX_mm-lrX_CutStartPos)/(CutEndX_mm-lrX_CutStartPos), 0, 100)`.
- **`ui/machine/machine_page.py`**: Vision Hazir kosulu
  `VisionReady AND xVisionHeartbeatOK AND NOT VisionFault` oldu; heartbeat
  kaybinda ayri "VISION: YANIT YOK" durumu eklendi (sadece bu bir mantik
  degisikligi, tasarima/layout'a dokunulmadi).
- **`config/opcua.example.json`**: kurgusal `HMI_*` okuma tag'leri (17 adet
  + estop_ok/safety_ok) kaldirildi; onaylanan 23 gercek tag eklendi (19
  Ana Ekran SS3 + VisionReady/VisionFault SS2 chip icin + lrX_CutStartPos/
  CutEndX_mm progress formulu icin). Yazma tarafi (`cmd_*`/`par_*`) hic
  degistirilmedi - Faz 2-4'te ele alinacak. `par_x_cut_start_pos` NodeId'i
  gercek `lrX_CutStartPos`'a duzeltildi (eskiden kurgusal `PAR_X_CutStartPos`).
- **Yeni testler**: `tests/test_machine_service_bindings.py` (6 test - servo
  ready turetmesi, clamp/blade up turetmesi, auto_mode turetmesi,
  cycle_active/start_permitted turetmesi, progress formulu + clamp);
  `tests/test_demo_simulator_cycle.py` (3 test - tam oto cevrim MANUAL'a
  geri donuyor ve tum yeni state'leri ziyaret ediyor, stop->STOPPING->
  RECOVERY->MANUAL akisi, AUTO_CYCLE_ACTIVE_STATES enum gecerliligi).
  `tests/test_tag_map.py`'deki eski `ipc_y_pos` testi `y_actual_pos`'a
  guncellendi (orphan tag kaldirildigi icin).
- **Bilinen/kalan mock noktalari**: `feed_forward_input`/`feed_reverse_input`
  (yeni sozlesmede karsiligi yok, hep False kalacak), `x_fault_code`/
  `y_fault_code` (yeni sozlesmede fault-code tagi yok), `alarm_active/code/
  count` (Faz 5'te edge-based alarm engine gelene kadar sadece demo modda
  dolu), `vision_target_x/y`/`confidence`/`slope` (Faz 6 Vision Simulator
  eklenene kadar bos), Ayarlar ekranindaki tum parametreler haricinde
  `par_x_cut_start_pos` (Faz 4'e kadar diger par_* tag'leri hala kurgusal
  isimlerle).
- Build/Test: `python -m py_compile` (5 dosya) + `pytest` 17/17 yesil
  (2026-09-16).

## 2026-09-12 (devam - UI ince ayar)

### Kullanici geri bildirimiyle bulunan 3 gorsel kusur duzeltildi

- Degisen dosyalar: `ui/machine/manual_page.py`, `ui/machine/widgets.py`,
  `ui/machine/machine_page.py`.
- Kaynak: kullanici uygulamayi kendi terminalinden calistirip ekran
  goruntusu + geri bildirim gonderdi (bu ortamdaki AI'nin kendi baslatma
  denemesi GUI penceresi acmadan takili kaldi, CPU=0 - detay `RULES.md`
  Faz 7 notlarinda; muhtemelen bu araç oturumunun goruntu baglami farkli).
- Duzeltmeler:
  1. Manuel/Servis ekraninda X ekseni karti Y ekseni kartiyla ayni satir
     sayisina sahip degildi (Y'de "MERKEZE GİT / Y=0" butonu var, X'te
     karsiligi yok -> boyle bir PLC/servis komutu da yok, uydurulmadi).
     Duzeltme: X kartina ayni yukseklikte (`MIN_TOUCH_HEIGHT`) bos bir
     spacer eklendi, ACTUAL POSITION/SERVO kutulari artik iki kolonda ayni
     hizada.
  2. Operator ekraninda ust durum cubugu (`StatusChip` + `statusBar`
     `QFrame`'i) dikey `QSizePolicy` "Fixed" degildi -> pencere/oturum
     buyuyunce kalan bosluk bu ogelere gidip devasa/orantisiz gorunuyordu.
     Duzeltme: ikisi de `QSizePolicy.Policy.Fixed` (dikey) yapildi.
  3. Operator ekraninda alt navigasyon sekmeleri (MANUEL/AYARLAR/ALARMLAR/
     KAMERA EKRANI) sayfanin ortasinda kaliyordu, altinda bosluk vardi.
     Duzeltme: `root.addStretch(1)` sekmelerden ONCE eklenerek CNC
     kontrolculerindeki gibi sekmeler ekranin en altina sabitlendi.
- Build/Test: `python -m py_compile` (3 dosya) + `pytest` 8/8 gecti.
  Gorsel dogrulama kullanicinin kendi calistirmasina birakildi.

## 2026-09-12

### AI hafiza sistemi projeye uyarlandi

- Eklenenler: `CLAUDE.md`, `.ai/` (INDEX, RULES, memory/*, skills/design/*, hooks/*)
- Kaynak: `D:\work\GitProjects\MilGor_Project\ai-starter-kit` sablonlari,
  Bufera projesinin gercek durumuyla dolduruldu (TODO birakilmadi).
- Build/Test: etkilenmedi (sadece dokumantasyon/hafiza dosyalari).

### Ilk proje iskeleti + iki gercek hata duzeltmesi

- Eklenenler: `core/`, `plc/`, `services/`, `persistence/`, `ui/machine/`,
  `app/main.py`, `tests/`, `config/opcua*.json`, `README.md`, `INTEGRATION.md`.
- Duzeltilen hatalar (gercek calistirma + ekran goruntusu ile bulundu):
  1. `manual_page.py`/`settings_page.py`/`alarm_page.py` "Ana Ekran" geri
     butonu `"main"` anahtari yayiyordu, `app/main.py` sozlugu
     `"machine_main"` bekliyordu -> KeyError, operator sayfada kilitleniyordu.
     Duzeltme: uc sayfa da `"machine_main"` yaymaya cekildi.
  2. `app/main.py::main()` icinde `service.start()`, `MainWindow` (ve onun
     sinyal aboneleri) olusturulmadan ONCE cagiriliyordu -> ilk Demo mod
     bildirimi kimse dinlemeden kayboluyordu, status bar "PLC: --" gosteriyordu.
     Duzeltme: `service.start()` cagrisi `MainWindow` olusturulup `show()`
     yapildiktan sonraya alindi.
- Build/Test: `pytest` 8/8 gecti. `python -m app.main` gercekten calistirilip
  PowerShell + UI Automation ile 4 ekranin ekran goruntusu alindi (Operator,
  Manuel, Ayarlar, Alarmlar) ve dogrulandi.
