# PLC-HMI-20260918-06 — Alarm, manuel pnomatik ve timeout sozlesmesi

## Durum ve teslim siniri
C0.2a ST 1710_C02 exportunda dogrulandi. C0.2b Alarm_Control cift task cagrisi kaldirma testleri kullanici tarafindan 3/3 gecti; yeni export teyidi bekliyor. C0.3 kodu teslim edildi, kullanici test ediyor; timeout taglarinin online yayini ve test sonucu henuz dogrulanmadi. HMI eksik node'u FALSE/normal diye gostermemeli; kullanilamiyor demeli. Bu dosya uygulama/test tamamlandi bildirimi degildir.

## H4 — PLC alarm BOOL'lari (HMI salt okunur)
| PLC tag | Operator metni | Durum |
|---|---|---|
| GVL.xAlarmClampLostDuringCut | Kesim sirasinda baski asagi sensoru kayboldu. | C0.2 |
| GVL.xAlarmBladeLostDuringCut | Kesim sirasinda bicak asagi sensoru kayboldu. | C0.2 |
| GVL.xAlarmClampDownTimeout | Baski belirtilen surede asagi konuma ulasamadi. | C0.3 test bekliyor |
| GVL.xAlarmBladeDownTimeout | Bicak belirtilen surede asagi konuma ulasamadi. | C0.3 test bekliyor |
Tum nedenleri ayri goster; tek alarm birbirini ezmesin. FALSE->TRUE gecisini tarihceye kaydet; baglanti sonrasi ilk okumada TRUE olan alarmi da mevcut aktif alarm olarak goster. HMI alarm bitlerini temizlemez. Reset mevcut GVL.Reset BOOL pulse'u ile; kabul ve state PLC'den okunur. Bu dort alarm tum servo/Vision arizalarini kapsayan katalog degildir; diger FAULT nedenleri icin bunlardan sahte neden turetme.
Ek salt okunur BOOL: GVL.xAlarmStopRequest, GVL.xAlarmResetAccepted (tek tarama olabilir; HMI pulse'u kacirabilir), GVL.xManualPreparationRequired, GVL.xBladeRetractAccepted, GVL.xClampRetractAccepted. Reset basildi diye kabul varsayma; state ve latched readback ile izle.

## Manuel ekran — dort butonun gercek durumu
| Buton | HMI yazacagi BOOL request | Durum |
|---|---|---|
| Bicak Yukari | GVL.xBladeRetractRequest | Mevcut, pulse |
| Baski/Dayama Yukari | GVL.xClampRetractRequest | Mevcut, pulse |
| Bicak Asagi | Henuz manuel request tanimli DEGIL | Devre disi; PLC gorevi acik |
| Baski/Dayama Asagi | Henuz manuel request tanimli DEGIL | Devre disi; PLC gorevi acik |
Baski/dayama ayni mekanizma; mevcut arayuzde tutarli isim kullan.
Yukari butonlari TRUE -> yaklasik100-250ms -> FALSE; sure PLC tarafinda gorulebilmeli, OPC write basarisi kabul kaniti degil. Iki talep bagimsiz, istenen sirada veya birlikte. Islem sonrasi Accepted boollari PLC'de tutulur; HMI yazmaz. FAULT'ta sifirlanir. Request uygun olmayan anda gelirse kuyruklanmaz; uygun MANUAL'da yeniden basilir. Baglanti kaybi/reconnectte eski komutu otomatik tekrar gonderme; request dusurme/temizleme mevcut pulse servis kurallariyla yapilir, basarisiz yazma operatora bildirilir.
PLC kabul kosullari: MANUAL state ve xManualMode TRUE, xEmergencyOK TRUE, xAlarmStopRequest FALSE, xMotionStop FALSE, HMI/fiziksel Stop aktif degil, iki eksen hiz toleransi icinde durmus, dort jog request'i birakilmis. HMI yalniz xManualMode'a bakarak kabul gostermesin; PLC nihai otorite. Eksik fiziksel Stop bilgisi nedeniyle kusursuz UI izin hesabi iddia edilmesin.
GVL.xBladeValveCmd / GVL.xClampValveCmd PLC tarafindan uretilen komutlar: TRUE asagi, FALSE geri cekme. HMI bunlara dogrudan YAZMAZ. GVL.ZDownRequest Vision istegidir, manuel Bicak Asagi yerine kullanilmaz. Otomatikte Start baskiyi indirir; bu manuel Asagi request'i degildir.
Geri bildirim: GVL.BladeZDown / GVL.ClampDown. FALSE kullanicinin kabul ettigi proses acikligi; bagimsiz yukari sensoru yok. Asagi butonlarini uygulayabilmek icin PLC tarafinda ayrica request/izin/ariza semantigi tamamlanacak; tag ismi uydurulmayacak.

## Operator yonlendirmesi
FAULT: '[Alarm nedeni]. Eksenlerin durmasini bekleyin. Nedeni kontrol ettikten sonra Reset verin.'
RECOVERY510: 'Manuel modu secin.'
MANUAL + xManualPreparationRequired: 'Bicak Yukari ve Baski Yukari dugmelerine istediginiz sirada basin. Sensor acikliklarini kontrol edin; eksenleri baslangic konumlarina getirin.'
Iki Accepted FALSE ise ilgili yukari talebinin eksikligini, asagi sensoru TRUE ise sensorun hala aktif oldugunu belirt. Konumlar xX_AtStart / xY_AtCenter; su an jog ile hazirlik, ayri Baslangica Git sozlesmesi henuz yok. Iki talep + iki sensor FALSE + iki asagi komut FALSE + baslangic/merkez/servo/durus kosullari hazirligi tamamlar. Ardindan 'Perdeyi kontrol edin. Otomatik modu secerek yeni Start verin.' Otomatik Reset/hareket yok. Onceki 05 notuyla birlikte uygulanir.

## H7 — yeni ayarlar (C0.3 test bekliyor)
GVL.tClampDownTimeout : TIME := T#60s;
GVL.tBladeDownTimeout : TIME := T#60s;
GVL persistent + PersistentVars instance paths; HMI saniye gosterir. IEC TIME milisaniye degeridir:60s=60000ms; OPC sunucusunun gercek DataType'ini ve olcegini online dogrula, mevcut type-aware yazma servisini kullan. Pozitif sure; sifir/negatif reddedilir. Kullanici yetkili ayarlar ekraninda makine dururken ve hareket/cevrim yokken degistirir; readback ve hata mesaji kullanilir. PLC ek bir parametre-yazma kilidi bu pakette getirmedi; canli cevrimde yazma timer esigini degistirebilir. HMI yalniz okuma testini persistence testi diye sunmasin.
Timer yalniz ilgili DOWN state + asagi komut + sensor yok iken calisir. Yukari hareket timeout'u eklenmedi. Kesimde sensor kaybi 60s beklemez.

## Takip listesi
- [ ] H4 dort alarm mapping, metin, tarihce, eksik-node davranisi.
- [ ] Iki mevcut Yukari pulse butonu ve Accepted/sensor mesajlari.
- [ ] PLC: iki manuel Asagi talebi/izinleri ayri gorev; henuz uygulanmadi.
- [ ] H7 TIME mapping, birim/yazma/readback; C0.3 kullanici kabulunden sonra online dogrulama.
- [ ] H5 ayri Baslangica Git PLC sozlesmesi bekliyor.
- [ ] HMI uygulama raporu ve gercek PLC entegrasyon testi PLC tarafina geri bildirilecek.


## 2026-09-18 — GUNCEL KARAR: sabit PLC timeout
Onceki ayarlanabilir/persistent TIME ve H7 ayar talebi IPTAL. Alarm_Control iki TON icin PT := T#60s kullanir. Sure sadece PLC kaynak kodundan degisir; HMI timeout okumaz/yazmaz/ayar gostermez. GVL.tClampDownTimeout ve GVL.tBladeDownTimeout eklenmez; eklenmisse yalniz bu iki bildirim ve bunlara ait PersistentVars instance path kayitlari kaldirilir. Diger persistent ayarlara dokunulmaz, liste yeniden siralanmaz. Toplam mevcut20 makine ayari korunur;22 talebi iptal. Iki runtime timeout alarm BOOL'u ve HMI alarm gostergeleri KALIR. Kullanici PLC TIME persistence kabul etmedigini bildirdi; bu not TIME genisligi hakkinda genel teknik iddia degildir.
C0.3-T01: Build ve iki TON PT degeri60s; yeni persistent ayar yok. T02-T07 ayni, testler60s ile yapilir. T08: kontrollu yeniden baslatma sonrasi PT degerleri kaynak geregi60s ve runtime latch varsayilaniFALSE; persistence testi degildir. Onceki gecici HMI/GVL5s onerisi iptal.
