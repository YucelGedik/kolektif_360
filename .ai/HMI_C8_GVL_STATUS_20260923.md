# PLC-HMI-20260923-24 — C8 Home sonuc cikislarini GVL uzerinden yayinla

HMI not23 yanitinda xSetZeroRequest online dogrulandi; 10 FB ic alan BadNodeIdUnknown, Programs browse bos, GVL yayinlaniyor olarak raporlandi. Kullanici mevcut Home bloklarini calistiriyor, ekranda iki Done TRUE. PLC kodunun eksikligi degil, sonuc alanlarinin yayini eksik.

Karar: Kullanici talebiyle mevcut 10 Home cikisi normal GVL alanlarina baglanacak. Yeni kontrol mantigi, latch, timer, state veya Action yok. Sadece sonuc aynalama. Mevcut xSetZeroRequest RW degismez; XY_pulse_home PLC ic sinyali kalir. Kullanici henuz bu10alani eklemedi.

|HMI anahtari|CFC kaynak pini|Yeni RO sembol|
|---|---|---|
|x_home_done|Motion_Control.MC_Home_X.Done|GVL.xX_HomeDone|
|x_home_busy|Motion_Control.MC_Home_X.Busy|GVL.xX_HomeBusy|
|x_home_error|Motion_Control.MC_Home_X.Error|GVL.xX_HomeError|
|x_home_error_id|Motion_Control.MC_Home_X.ErrorID|GVL.eX_HomeErrorID|
|x_home_aborted|Motion_Control.MC_Home_X.CommandAborted|GVL.xX_HomeAborted|
|y_home_done|Motion_Control.MC_Home_Y.Done|GVL.xY_HomeDone|
|y_home_busy|Motion_Control.MC_Home_Y.Busy|GVL.xY_HomeBusy|
|y_home_error|Motion_Control.MC_Home_Y.Error|GVL.xY_HomeError|
|y_home_error_id|Motion_Control.MC_Home_Y.ErrorID|GVL.eY_HomeErrorID|
|y_home_aborted|Motion_Control.MC_Home_Y.CommandAborted|GVL.xY_HomeAborted|

Iki ErrorID SMC_ERROR tipinde (FB ile ayni); HMI OPC gercek sayisal tipini browse/read ile dogrulasin. BOOL cikislar BOOL. Kullanici GVL'ye ekleyip iki CFC bloğunun cikislarina dogrudan baglar; yalniz deklarasyon yetmez. Symbol Configuration'da bu10alan RO, xSetZeroRequest RW. Kullanici build/download sonrasi bildirince saltokunur sorgula; gerçek NodeId teyidinden sonra config'e ekle. Eski Motion_Control.* aday yollarini example dahil bu GVL sozlesmesiyle degistir; online dogrulanmadan gercek config'e varmis gibi ekleme. Eksik anahtar listesi/3sn/modal ve temiz eski sonuc denetimi korunur.

Iki Done TRUE goruntusu yalniz manuel PLC testindeki blok basarisini gosterir; HMI ucuca testini gecti diye isaretleme. Yeni talep oncesi xSetZeroRequest FALSE ve force olmamali; Execute/Done temizlendigi kontrol edilmeli. Otomatik TRUE/Home/force yazma yapmayin. C8E EMG ayri gorevdir.
