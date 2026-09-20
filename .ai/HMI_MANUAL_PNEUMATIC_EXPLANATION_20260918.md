# PLC-HMI-20260918-08 — Manuel pnomatik ekrani aciklamasi
Kullanici ekran goruntusu uzerinden manuel pnomatik davranisini netlestirmek istiyor. Mevcut yalniz Yukari request gonderme dogrudur; Asagi butonlarini pasif birakma onceki PLC notunun talimatidir. HMI agent hatasi olarak yorumlanmamali. Iki yonlu manuel kontrol PLC tarafinda henuz tamamlanmadi.

## Komut zinciri
Bicak Yukari: HMI GVL.xBladeRetractRequest BOOL pulse TRUE->FALSE yazar. Izinli MANUAL'da PLC kenari kabul eder, GVL.xBladeValveCmd := FALSE ve GVL.xBladeRetractAccepted := TRUE yapar. Logic sonundaki IO_Control.WriteOutputs fiziksel xDO_BladeValve := GVL.xBladeValveCmd yazar. Tek bobinde FALSE geri cekme, TRUE asagi talebidir. HMI request'i FALSE yapinca valf tekrar TRUE olmaz; PLC komutu korunur.
Baski Yukari: ayni zincir xClampRetractRequest -> xClampValveCmd FALSE + xClampRetractAccepted TRUE -> xDO_ClampValve FALSE.
HMI valf komutlarini, fiziksel cikislari veya Accepted bitlerini YAZMAZ. ZDownRequest kamera sozlesmesidir; manuel Asagi yerine kullanilmaz.

## Ekran anlamlari — sade tut
1. Talep: Yukari butonu bir istek gonderir. OPC yazma basarisi tek basina PLC kabul kaniti degildir.
2. PLC valf komutu: xBladeValveCmd/xClampValveCmd TRUE ise 'Asagi komutu', FALSE ise 'Geri cekme komutu'. Bu fiziksel bobin/valf geri bildirimi degildir.
3. Sensor: BladeZDown/ClampDown TRUE ise 'Asagi sensoru aktif'; FALSE ise 'Asagi sensoru pasif (aciklik)'. Tek basina 'SENSOR ACIK' yazisi belirsiz, degistir. Kullanici asagi sensorunden cikmayi yeterli aciklik kabul ediyor; ayri yukari sensoru yok.
4. Accepted: 'Yukari talebi alindi' hazirlik kaydidir; surekli sinyal veya mekanizmanin kalktigina dair kanit degildir. TRUE kalir, FAULT'ta sifirlanir. Onceki TRUE'yu yeni tiklamanin kabul kaniti yapma. Baglantisiz/stale durumda eski yesil bilgiyi guncel onay gibi gosterme.
Iki Yukari butonu istenen sirada/birlikte kullanilir. Manüel sayfaya girmek manuel mod secmek degildir: xManualMode ve eMachineState MANUAL readback'i esas. Mevcut kabul kosullari 06 notunda; UI engel nedenini aciklasin, PLC son otorite. Sadece 'kabul edildi' gorunup fiziksel durum anlasilmaz kalmasin. Mevcut tasarimi koru; buyuk yeniden tasarim yok.

## Acik PLC gorevi
Manuel Bicak Asagi/Baski Asagi icin request ve izin mantigi henuz YOK. PLC tarafi ayri teslimle bu iki yonlu manuel kontrolu tamamlayacak. O zamana kadar iki buton pasif; kisa aciklama 'Manuel asagi kontrolu henuz devrede degil'. Yeni tag tahmin etme, cikis komutlarini dogrudan yazma. Yeni PLC sozlesmesi gelince bu gorev guncellenecek.
Timeout ayarlari HMI'da yok (07 karari); alarm ve mesajlar korunur. Bu belge HMI uygulama tamamlandi iddiasi degildir; uygulama raporu bekleniyor.
