# HMI kontrol raporu — C06_1 / 2026-09-22

Kapsam: D:/work/GitProjects/Bufera_Tekstil_Project kaynakları ve gerçek/example OPC eşlemeleri; PLC C06_1. Kaynak/doküman farkları raporlandı; HMI/PLC uygulama kodu ve gerçek config/veritabanı değiştirilmedi. Online bağlantı, OPC node erişimi ve fiziksel test yapılmadı. Görsel ekran kabulü yapılmadı.

## Sonuç
Mevcut mimari korunabilir. Dört pnömatik talep ve tek 3 saniyelik dönüş butonunun tag sözleşmesi doğru. C6 görünürlüğü ve bağlantı/kalıcılık kenar durumlarında aşağıdaki işler gerekli.

## Öncelikli düzeltmeler

### HMI-A01 — P1: Ayar yazma iznini servis seviyesinde tamamla
Kaynak: services/machine_service.py:956 set_parameter; ui/machine/settings_page.py:257 _row_enabled, :267 unlock.
Servis yalnız move_to_start_busy kontrol ediyor; cycle_active, stale, bağlantı, jog/hareket kontrolü yok. UI otomatik çevrimde erişimi kapatsa da bu servis açığını kapatmıyor; onay penceresi sırasında koşullar değişebilir. Manuel jog sırasında ayar düzenleme de ortak bir duruş kontrolüne bağlı değil.
Yeniden üretim: cycle_active=True + stale=True + DISCONNECTED iken set_parameter('lr_x_jog_velocity',20), mock worker request_write çağrısını aldı.
İş: mevcut servis içinde ortak ve basit izin kontrolü; gerçek modda taze/bağlı, otomatik çevrim ve C5 hareketi yok, jog talepleri ve eksen hareketi yok; uygun olmayan durumda cache/yerel ayar/yazma değişmeden açık ret. UI aynı sonucu kullansın. Bırakma/Stop komutları bu ayar kilidine bağlanmasın.
Kabul: çevrim, jog, C5, stale/disconnected senaryolarında yazı yok; duruşta geçerli ayar yazılır. Yeni katman veya PLC tagı zorunlu değil.

### HMI-A02 — P1: Yeniden açılışta alarm aktifliğini uzlaştır
Kaynak: services/machine_service.py:232 _active_alarm_events boş başlar; :479 alarm değerlendirme; :521 sayaç. persistence/alarms.py:139 recent yalnız son100 satır.
Eski aktif kayıt SQLite içinde dururken yeni servis yalnız kendi sözlüğündeki eventleri kapatabiliyor. HMI yeniden açıldıktan sonra PLC hata FALSE gelse eski event aktif kalıyor; TRUE gelse ikinci kayıt oluşabilir. Sayaç ve aktif listeyi son100 geçmiş kaydıyla sınırlamak da uzun süre aktif hatayı gizleyebilir.
Yeniden üretim: servisA x_power_error=True -> aktif1; aynı testDB ile servisB x_power_error=False -> aktif hâlâ1.
İş: katalog kimliği ile kalıcı kayıtların eşleşmesini koru; ilk TAZE tam okumada mevcut koşullarla uzlaştır. Bağlantı yokken hatalar temizlendi iddiası üretme. Aktif sorgusu geçmiş limitinden bağımsız olsun; geçmiş korunmalı, toplu DB silme yapılmamalı.
Kabul: yeniden açılışta hâlâTRUE tek aktif kayıt; FALSE taze okununca aktiften kalkar/geçmiş kalır; 100+ geçmiş satırı aktif hatayı gizlemez.

### HMI-A03 — P2: U10 veri tazeliği önce değerlendirilmeli
Kaynak: ui/machine/machine_page.py:126 compute_start_inhibit_reasons.
start_permitted TRUE kontrolü stale kontrolünden önce return ediyor. Eski TRUE izin ve stale=True birlikteyken uyarı listesi boş.
Yeniden üretim: MachineSnapshot(stale=True,start_permitted=True) -> [].
İş: bağlantı/tazelik önce; [U10] gösterilsin, eski izin uyarıyı bastırmasın. Buton izinleri ayrıca taze veriye bağlı kalsın.
Kabul: son izin TRUE/FALSE fark etmeksizin bağlantı kaybı U10; bağlantı tazelenince eski uyarı kalkar.

### HMI-A04 — P1 entegrasyon kapısı: C6 sekiz alan ve bilinmiyor durumu
Gerçek config/opcua.json içinde aşağıdaki sekiz alan YOK; example içinde mevcut. Bu önceki online doğrulama bekleme kararına uygun, fakat H12-H15/H20-H22/U06 canlı çalışıyor kabul edilemez.
- operator_stop_active -> GVL.xOperatorStopActive
- x_stop_error -> GVL.xX_StopError
- y_stop_error -> GVL.xY_StopError
- x_axis_error -> GVL.xX_AxisError
- y_axis_error -> GVL.xY_AxisError
- alarm_mode_changed_during_cycle -> GVL.xAlarmModeChangedDuringCycle
- alarm_clamp_lost_during_cycle -> GVL.xAlarmClampLostDuringCycle
- alarm_blade_not_clear_during_return -> GVL.xAlarmBladeNotClearDuringReturn
C06_1 exportunda sekizi de var; online namespace/erişim henüz kanıtlanmadı. Kod eksik alanları varsayılan FALSE olarak tutuyor; bu sağlıklı okuma kanıtı değildir. Eksik eşlemeler için görünür eksik/bilinmiyor açıklaması ver. Online node kontrolünden sonra gerçek config'e geçir; tahmini eklemeyle toplu okuma döngüsünü bozma. Worker toplu read_values yapıyor.
Kabul: eksik tag listesi görünür; yayınlandıktan sonra sekiz alan gerçek okumada doğrulanır; H20/H21/H22 ayrı hatalar görünür, H19 çift sayılmaz.

### HMI-A05 — P2: Mesaj sınıfını canlı tabloya bağla
core/notification_catalog.py M01-M09 referans metinlerini içeriyor. Gerçek MachineService log_event çağrıları yalnız HATA üretiyor; MachinePage tabloya yalnız ek canlı UYARI satırları ekliyor. Dolayısıyla state mesajlarının statik katalogda bulunması canlı Mesaj filtresini tamamlamıyor.
İş: mevcut tablo içinde uygun M01-M09 canlı mesajlarını göster; her poll geçmiş kaydı ekleme. 40 kamera,60 talep,30/70 sensör,90/110 çıkış,130 dönüş,140 durduruluyor,510 manuel hazırlık,500 otomatik Stop devam yolu. M08 yalnız yeni sonuç olarak gösterilsin.
Kabul: Hata/Uyarı/Mesaj filtreleri gerçek akışta anlamlı; bağlantı eskiyse kesin proses mesajı üretme.

### HMI-A06 — P2: Operatör açıklamalarının son sözleşmeyle uyumu
- core/cycle_state.py: MANUAL_RETURN_STOP140 etiketi 'Durduruldu' diyor; süreç tamamlanmadığı için 'Durduruluyor' olmalı. RECOVERY510 'Manuel hazırlık gerekli' olmalı.
- _pneumatic_common_allowed operator_stop_active kontrol etmiyor; PLC reddetse de HMI butonu açık kalabilir. C6 alanı doğrulanınca ortak izinde kullan.
- U05 yalnız blade_down kontrol ediyor; sözleşme BladeZDown OR xBladeValveCmd. Valf komutu mevcut snapshot/config'te yoksa kesin neden uydurma; salt okunur eşleme veya açık genel engel yaklaşımını mevcut sözleşmeyle tamamla.
- HMI SESSION_BRIEF, C5.1 state140 kararını hâlâ bekliyor diyor; karar ve C06_1 kaynak doğrulaması tamamlandı, saha C6 testi bekliyor. 'build/export yok' notları export doğrulandı / online test bekliyor olarak güncellenmeli.

## Doğru bulunanlar
- cmd_blade_retract -> xBladeRetractRequest; cmd_clamp_retract -> xClampRetractRequest.
- cmd_blade_down -> xBladeDownRequest; cmd_clamp_down -> xClampDownRequest. Gerçek config'te mevcut.
- cmd_move_to_start -> xMoveToStartRequest; Allowed/Busy/Done/Aborted/Error altı eşleme mevcut ve example ile aynı.
- 3 saniye hold, erken bırakma/izin kaybı/sayfa değişimi iptali; dönüş izni PLC Allowed üzerinden. Busy+Aborted ara duruş olarak ele alınıyor.
- Reset gerçek modda yalnız komut pulse; clear_active kaldırılmış.
- State numaraları PLC ile uyumlu (130/140 dahil).
- H01-H22 katalog uygulaması var; U01-U11 çoklu canlı satır desteği var.
- Pnömatik timeout ayarları HMI parametre listesinde yok. Vision heartbeat timeout ayrı konudur.
- Vision simülatörü dar izinli Vision yazma listesinden çalışıyor; sequence sıralı yazılıyor. PLC state/valf/trajectory-valid yazma yolu simülatöre açılmamış.

## Test kanıtı
HMI kaynakları bu raporun yanındaki hmi_audit_20260922 klasörüne kopyalandı; gerçek config ve data alınmadı. Endpoint boş demo config kullanıldı. Offscreen pytest: 267 passed in 9.06s. İlk koşuda eksik izole config nedeniyle 7 test başarısızdı; demo config eklenince geçti. Windows pytest geçici klasör erişimi için izole test çalıştırması yükseltilmiş izinle yapıldı.
Ek audit_repro.py, mock worker ve ayrı audit_repro.db ile A01/A02/A03 sorunlarını tekrar üretti; gerçek PLC bağlantısı başlatılmadı.
Mevcut suite'in geçmesi bu üç eksik senaryoyu kapsadığı anlamına gelmez. HMI ajanı düzeltmelerine bu regresyonları eklemeli.

## Uygulama sırası
A01 -> A02 -> A03 -> A04 eksik veri gösterimi -> A05 -> A06. A04 gerçek node aktivasyonu online erişime bağlıdır. Ardından HMI düzeltme kontrolü; sınır sensörleri ayrı karar; C7 fiziksel toplu test en son. Mimariyi büyütme, yeni PLC motion/state kararı alma.
