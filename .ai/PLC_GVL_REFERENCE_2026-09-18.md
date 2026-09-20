# PLC GVL - Kullanıcının paylaştığı güncel kaynak (2026-09-18)

Kullanıcı bu tam GVL kaynağını doğrudan paylaştı ("belki lazım olabilir,
kayıt et"). Aşağıdaki blok BİREBİR kullanıcının verdiği kaynaktır -
yorumlanmadan/değiştirilmeden saklanır. Bu, `.ai/HMI_TEMP_VISION_SIMULATOR_
TASK.md` ve `.ai/HMI_AUTO_CAMERA_BENCH_TEST_TASK.md` için daha önce
kullanılan `GVL_LAST_SHARED_REFERENCE.st` (kullanıcının yerel PLC
koordinasyon paketinden) kaynağından DAHA GÜNCEL kabul edilir - bu dosya
tarih olarak sonra paylaşıldı.

## Bu kaynaktan doğrulanan, önceki notları güncelleyen bulgular

1. **Kalıcı makine parametreleri REAL (32-bit), LREAL DEĞİL.** Dosyanın
   kendi yorumu: "PERSISTENT PARAMETRELERDE LREAL KULLANILMIYOR. Persistent
   memory tasarrufu için makine ayarları REAL tutulur." Kullanıcı nedenini
   netleştirdi (2026-09-18): kullanılan CODESYS ürününde Persistent Variable
   özelliği 64-bit'i (LREAL) desteklemiyor - bu yüzden bilinçli olarak
   REAL'e çekilmiş; "memory tasarrufu" değil, bir ARAÇ/PLATFORM KISITI. Bu,
   2026-09-18'de
   düzeltilen gerçek-PLC `BadTypeMismatch` hatasının KESİN kök nedenidir
   (`lrX_CutVelocity`, `lrX_CutEndPos` vb. - isim "lr" önekiyle başlasa da
   REAL/Float, Double değil). HMI tarafı artık bunu TAHMİN ETMİYOR - her
   yazımdan önce sunucudan gerçek DataType'ı soruyor (`plc/opcua_client.py::
   _write_checked` + `_resolve_variant_type`, bkz. `.ai/memory/
   CHANGELOG_MEMORY.md` 2026-09-18 girişi). Bu kaynak o çözümün NEDEN
   gerekli olduğunu teyit ediyor, kod tarafında ek değişiklik gerekmiyor.
2. **`tVisionHeartbeatTimeout` tipi `TIME` (`T#2s`), düz sayısal ms değil.**
   HMI bu parametreyi `core/parameters.py`'de "ms" birimiyle düz `float`
   olarak okuyup gösteriyor (varsayılan 2000.0). Sunucu-tabanlı tip
   çözümleme (2026-09-18 fix) bu alan için de otomatik doğru tipte
   yazacaktır, ancak TIME'ın OPC UA üzerinde tam olarak nasıl kodlandığı
   (ör. UInt32 ms sayısı) ayrıca doğrulanmadı - kullanıcı bu parametreyi
   Ayarlar'dan değiştirip Uygula derse ayrıca gözlemlenmeli. Şimdiye kadar
   bu alanda bir hata BİLDİRİLMEDİ; bu sadece bir izleme notu.
3. **Persistent parametrelerin GÜNCEL PLC varsayılan değerleri**, kullanıcının
   2026-09-16'da verdiği ve `core/parameters.py`'ye işlenen listeden BAZI
   alanlarda FARKLI (muhtemelen motorlar mekanikten ayrıyken masa testi için
   düşürülmüş):
   - `lrX_CutVelocity`: kod varsayılanı 175.0 → bu kaynakta **50.0**.
   - `lrX_ReturnVelocity`: kod varsayılanı 400.0 → bu kaynakta **50.0**.
   - `lrX_CutEndPos`: kod varsayılanı 3600.0 → bu kaynakta **300.0**.
   - Diğer tüm parametreler (Acc/Dec'ler, Y ekseni, Jog, Software Min/Max,
     lrMaxAllowedSlope, tVisionHeartbeatTimeout) BİREBİR eşleşiyor.
   Kod tarafındaki bu üç değer bilinçli olarak GÜNCELLENMEDİ: Ayarlar ekranı
   zaten hiçbir zaman bu local/varsayılan değerleri "PLC'den okunmuş gerçek
   değer" gibi göstermiyor (`MachineService.is_parameter_confirmed`) - ekran
   açılır açılmaz gerçek PLC okumasıyla ezilirler. Bu üçünün masa testi için
   mi (mekanik ayrık, kısa/yavaş test) yoksa üretim için mi kalıcı olduğu
   belirsiz; kullanıcı netleştirirse `core/parameters.py` güncellenebilir.
4. Diğer tüm tag adları/tipleri (BOOL komutlar, Vision alanları, UDINT
   sequence/heartbeat, motion status vb.) önceki referanslarla ve
   `config/opcua.json`/`.example.json`'daki mevcut eşlemelerle uyumlu -
   yeni bir NodeId/tag değişikliği gerekmiyor.

## Ham kaynak (kullanıcının verdiği, değiştirilmeden)

```st
{attribute 'qualified_only'}

// ============================================================================
// BUFERA TEKSTIL - GVL
//
// PERSISTENT PARAMETRELERDE LREAL KULLANILMIYOR.
// Persistent memory tasarrufu için makine ayarları REAL tutulur.
//
// Runtime / Motion / Trajectory hesaplarında hassasiyet ve
// SoftMotion uyumluluğu için LREAL kullanılmaya devam edilir.
//
// NOT:
// Değişken isimleri HMI / OPC UA sözleşmesini bozmamak için korunmuştur.
// ============================================================================


// ============================================================================
// KALICI MAKİNE / MÜHENDİSLİK PARAMETRELERİ
// ============================================================================

VAR_GLOBAL PERSISTENT RETAIN


    // =====================================================
    // X AXIS - CUT PARAMETERS
    // =====================================================

    lrX_CutStartPos         : REAL := 0.0;
    lrX_CutEndPos           : REAL := 300.0;

    lrX_CutVelocity         : REAL := 50.0;
    lrX_CutAccDec           : REAL := 500.0;


    // =====================================================
    // X AXIS - RETURN PARAMETERS
    // =====================================================

    lrX_ReturnVelocity      : REAL := 50.0;
    lrX_ReturnAccDec        : REAL := 500.0;


    // =====================================================
    // Y AXIS - POSITIONING PARAMETERS
    // =====================================================

    lrY_CenterPosition      : REAL := 0.0;

    lrY_MoveVelocity        : REAL := 10.0;
    lrY_MoveAccDec          : REAL := 100.0;


    // =====================================================
    // MANUAL JOG PARAMETERS
    // =====================================================

    lrX_JogVelocity         : REAL := 50.0;
    lrY_JogVelocity         : REAL := 5.0;

    lrJogAccDec             : REAL := 100.0;


    // =====================================================
    // Y AXIS LIMIT / FOLLOW PARAMETERS
    // =====================================================

    lrY_SoftwareMin         : REAL := -30.0;
    lrY_SoftwareMax         : REAL := 30.0;

    // Maksimum kabul edilen çizgi eğimi dY/dX
    lrMaxAllowedSlope       : REAL := 0.020;

    // Follow sırasında izin verilen maksimum Y hızı
    lrY_MaxVelocity         : REAL := 5.0;


    // =====================================================
    // MOTION / POSITION TOLERANCE PARAMETERS
    // =====================================================

    lrStopAccDec            : REAL := 500.0;

    lrPositionTolerance     : REAL := 0.5;
    lrStopVelocityTolerance : REAL := 1.0;


    // =====================================================
    // COMMUNICATION PARAMETERS
    // =====================================================

    // Vision heartbeat bu süre boyunca değişmezse
    // haberleşme kopmuş kabul edilir.
    tVisionHeartbeatTimeout : TIME := T#2s;

END_VAR



// ============================================================================
// RUNTIME / KOMUT / DURUM DEĞİŞKENLERİ
//
// Bunlar persistent DEĞİLDİR.
// Restart sonrası güvenli/default değerlere döner.
// ============================================================================

VAR_GLOBAL


    // =====================================================
    // Y ABSOLUTE MOVE RUNTIME TARGET
    // =====================================================

    lrY_MovePosition        : LREAL := 0.0;


    // =====================================================
    // HMI / OPERATOR JOG REQUESTS
    // =====================================================

    xX_JogPlusRequest       : BOOL := FALSE;
    xX_JogMinusRequest      : BOOL := FALSE;

    xY_JogPlusRequest       : BOOL := FALSE;
    xY_JogMinusRequest      : BOOL := FALSE;


    // =====================================================
    // PLC JOG PERMISSION
    // =====================================================

    xManualJogAllowed       : BOOL := FALSE;


    // =====================================================
    // REAL MOTION JOG COMMANDS
    // =====================================================

    xX_JogPlus              : BOOL := FALSE;
    xX_JogMinus             : BOOL := FALSE;

    xY_JogPlus              : BOOL := FALSE;
    xY_JogMinus             : BOOL := FALSE;


    // =====================================================
    // ACTUAL AXIS VALUES
    // =====================================================

    lrX_ActualPosition      : LREAL := 0.0;
    lrY_ActualPosition      : LREAL := 0.0;

    lrX_ActualVelocity      : LREAL := 0.0;
    lrY_ActualVelocity      : LREAL := 0.0;


    // =====================================================
    // TRAJECTORY CALCULATED VALUES
    // =====================================================

    lrVision_TargetX        : LREAL := 0.0;
    lrVision_TargetY        : LREAL := 0.0;

    lrVision_Slope          : LREAL := 0.0;

    lrY_SetPosition         : LREAL := 0.0;
    lrY_SetVelocity         : LREAL := 0.0;

    xTrajectoryValid        : BOOL := FALSE;
    xTrajectoryFault        : BOOL := FALSE;


    // =====================================================
    // MOTION COMMANDS - X
    // =====================================================

    xX_CutExecute           : BOOL := FALSE;
    xX_ReturnExecute        : BOOL := FALSE;


    // =====================================================
    // MOTION COMMANDS - Y
    // =====================================================

    xY_MoveExecute          : BOOL := FALSE;
    xY_FollowEnable         : BOOL := FALSE;


    // =====================================================
    // MOTION STATUS - X CUT
    // =====================================================

    xX_CutDone              : BOOL := FALSE;
    xX_CutBusy              : BOOL := FALSE;
    xX_CutError             : BOOL := FALSE;


    // =====================================================
    // MOTION STATUS - X RETURN
    // =====================================================

    xX_ReturnDone           : BOOL := FALSE;
    xX_ReturnBusy           : BOOL := FALSE;
    xX_ReturnError          : BOOL := FALSE;


    // =====================================================
    // MOTION STATUS - Y ABSOLUTE
    // =====================================================

    xY_MoveDone             : BOOL := FALSE;
    xY_MoveBusy             : BOOL := FALSE;
    xY_MoveError            : BOOL := FALSE;


    // =====================================================
    // MOTION STATUS - Y FOLLOW
    // =====================================================

    xY_FollowBusy           : BOOL := FALSE;
    xY_FollowError          : BOOL := FALSE;


    // =====================================================
    // OPERATOR / MACHINE COMMANDS
    // =====================================================

    Start                   : BOOL := FALSE;
    Stop                    : BOOL := FALSE;
    Reset                   : BOOL := FALSE;
    Pause                   : BOOL := FALSE;


    // =====================================================
    // BASIC MACHINE STATUS
    // =====================================================

    MachineReady            : BOOL := FALSE;

    CutActive               : BOOL := FALSE;
    CutStart                : BOOL := FALSE;
    CutStop                 : BOOL := FALSE;

    ServoReady              : BOOL := FALSE;

    // FALSE = normal
    // TRUE  = emergency aktif
    EmergencyState          : BOOL := FALSE;


    // =====================================================
    // PNEUMATIC / MACHINE STATUS
    // =====================================================

    IPC_Pb                  : BOOL := FALSE;
    IPC_Pk                  : BOOL := FALSE;

    // Gerçek aşağı-konum sensörlerinden beslenecek
    BladeZDown              : BOOL := FALSE;
    ClampDown               : BOOL := FALSE;


    // =====================================================
    // FEED / CURTAIN MOTOR
    // =====================================================

    FeedActive              : BOOL := FALSE;
    FeedComplete            : BOOL := FALSE;

    FeedForwardPB           : BOOL := FALSE;
    FeedReversePB           : BOOL := FALSE;

    FeedManualAllowed       : BOOL := FALSE;


    // =====================================================
    // PLC -> IPC / CAMERA
    // =====================================================

    IPC_X_POS               : LREAL := 0.0;
    IPC_Y_POS               : LREAL := 0.0;

    ActualX_mm              : LREAL := 0.0;
    ActualY_mm              : LREAL := 0.0;

    X_Velocity              : LREAL := 0.0;

    CutEndX_mm              : LREAL := 0.0;
    StripLength_mm          : LREAL := 0.0;

    // -1 / 0 / +1
    Direction               : INT := 0;


    // =====================================================
    // CAMERA / VISION -> PLC
    // =====================================================

    VisionReady             : BOOL := FALSE;
    LineValid               : BOOL := FALSE;
    VisionFault             : BOOL := FALSE;

    udiVisionSequence       : UDINT := 0;

    TargetY_mm              : LREAL := 0.0;
    TargetX_mm              : LREAL := 0.0;

    Confidence              : LREAL := 0.0;

    Heartbeat               : UDINT := 0;


    // =====================================================
    // OPTIONAL VISION PROCESS SIGNALS
    // =====================================================

    EndBufferReady          : BOOL := FALSE;

    CutPermit               : BOOL := FALSE;

    ZDownRequest            : BOOL := FALSE;
    ZDownAtX_mm             : LREAL := 0.0;

    FaultCode               : INT := 0;


    // =====================================================
    // UI / LEGACY COMPATIBILITY
    // =====================================================

    ShowVisionScreen        : BOOL := FALSE;
    VisionScreenRelease     : BOOL := FALSE;


    // =====================================================
    // COMMUNICATION / DIAGNOSTIC
    // =====================================================

    xVisionHeartbeatOK      : BOOL := FALSE;
    xOPCUACommunicationOK   : BOOL := FALSE;


    // =====================================================
    // AXIS RESET / POWER / STOP RUNTIME
    // =====================================================

    xAxisReset              : BOOL := FALSE;

    xX_ResetDone            : BOOL := FALSE;
    xY_ResetDone            : BOOL := FALSE;

    xServoPowerEnable       : BOOL := FALSE;
    xMotionEnable           : BOOL := FALSE;

    xEmergencyOK            : BOOL := FALSE;

    xMotionStop             : BOOL := FALSE;

    xX_StopDone             : BOOL := FALSE;
    xY_StopDone             : BOOL := FALSE;


    // =====================================================
    // POWER STATUS
    // =====================================================

    xX_PowerStatus          : BOOL := FALSE;
    xX_PowerBusy            : BOOL := FALSE;
    xX_PowerError           : BOOL := FALSE;

    xY_PowerStatus          : BOOL := FALSE;
    xY_PowerBusy            : BOOL := FALSE;
    xY_PowerError           : BOOL := FALSE;


    // =====================================================
    // MACHINE LOGIC / STATE MACHINE
    // =====================================================

    eMachineState           : E_MachineState := E_MachineState.INIT;

    // FALSE = Auto
    // TRUE  = Service / Manual
    xManualMode             : BOOL := FALSE;

    xCycleActive            : BOOL := FALSE;
    xStartPermitted         : BOOL := FALSE;


    // =====================================================
    // AXIS POSITION STATUS
    // =====================================================

    xX_AtStart              : BOOL := FALSE;
    xY_AtCenter             : BOOL := FALSE;


    // =====================================================
    // PNEUMATIC OUTPUT COMMANDS
    // =====================================================

    xClampValveCmd          : BOOL := FALSE;
    xBladeValveCmd          : BOOL := FALSE;


    // =====================================================
    // CURTAIN FEED OUTPUT COMMANDS
    // =====================================================

    xFeedForwardCmd         : BOOL := FALSE;
    xFeedReverseCmd         : BOOL := FALSE;

END_VAR
```
