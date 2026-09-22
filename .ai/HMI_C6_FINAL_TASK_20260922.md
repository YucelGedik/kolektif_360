# C6 toplu teslim — 2026-09-22
Temel: Bufera_Perde_Kesme_20260921_1050_C06.export.
KAYNAK FARKI: C6.1 Start hesabi Alarm_Control oncesinde tek kalmis; teslimde Alarm sonrasinda kabul ve CASE sonrasinda readback iki hesap vardi. Alarm_Control C6.1 ile ayni. Bu fark raporlanarak pakette duzeltildi; orijinal export degistirilmedi.

## Uygulama
1 GVL normal VAR_GLOBAL'a GVL_ADDITIONS.st yeni3BOOL ekle; onceki5C6 teshis boolu korunur.
2 Logic_Control declaration ve implementation bu klasordeki tam dosyalarla degistirilir. Iki yeni local BOOL: xFaultStopReleasePending / xResetInputsReleased. State/bölüm basliklari kaynakta korunur.
3 Alarm_Control implementation tam dosyasi yapistirilir; declaration degismez (ikiTON). Task/CFC/enum/persistent degismez. Timeout normalGVL10s korunur.
4 Symbol Configuration yeni3alarm RO yayinla. HMI yeni mappinglerini online teyit et. Build kullanici CODESYSte yapacak.

## C6.2 acik davranis kararlari
- Aktifotomatik cevrimde Manuel secimi latchedHATA/FAULT; otomatik donus yok. HMI zaten degisimi kilitler, PLC ek savunmasi. xManualMode'a PLC yazmaz.
- Baski tutma gereken WAIT_VISION,ALIGN_Y,WAIT_BLADE_REQUEST,BLADE_DOWN,BLADE_UP,RETURN_AXES boyunca clamp kaybi latchedHATA. CUTTING mevcut alarminda; normalCLAMP_DOWN/CLAMP_UP'ta beklenen sensorFalse hata degil.
- OtomatikRETURN_AXES'te bicak asagi sensoru/komutuHATA. ManuelC5 kontrolu zaten var.
- Hareket/cycle aktifken eksen veyaStopFB hatasi FAULT. EskiStop.Error+standstill C5'te de genelFAULT kurtarma yoluna yonlenebilir;140da kalma zorunlulugu yok.
- MC_Reset yalniz gercek errorstop, durmus eksenler, bos hareket talepleri ve INIT/MANUAL/RECOVERY/FAULT durumlarinda. Calisanotomatik cevrim/C5 hareketinde Reset yok sayilir; Stop kullanilir.
- FAULT Reset iki taramada: operatorReset, eksenstandstill veya hatasizStopDone+stopping ise StopExecuteFALSE; sonraki Power cagrisinda iki standstill ve StopBusy/ErrorFALSE gorulunce alarmResetAccepted veRECOVERY. Valf korunur. Gerceksurucu arizasinda ilkReset drive hatasini giderir; bloklar temizlendikten sonra ikinciReset proses hazirligina gecirir. Bu otomatik reset dongusu degil.
- C5.1'deki yerel stop release korunur; yeni globalaxis/Stop error yolu gerektigindeFAULT'a gider.

## Statik dogrulama / sinir
Tum GVL referanslari deklarasyonlarla eslesti; IF dengesi, tekAlarm/WriteOutputs cagrisi, ikiStart hesabi kontrol edildi. FAULT disindaki18state tablosunun diger govdeleri yorum/bosluk haric kaynakla ayni; hareket tepkisi yeni globalinterlock/alarm kosullariyla degisir. CODESYS derleyicisi veya PLC testi yok. Testler TOPLU_TESTLER.md 20adet, hepsiYAPILMADI. C6 tasarim/kod teslimi tamam; cihaz kabulu BEKLIYOR.
HMI16notu uygulandi256/256test raporu HMIagentina aittir, bizim cihaz testimiz degildir. Yeni3alarm H20-H22 asagidaki HMI gorevinde. Kisa live motion hata olaylarinin eksiksiz ilk-neden tarihcesi mevcut degil; genelFAULT fallback korunur.
Kapsam disi aciklar: fizikselX/Y limit uc/kontak bilgisi; yukari timeout,Vision paket yasi ve aktifVisionkaybi STOPPING/donus politikasi ayri karar gerektirir. Bunlar bu teslimde sessizce degistirilmedi. Genel urun/hardware devreyealma bitmis iddiasi yok.

# PLC-HMI-20260922-17 — HMI ek gorev
Mevcut16katalogunu surdur; HMI256test sonucu alindi. YeniPLC3BOOL read-only; gercek/example config/model/catalog birlikte, onlineyayindan once biliniyor varsayma:
H20 HATA GVL.xAlarmModeChangedDuringCycle: "Calisan cevrimde mod degistirme talebi alindi; makine durduruldu."
H21 HATA GVL.xAlarmClampLostDuringCycle: "Cevrim sirasinda baski asagi sensoru kayboldu; makine durduruldu."
H22 HATA GVL.xAlarmBladeNotClearDuringReturn: "Eksenler donerken bicak acikligi kayboldu; makine durduruldu."
Ucunde de neden kontrolu->duruş->Reset->Manuel->ikiYukari->3sBaslangicaDon->perdekontrolu->AutoStart. ResetdurumuPLC otoritesi; kendi alarmclear yok. Gercekaxisarizasinda ilkReset surucu,ikinci uygunReset proses icin gerekebilir; kullaniciya devam eden hata ve eksik kosulu goster, otomatikReset gonderme.
Yalniz kopru dokumanlarina dayanarak online node teyidi var denmez. Kod/plctesti henuz yok. Eksiktag falseyerine bilinmiyor; H12-H15 'guvenliFalse' varsayimi aktifalarm yok kaniti degil. MevcutC6.1beshastag da tam gercekconfigte eklenmeli.
HMI offline testleri:3alarm initialTRUE/rising/falling/history/resetreddi; coklualarm/fallbacksayac; hareketBusy/cycle iken mode veReset UI davranisi (PLC hareketresetini yok sayar); reconnectkomut yok. Sonuclari kopruye bildir. Toplu20PLCTest kullanicinin baglantisi gelince yapilacak.
