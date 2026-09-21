# C6.1 / PLC-HMI-20260921-16 — Hata/Uyari/Mesaj katalogu
Durum: PLC aday ST hazir; kullanici build/test/export bekleniyor. HMI gorevi verilmis, uygulanmis sayilmaz. Temel C5.1 dogrulanmis C05. Mevcut tasarimi ve alarm deposunu kullan; yeni ekran/bitmask/karmaşık sistem yok.

## Kaynakta bulunan eksikler
1. services/machine_service.py request_reset gercek modda request_pulse sonrasi _alarms.clear_active() cagiriyor. Bunu kaldir: Reset kabul edilmeden aktif hata kaybolmamali. Clear karari yalniz guncel PLC readback; history silinmez.
2. MachineSnapshot alarm_active/code/count alanlari okunuyor ama bunlar GVL'de mevcut degil. Config/gercek kaynak dogrulanmadan bu hayali alanlara dayanma. Sayac mevcut aktif HATA listesinden, genelFAULT fallback double-count olmadan hesaplansin. Demo/gercek veri yollari ayri.
3. MC_Stop Error ve fiziksel Stop anlik bilgileri HMI icin eksik. PLC'de5 RO BOOL aday: xOperatorStopActive,xX_StopError,xY_StopError,xX_AxisError,xY_AxisError. AxisError=bError veya errorstop veya interface error. Bunlar CANLI, latch degil; kisa olaylar HMI polling araliginda kacabilir. Tam PLC ilk-neden kaydi bu teslimde yok.
4. StartPermitted FAULT/RECOVERY dislamasi acik degildi; yeni paket yalniz WAIT_FOR_MATERIAL'da izin, stop/axis error yok kosulu. Kabul oncesi Alarm_Control sonrasi ve CASE sonrasi nihai readback hesaplanir. Diger state/motion/valf davranisina dokunulmadi.

## Katalog (GVL oneki tum PLC taglari icin gecerli)
| ID | Tur | Tetik/kaynak | Operator metni / islem |
|---|---|---|---|
| H01 | Hata | xAlarmClampLostDuringCut | Kesimde baski asagi sensoru kayboldu. Duruş, neden kontrolu, Reset ve manuel hazirlik. |
| H02 | Hata | xAlarmBladeLostDuringCut | Kesimde bicak asagi sensoru kayboldu. Ayni hazirlik. |
| H03 | Hata | xAlarmClampDownTimeout | Baski belirtilen surede asagi konuma ulasamadi. Sensor/hava/mekanizma kontrolu; kesin ariza parcasi uydurma. |
| H04 | Hata | xAlarmBladeDownTimeout | Bicak belirtilen surede asagi konuma ulasamadi. |
| H05 | Hata | xMoveToStartError | Baslangica donus arizasi. Reset->Manuel->ikiYukari->3sDon;14 notunun yonlendirmesi. |
| H06 | Hata | xX_PowerError | X servo etkinlestirme hatasi. |
| H07 | Hata | xY_PowerError | Y servo etkinlestirme hatasi. |
| H08 | Hata | xX_CutError | X kesim hareketi hatasi. |
| H09 | Hata | xX_ReturnError | X donus hareketi hatasi. |
| H10 | Hata | xY_MoveError | Y konumlandirma hatasi. |
| H11 | Hata | xY_FollowError | Y takip hareketi hatasi. |
| H12 | Hata | xX_StopError (yeni) | X durdurma blogu hata verdi. Tam durusu kontrol edin. C5.1 reset yolunu atlamayin. |
| H13 | Hata | xY_StopError (yeni) | Y durdurma blogu hata verdi. |
| H14 | Hata | xX_AxisError (yeni) | X eksen/surucu ariza durumu. Kodu bilinmeden nedeni tahmin etme. |
| H15 | Hata | xY_AxisError (yeni) | Y eksen/surucu ariza durumu. |
| H16 | Hata | NOT xEmergencyOK, taze veri | Emniyet geri bildirimi yok. Acil stop/emniyet zincirini kontrol edin. Mutlaka acil stop basili demek degil. |
| H17 | Hata | VisionFault | Vision uygulamasi ariza bildiriyor. FaultCode varsa ek bilgi; servo hata kodu gibi kullanma. |
| H18 | Hata | xTrajectoryFault | Yorumlanan hedef/cizgi gecersiz. IleriX, egim ve Y sinirlari kontrol edilmeli; hangisi oldugunu tahmin etme. |
| H19 | Hata | stateFAULT900 ve bilinen aktif Hata yok | PLC ariza durumunda; ayrintili neden bilgisi mevcut degil. |
| U01 | Uyari | NOT xX_AtStart, Start hazirlik baglami | X baslangic konumunda degil. Ayarli X hedefine donun. |
| U02 | Uyari | NOT xY_AtCenter, ayni baglam | Y merkez konumunda degil. |
| U03 | Uyari | xManualMode, cevrim disi | Start icin Otomatik modu secin. |
| U04 | Uyari | xManualPreparationRequired | Manuel hazirligi tamamlayin; eksik retract/sensor/konum kosullarini belirt. |
| U05 | Uyari | BladeZDown OR xBladeValveCmd, Start baglami | Start icin bicagi kaldirin. Baski Start oncesi asagi olmali diye kosul EKLEME. |
| U06 | Uyari | xOperatorStopActive (yeni) | Stop talebi aktif; Start engelli. Fiziksel/HMI kaynagi ayri bilinmiyorsa ayirma. |
| U07 | Uyari | NOT ServoReady ve belirli servo Hata yok | Servolar hazir degil. |
| U08 | Uyari | NOT xVisionHeartbeatOK | Vision heartbeat alinmiyor/guncellenmiyor. PLC baglantisi taze olmali. |
| U09 | Uyari | NOT VisionReady ve VisionFaultFALSE | Vision hazir degil. |
| U10 | Uyari | PLC baglantisi yok/stale | PLC verisi guncel degil; izin/konum bilgisi dogrulanamiyor. Eski yesili aktif gibi sunma. |
| U11 | Uyari | StartPermittedFALSE, aciklanan neden yok, cycle/Busy yok | PLC Start izni yok; ek kosul bilgisi gerekli. |
| M01 | Mesaj | state40 | Kamera verisi bekleniyor. Mevcut sequence/ready/line/permit'i goster; local sequence yakalama degeri HMI'da yok, yeni paket geldi diye tahmin etme. |
| M02 | Mesaj | state60 | Bicak talebi / gecerli yörünge bekleniyor. ZDownRequest/xTrajectoryValid salt oku. |
| M03 | Mesaj | state30/70 | Baski/bicak asagi sensoru bekleniyor. TimeoutTRUE olursa ilgili Hata. |
| M04 | Mesaj | state90/110 | Bicak/baski asagi sensorunden cikis bekleniyor. Yukari timeout yok. |
| M05 | Mesaj | state130 | Baslangic konumuna donuluyor. |
| M06 | Mesaj | state140 veya Busy+Aborted | Donus durduruluyor; talepleri birakin. StopError varsa Hata da gorunur. |
| M07 | Mesaj | state510 | Manuel modu secerek hazirlik yapin. |
| M08 | Mesaj | yeni xMoveToStartDone sonucu | Baslangic konumuna donus tamamlandi. Eski latchedDone yeni olay degil. |
| M09 | Mesaj | state500 | Otomatik cevrim durduruluyor; mevcut devam yolu bicak yukari/eksen donusu. |

Katalog ID'leri belge kimligi, PLC alarm numarasi/tag'i degildir. Canli cause ve latched cause farkini koru. Coklu nedenleri gizleme, duplicate genel nedenleri sayma. Ilk okumaTRUE aktif listede gorunmeli. Tarihce kosul gecisiyle bir kez; her poll satir ekleme. Uyarilar baglama uygun (normal kesim sirasinda X baslangicta degil spam yok). Start engelleri ilk nedenle sinirlanmaz; PLC xStartPermitted nihai otorite. HMI state/command/latch yazmaz.
VisionHeartbeat kaybinda mevcut PLC bazı aktif statelerde STOPPING otomatik donus yolunu kullaniyor; bu not davranisi FAULT'a cevirmez. Aktif cycle baglamini kacirinca kesin olay hikayesi uretme; online baglanti uyarisi ayri tutulur.

## HMI uygulama sirasi
1.Gercek reset clear_active kusurunu duzelt; aktif sayac/listede tek gercek kaynak.
2.Mevcut taglarin katalog/mappinglerini gercek opcua.json ve example'da tamamla; online node dogrulama. Yeni5 tag PLC C6.1 yayini bekler; yoksa veri bilinmiyor.
3.Coklu Start engelleri, state130/140/510 aciklamalari ve Reset/manual hazirlik metinleri.
4.Test: Reset reddedilirse hata kaybolmaz; FAULT+bilinen neden veya fallback; hata kaybolunca aktif listeden kalkar/historykalir; ayni anda X/Y/Vision nedenleri gorunur; stale veriden sahte neden yok; normal kesim X uyarisi spam yok; acikHATA sayaci ile tablo tutarli.

## Ayrica acik PLC isleri — bu paket davranisi degistirmez
- C5.1 disindaki FAULT/STOPPING Stop-error kurtarmasi genel olarak tamamlanmadi; diger statelerde Reset MC_Reset uretmeye devam ediyor. Ayri dar C6.2 duzeltme ve test gerekli.
- Otomatik cycle sirasinda xManualMode PLC tarafinda hareketi nasil etkileyecek; mevcut HMI kilidi var ama PLC state'leri bunu genel kesmiyor. HMI'ya ikinci yazar eklemek yerine ayri dar karar/teslim.
- RETURN_AXES veya ALIGN_Y boyunca pnomatik sensor kaybinin kapsamli durdurma politikasi CUTTING kaybi gibi uygulanmis degil. Mevcut C5 kontrolu yalniz manuel donus icin. Sessizce yayginlastirilmadi.
- Yukari sensor timeout'u, Vision yeni paket yaslanmasi ve fiziksel limit uç/kontak politikasi acik. Ilk-neden latch'i olmayan kisa motion/vision hatasi HMI pollingde kaybolabilir; genelFAULT fallback bunu neden biliyormus gibi gizlemez.
Bu aciklar tamamlanmadan C6'nin tamami bitti denmez. Once C6.1 gorunurluk, sonra C6.2 hareket/Reset/mod kararlari, sonra C7 regresyon/rehber.
