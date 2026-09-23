# PLC-HMI-20260922-19 — C8 / şifreli sıfır referansı belirleme

## Kapsam
Kullanıcı yeni görev istedi: Eksenler EMG basılıyken disable olur; operatör elle gerçek sıfır noktasına taşır; EMG’yi bırakır ve eksenlerin enable/servo hazır olmasını bekler; şifreli HMI penceresindeki tek butona3sbasarak bulunduğu konumu X=0/Y=0 kabul ettirir. Bu mevcut Başlangıç Konumuna Dön butonundan FARKLI işlem: biri mevcut hedefe hareket, diğeri koordinat referansını değiştirir. Mevcut mimariyi/sayfa tasarımını büyütmeyin. Yeni state veya genel home otomatiği istemiyoruz.

PLC temel export: Bufera_Perde_Kesme_20260921_1840_C06_1.export. Kullanıcı iki MC_Home kutusu ekledi; Position0, ortak pulse_home, sonuçlar bağlı değil. PLC C8 paketi son EMG/enable düzeltmesine göre hazırdır; kullanıcı henüz uygulamamıştır. Eski EMGbasılıHome taslağı geçersizdir. Bu not yayımlandı diye taglar online var kabul etmeyin.
MC_Home sürücü yöntemine bağlıdır; yalnız mevcut konumda HAREKETSİZ referans alma olarak doğrulanmış sürücü ayarıyla kullanım. Kullanıcı enabled eksenlerde hareket olmadan iki Done TRUE ve konumların 0 olduğunu doğruladı. Disabled eksende MC_Home hata veriyor; EMG basılıyken sıfırlama talebi gönderilmez. Yeni C8 paketinin cihaz testleri yine yapılmalıdır. Servo enable/bypass/home parametresi yazma eklemeyin. Kaynakta homing yöntemi0x6098 doğrulanmadı.

## HMI görünümü
Ayarlar sayfası: “Sıfır Referansı Belirle” butonu. Tıklayınca HER AÇILIŞTA şifre; yanlış/iptal hiçbir yazma yapmaz. Mevcut mühendislik/Vision şifre doğrulama mekanizmasını kullanın; şifreyi yeni dosyaya/loga/PLC tagına yazmayın, yeni varsayılan gizli şifre icat etmeyin. Normal mühendislik checkbox'ı tek başına yetki olmasın. Yetki yalnız bu pencere açıkken geçerli; kapatma/uygulama odak kaybı/bağlantı kaybı yetkiyi iptal eder; tekrar girişte şifre gerekir. Merkezi servis komut kapısı da bu yetkiyi ve taze bağlı veriyi kontrol etsin; yalnız görünürlük kontrolü yetmez.
Pencere: aşağıdaki6talimat, X/Y gerçek konum, EMG geri bildirimi, PLC EMG hazırlık kaydı (set_zero_emg_seen), servo hazır ve sıfırlama izni/durum ve TEK “Bu Konumu X=0 / Y=0 Yap — 3 saniye basılı tut” butonu. Otomatik valf kaldırma/mod değiştirme/Reset/hareket eklemeyin.
1. Çevrimi bitirin; arıza varsa normal Reset ve manuel hazırlığı tamamlayın. Manuel modu seçin.
2. Bıçak ve baskıyı kaldırın; aşağı sensörleri ve valf komutları kapalı olmalı.
3. EMG'ye basın; sürücülerin çalışma izni kapanmış olmalı.
4. X ve Y'yi elle işaretli sıfır konumuna getirin; ellerinizi çekin, eksenler dursun.
5. EMG’yi bırakın; servolar hazır olsun. Ardından butonu3sbasılı tutun. İki eksen başarı onayını bekleyin.
6. Başarı ve BusyFALSE görüldüğünde işlem tamamdır. Manuelde kalır; otomatik kullanım için operatörün yeni seçimi/Start'ı gerekir. Yarım kesim kendiliğinden devam etmez.

## PLC sözleşmesi —10 yeni runtime tag
| HMI anahtarı | GVL tag | Tip | Erişim |
|---|---|---|---|
|cmd_set_zero|xSetZeroRequest|BOOL|RW pulse|
|set_zero_emg_seen|xSetZeroEmgSeen|BOOL|RO|
|set_zero_allowed|xSetZeroAllowed|BOOL|RO|
|set_zero_busy|xSetZeroBusy|BOOL|RO|
|set_zero_done|xSetZeroDone|BOOL|RO|
|set_zero_error|xSetZeroError|BOOL|RO|
|set_zero_result|uiSetZeroResult|UINT|RO|
|set_zero_result_sequence|udiSetZeroResultSequence|UDINT|RO|
|set_zero_x_error_id|udiSetZeroXErrorID|UDINT|RO|
|set_zero_y_error_id|udiSetZeroYErrorID|UDINT|RO|

3s kesintisiz tutuş sonunda yalnız1pulse TRUE~150ms~FALSE. Erken bırakma/odak kaybı/pencere kapatma/izin kaybı/stale/bağlantı kaybı sayacı iptal eder. Yeni denemede0'dan başlar. Busy'de yeni talep gönderilmez. HMI iç motion/valf/position/MC_Home.Execute veya pulse_home yazmaz. PLC’nin Allowed biti nihai izin; HMI yeniden uzun izin formülü oluşturmasın.
Göndermeden önce result_sequence değerini yakala. Sonuç ancak kimlik değişince yeni sonuçtur; eski Done yeni işlem başarı kanıtı değildir. PLC terminal sayacı UINT32wrap ile0olabilir; büyüktür değil eşit değil kontrolü. Beklenen readback gelmezse “sonuç doğrulanamadı” göster; otomatik retry/replay yapma. Bağlantı sonrası eski talepleri yeniden yazma.
Busy süresince mod/jog/pnömatik/başlangıca dönüş/ayar yazmalarını kilitle. Stop erişimini kapatma. PLC MC_Home için enable gerektiriyor; mevcut Power_Control değişmeyecek. EMG işlemi yeniden kesebilir; Busy/Done HMI tarafından temizlenmez.

## Bildirimler
- Result1: Mesaj — “X ve Y sıfır referansı belirlendi.” Sonuçdurumu, sürekli kalibrasyon geçerlilik biti değil.
- Result2: Uyarı — “Sıfırlama isteği kabul edilmedi. Manuel mod, EMG ile hazırlık yapılması, EMG’nin bırakılması/servo hazır, sürücü duruşu, bıçak/baskı açıklığı ve bırakılmış talepleri kontrol edin.” Koşul hakkında veri yoksa neden uydurmayın.
- Result3/4: Hata — “X/Y referans belirleme bloğu hata verdi.” Gerçek ErrorID eklenir.
- Result5: Hata — “Referans belirleme komutu kesildi. İki eksenin sıfırını yeniden kontrol edin.”
- Result6: Hata — “Referans belirleme sırasında izin kayboldu. EMG ve eksen durumunu kontrol edin.”
- Result7: Hata — “10 saniyede iki eksenin sıfırlanması doğrulanamadı.”
- Busy: Mesaj — “Sıfır referansı belirleniyor; sonucu bekleyin.” Busy+Error varsa hata öncelikli, işlemin bitmediği ayrıca belirtilir.
Tek eksen sıfırlanmış olabilir; otomatik eski konuma geri dönüş yapmayın. Yeni katalog kimliklerini mevcut listeyle çakıştırmadan ekleyin; Hata/Uyarı/Mesaj tipini koruyun. Reset HMI geçmişini silmesin. xSetZeroError yalnız yeni İZİNLİ sıfırlama denemesi kabul edildiğinde temizlenir; Reset veya reddedilen talep hatayı temizlemez. Bu hata aktifken PLC Start ve C5 dönüşünü engeller; operatöre EMG hazırlığını ve sıfırlamayı yeniden tamamlamasını söyleyin. Referans hatası otomatik makineFAULT tagı gibi yorumlanmamalı.

## Yayın ve kabul
Önce example config + kod/mock test. Kullanıcının C8 export/build/online sembol doğrulaması sonrasında gerçek config; eksiktagda bilinmiyor, butonkapalı. PLC paket yolu:
C:/Users/agedik/Documents/ChatGPT/Bufera Tekstil PLC/BUFERA_TEKSTIL_MASTER_CONTEXT_PACK_2026-09-16/plc_changes/2026-09-22_C8_zero_reference
Testler: şifreyanlış/iptal, erkenbırakma, izin kaybı,3s tekpulse, Busy kilitleri, eskiDone ve yeniSequence, kısmiX/Y hata, stale/reconnect replayyok, eksiktag, enerji yenilemede referans kalıcılığını varsaymama. Fiziksel test ayrı, test sayısı ve sonuçları köprü dosyasına yazın.

## Ayrı kaynak farkı — sensör polaritesi
1840 export IO_Control: ClampDown := NOT xDI_ClampDownSensor. Kullanıcı baskı aşağıdayken ham giriş0olduğunu doğruladı. HMI GVL.ClampDown TRUE=aşağı okumaya devam eder; ikinci kez NOT yapmayın. Bıçak ham giriş aşağı1.

Önceki 18 numaralı HMI-A01..A06 için HMI ajanı uygulama ve 305/305 test sonucu bildirdi; PLC tarafı yeni kodu henüz tekrar denetlemedi. Online doğrulama açıkları ve C7 saha testi devam ediyor. C7 toplu test henüz yapılmadı.

PLC hazırlık kaydı: Mod değişimi, jog/hareket veya başka proses komutu EmgSeen kaydını iptal eder. Kabul edilen sıfırlama da kaydı tüketir. Böyle bir durumda HMI talimatı baştan EMG hazırlığına yönlendirsin; bu RO biti HMI yazamaz.
