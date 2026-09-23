# C8 — SADE REVİZYON / 2026-09-23

Bu sürüm önceki 2026-09-22_C8_zero_reference paketinin yerine geçer. Kullanıcı önceki paketi uygulamadığını bildirdi. Önceki Action, 10 değişken, EMG geçmişi ve tam Logic/Jog değişimi UYGULANMAYACAK.

## PLC
Mevcut Motion_Control CFC içindeki iki MC_Home bloğu korunur. Yeni POU, Action, state ve timer yok. Mevcut pulse_home BOOL, iki Execute girişine giden izinli ortak sonuç olarak kullanılabilir. HMI doğrudan bu iç değişkene yazmaz.
GVL normal VAR_GLOBAL içine tek yeni HMI talebi:
```iecst
xSetZeroRequest : BOOL := FALSE;
```

Mevcut CFC'de bir AND ile aşağıdaki ifade pulse_home'a bağlanır. Bu ST ifadesi CFC bağlantısının karşılığıdır; yeni Action açılmayacak:
```iecst
pulse_home :=
    GVL.xSetZeroRequest
    AND GVL.xManualMode
    AND (GVL.eMachineState = E_MachineState.MANUAL)
    AND GVL.xEmergencyOK
    AND GVL.ServoReady
    AND Logic_Control.xAxesStopped
    AND NOT GVL.xCycleActive
    AND NOT GVL.xMoveToStartBusy
    AND NOT GVL.xMotionStop
    AND NOT GVL.xAlarmStopRequest
    AND NOT GVL.BladeZDown
    AND NOT GVL.ClampDown
    AND NOT GVL.xBladeValveCmd
    AND NOT GVL.xClampValveCmd
    AND NOT GVL.xX_JogPlusRequest
    AND NOT GVL.xX_JogMinusRequest
    AND NOT GVL.xY_JogPlusRequest
    AND NOT GVL.xY_JogMinusRequest
    AND NOT GVL.FeedForwardPB
    AND NOT GVL.FeedReversePB
    AND NOT GVL.xFeedForwardCmd
    AND NOT GVL.xFeedReverseCmd
    AND NOT GVL.xMoveToStartRequest
    AND NOT GVL.xBladeDownRequest
    AND NOT GVL.xClampDownRequest
    AND NOT GVL.xBladeRetractRequest
    AND NOT GVL.xClampRetractRequest
    AND NOT GVL.Stop
    AND NOT xDI_StopPB
    AND NOT GVL.Reset;
```
CFC işlem sırası: AND/atama → MC_Home_X ve MC_Home_Y. Eksenler Motor_X / Motor_Y, Position=0, Execute=pulse_home. Mevcut Home örnekleri yalnız burada çağrılır. Power_Control ve task sırası değişmez.

HMI modal pencere fiziksel butonları engellemez. Bu nedenle sadece mevcut `GVL.xManualJogAllowed` ve `GVL.FeedManualAllowed` izin formüllerine aşağıdaki aynı iki koşul eklenir; tam POU değiştirilmez:
```iecst
AND NOT GVL.xSetZeroRequest
AND NOT (Motion_Control.MC_Home_X.Busy OR Motion_Control.MC_Home_Y.Busy)
```
Böylece talep veya gerçek Home işlemi sürerken fiziksel besleme ve jog engellenir. Execute iznine Home.Busy koymayın; kendi komutunu kesen döngü oluşmasın. Sıfırlama izni için xManualJogAllowed kullanmayın; talep ile bu izin kapanır.

## HMI — modal servis penceresi
Ayarlar → Sıfır Referansı Belirle → her açılışta mevcut mühendislik şifresi → uygulama genelinde MODAL pencere. Arkadaki tüm sayfalar/komutlar pasif; PLC okuma ve haberleşme devam eder. Ana pencereyi kapatıp yeniden açmak, bağlantı kaybı veya odak kaybı 3 saniye tutuşunu iptal eder. HMI sayfa kilidi PLC emniyet zincirinin yerine geçmez.
Talimat: Manuel; bıçak/baskı yukarı; EMG bas; eksenleri elle sıfıra getir; ellerini çek; EMG bırak; servolar hazır; tek butona 3 saniye bas.

Tek buton: BU KONUMU X=0 / Y=0 YAP. 3 saniye tamamlanınca yalnız GVL.xSetZeroRequest TRUE yazılır. Mevcut iki FB'nin Done/Error/Busy/ErrorID alanları RO izlenir; yeni sonuç tagları eklenmez. Önce Request FALSE ve eski Done/Error/Busy temizlenmiş olmalı; eski sonuç yeni başarı sayılmaz. İki Done TRUE görülünce başarı önce HMI'da kaydedilir, sonra Request FALSE yazılır. Bir Error/CommandAborted veya sonuç bekleme süresi aşımında Request FALSE ve açıklayıcı hata; otomatik tekrar yok. Sadece talep göndermek başarı değildir. Gerçek Busy bitleri bırakılmadan işlem tamamlandı/kapandı gösterilmez.
İşlem sırasında buton tekrar tetiklenmez, modal pencere normal olarak kapatılamaz. Bağlantı kaybında sonuç belirsiz gösterilir; reconnect TRUE talebi tekrar yollamaz, bekleyen talep FALSE temizlenir ve güncel gerçek Busy/sonuç okunur. EMG erişimi fiziksel olarak korunur. HMI kapanması/bağlantı kesilmesi MC_Home'u durdurdu diye kabul edilmez.

RO alanlar: Motion_Control.MC_Home_X ve MC_Home_Y için Done, Busy, Error, ErrorID, CommandAborted. Sembol yayını ve online NodeId kullanıcıyla doğrulanır; iç FB üyeleri yayınlanamıyorsa durumu bildir, kendiliğinden yeni sözleşme üretme. Tek RW: GVL.xSetZeroRequest. pulse_home/Execute/konum doğrudan yazılmaz.

Mesaj: “X ve Y sıfır referansı belirlendi.”
Uyarı: “Sıfırlama koşulları sağlanmıyor. Manuel mod, servo hazır ve mekanizmaların yukarıda olduğunu kontrol edin.”
Hata: “Sıfırlama tamamlanamadı. X/Y blok hata bilgisini kontrol edin; iki eksenin referansını yeniden doğrulayın.” HataID gerçek kaynaktan gösterilir. Tek eksen başarılı olursa iki eksen başarı kabul edilmez. Operatör tamamlamadan otomatik kullanıma geçmemelidir; bu sade sürümde kalıcı referans-hatası kilidi eklenmedi.

EMG bırakmak çevrim başlatmaz; işlem manuelde yapılır. Bu işlem C5 Başlangıç Konumuna Dön değildir. Kullanıcı mevcut sürücü ayarında enabled MC_Home'un hareket olmadan iki ekseni 0 yaptığını doğruladı; homing yöntemi değiştirilmez. Yeni yazılım cihazda henüz denenmedi.

## Testler — toplam 5
1. C8-S01 — 1/5: Build; mevcut iki Home ve tek yeni GVL talebi; CFC hesap sırası ve RO semboller doğrulanır.
2. C8-S02 — 2/5: Yanlış şifre, 3 saniye erken bırakma ve modal arkasına tıklamada talep/başka komut oluşmaz.
3. C8-S03 — 3/5: EMG basılı veya manuel değil veya sensör aşağı: Home başlamaz. Fiziksel besleme/jog talebi ile aynı anda referans kabul edilmez.
4. C8-S04 — 4/5: Doğru sırayla iki eksen hareketsiz 0, iki Done; HMI başarı gösterir ve talebi bırakır; otomatik çevrim başlamaz.
5. C8-S05 — 5/5: Eski Done yeni sonuç sayılmaz; bağlantı kaybı/yarım sonuç başarı sayılmaz, TRUE tekrar gönderilmez. Request/Busy sırasında fiziksel besleme ve jog kilidi kontrol edilir. Oluşturulamayan hata senaryosuna YAPILMADI yazılır.
