# PLC-HMI-20260921-09 — C0.4 manuel pnomatik
Durum: PLC ST teslimi hazir, kullanici uygulama/build/test/yeni export bekleniyor. Online node varligi dogrulanmadan butonlari etkinlestirme. Mevcut tasarimi koru.
Dort BOOL pulse butonu:
- Bicak Asagi -> GVL.xBladeDownRequest (YENI)
- Bicak Yukari -> GVL.xBladeRetractRequest (mevcut)
- Baski Asagi -> GVL.xClampDownRequest (YENI)
- Baski Yukari -> GVL.xClampRetractRequest (mevcut)
100-250ms TRUE->FALSE, mevcut pulse servisiyle; click-toggle/kalici TRUE yok. Baglanti sonrasi komut otomatik tekrar edilmez. Eksik node/stale/baglanti yokken yazma yok.
PLC uygun MANUAL'da talebi kabul eder. Asagi valf komutunu TRUE, Yukari FALSE yapar; pulse bitince komut korunur. Ayni mekanizmanin iki talebi birlikteyse Yukari oncelikli. Iki mekanizma bagimsiz. Yukari talebi seviyesi TRUE iken Asagi da reddedilir. Gecersiz zamanda gelen talep kuyruklanmaz.
Ortak izin: MANUAL state + xManualMode + emergencyOK + alarmStopRequest FALSE + motionStop FALSE + Stop pasif + eksenler durmus + jog requestleri birakilmis. Asagi icin ek: manualPreparationRequired FALSE, fiziksel feed talepleri ve feed komutlari kapali. Hazirlikta Yukari kullanilabilir, Asagi pasif kalir. Fiziksel Stop/yerel hesaplar tam yayinli degil: HMI izinleri PLC yerine gecmez.
Asagi kabul edilince ilgili xBladeRetractAccepted/xClampRetractAccepted FALSE olur. Yeni asagi-kabul biti eklenmedi. Talep gonderimi fiziksel konum kaniti degil; cmd ve sensor ayri gosterilir. Tek bobin cmdTRUE asagi/cmdFALSE geri cekme. HMI valf komutu/DO/Accepted/sensor yazmaz. Vision ZDownRequest manuel kontrol yerine kullanilmaz.
Onceki06/08 Asagi henuz yok notlari bu aday sozlesmeyle guncellenir; uygulama teyidi henuz yok. HMI uygulama ve online test sonucunu geri bildir.
Timeoutlar HMI ayari DEGIL. C03 kaynaginda normal GVL TIME10s (60s literal degil) var; PLC mevcut degeri koruyor. Watchdog yalniz otomatik DOWN state'lerini izler; manuel hareket timeout'u bu pakette yok. Alarm mappingleri korunur.
Manuelden Auto'ya mod degisimi mevcut INIT uzerinden valfleri geri ceker; bu paket mod davranisini degistirmedi. Operator arayuzunde hareket geribildirimi sensor ve komutla gosterilmeli.
