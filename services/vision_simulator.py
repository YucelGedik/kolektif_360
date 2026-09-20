"""Geçici mühendislik diagnostic ekranı ve Vision veri simülatörü
(görev: .ai/HMI_TEMP_VISION_SIMULATOR_TASK.md, PLC-HMI-20260917-02).

Bu servis GEÇİCİDİR. Gerçek kamera uygulamasının PLC'ye göndereceği sınırlı
Vision->PLC alanlarını (kapalı izin listesi: `machine_service.
VISION_SIM_WRITABLE_TAGS`) mühendisin elle tetiklediği tek bir sıralı pakette
üretir. Ana `MachineSnapshot`'a sahte veri yazmaz, `DemoSimulator` ile
karıştırılmaz (o, PLC olmayan ortamın genel sahte kaynağıdır; bu servis
sadece Vision alanlarını, sadece armed iken, sadece gerçek/demo worker'a
gönderir).

Sahiplik / güvenlik modeli:
- `armed=False, source="REAL"` varsayılan ve her açılışta/yeniden bağlanmada
  zorunlu başlangıç durumu; önceki armed durumu diske kaydedilmez.
- Kaynak devri (REAL <-> SIMULATOR) yalnız çevrim pasif iken yapılabilir
  (`can_arm`). Armed olduktan SONRA, tasarlanan kullanım tam olarak budur:
  mühendis simülatörü aktif kamera kaynağı yapıp ayrı pencereden Start/Stop
  ile gerçek çevrimi paralel çalıştırır (kullanıcı talebi, 2026-09-17).
- Bağlantı durumu değiştiğinde (kopma, reconnect, ilk bağlantı) sahiplik asla
  otomatik varsayılmaz: `_force_disarm` çağrılır, temizlik yazısı denenmez
  (bağlantı garantisi yok), kullanıcı yeniden arm etmelidir.
- Planlı `disarm()` çevrim pasifken izin alanlarını (VisionReady, LineValid,
  VisionFault, CutPermit, ZDownRequest) FALSE'a geri çekmeye çalışır; çevrim
  aktifken çağrılırsa bu yazıları ATLAR (hareket ortasında izni çekmek
  STOPPING/dönüş hareketi doğurabilir - görev notu) ve arayüze bunu açıkça
  bildirir.
- Her arm/disarm bir "generation" sayacını ilerletir; bekleyen bir paket
  sonucu farklı bir generation için gelirse (disarm/reconnect arada oldu)
  sessizce yok sayılır. Bu artık sadece "sonucu yok say" değil: disarm/
  reconnect ayrıca `MachineService.request_vision_cancel_pending()` ile
  worker'daki bekleyen yazma coroutine'ini GERÇEKTEN iptal eder (2026-09-17,
  PLC notu) - eski bir paketin kalan alanları (özellikle sequence) artık
  geçersiz bir oturum için PLC'ye yazılmaz.

Otomatik kamera / düz çizgi masa testi (PLC-HMI-20260917-03, kullanıcı:
"manuel paket göndererek ilerlemek istemiyorum" - motorlar mekanikten ayrı,
sensörler elle tetikleniyor): `start_auto_camera()` sonra ana ekrandan Start
verilince, `_on_auto_camera_tick` PLC state'ini (`cycle_state`,
`xTrajectoryValid/Fault`) ve `x_actual_pos`'u izleyerek TargetX/TargetY/
CutPermit/ZDownRequest'i kendisi üretir - kullanıcı tek tek paket/izin
tıklamaz. Manuel kontroller (dialog) auto_camera_active iken devre dışı
bırakılır ("tek arbiter" kuralı, görev notu) - aynı tag'e otomatik ve
manuel yoldan zıt yazı gitmesin.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from core.cycle_state import CycleState
from core.models import ConnectionState

if TYPE_CHECKING:
    from services.machine_service import MachineService

# Eksen "durmuş" kabulü için actual velocity toleransı (mm/s). 2026-09-17
# düzeltmesi (PLC notu, PLC-HMI-20260917-03): "PLC'de Y actual velocity yok"
# denen önceki not YANLIŞTI - GVL.lrY_ActualVelocity mevcut ve artık
# `MachineSnapshot.y_actual_vel` olarak okunuyor; kontrol şimdi HER İKİ
# eksene de bakıyor.
AXIS_STOPPED_VELOCITY_TOLERANCE = 0.5

# Hedef X, güncel X'ten en az bu kadar ileride olmalı (Trajectories_Calculate
# kuralı, docs/reports/2026-09-17_06_PARTIAL_AUTO_TEST.md).
MIN_TARGET_X_LEAD_MM = 0.001

UINT32_MOD = 2**32

# -- Otomatik kamera / düz çizgi masa testi (PLC-HMI-20260917-03) -----------

# Paket üretim periyodu (ms). Görev notu: "PLC 2 ms taskına HMI paket hızını
# eşitleme" - bu imkansız/gereksiz; bunun yerine ileri bakış mesafesi (aşağı)
# bu periyodu ve kesim hızını hesaba katarak hedefin asla geride kalmamasını
# sağlıyor.
AUTO_CAMERA_DEFAULT_PERIOD_MS = 100
AUTO_CAMERA_MIN_PERIOD_MS = 50
AUTO_CAMERA_MAX_PERIOD_MS = 1000

# İleri bakış mesafesi kaç paket-periyodu kadar pay içersin (iletim/PLC
# gecikmesi payı) ve minimum taban (mm/s çok düşükken bile anlamlı ileri
# hedef kalsın).
LEAD_MARGIN_PACKET_PERIODS = 5
MIN_LEAD_DISTANCE_MM = 5.0

# Aynı state içinde actual X bu kadar (mm) değişmeden yeni paket/sequence
# üretme - "gereksiz paket üretme" (görev notu). State DEĞİŞTİĞİNDE (örn.
# WAIT_VISION'a yeni girildiğinde) bu eşikten bağımsız olarak HER ZAMAN bir
# paket gönderilir (görev notu: "Start'ından SONRA yeni sequence mutlaka
# gönder").
PACKET_REFRESH_EPSILON_MM = 0.5

# CutPermit TRUE tutulan state'ler (Faz C tablosu).
_CUT_PERMIT_STATES = frozenset(
    {
        CycleState.WAIT_VISION,
        CycleState.ALIGN_Y,
        CycleState.WAIT_BLADE_REQUEST,
        CycleState.BLADE_DOWN,
        CycleState.CUTTING,
    }
)

# Bu state'lerdeyken taze bir TargetX/TargetY paketi (yeni sequence) üretmek
# anlamlı; dönüş/idle state'lerinde ("kesim dışı") yeni ileri hedef üretmek
# görev notunca gereksiz sayılıyor.
_PACKET_STATES = _CUT_PERMIT_STATES

# H6 (2026-09-18, PLC-HMI-20260918-04): kamera senaryoları. "straight" -
# varsayılan, TargetY = canlı lrY_CenterPosition (değişmedi). "tilted" -
# ikinci, açıkça seçilen senaryo: y(x) = y0 + m*(x-x0), sabit bir çevrim-
# başlangıç referansından (x0,y0) - kullanıcı notu: "her pakette sabit Y
# arttırma yok", TargetY doğrudan TargetX'in bir fonksiyonu.
CAMERA_SCENARIOS = ("straight", "tilted")

# Kullanıcıya "şimdi ne bekleniyor" ipucu (Faz D, salt bilgi - hiçbir yazı
# üretmez). ui/machine/vision_simulator_page.py bunu gösterir.
SENSOR_HINTS: dict[CycleState, str] = {
    CycleState.INIT: "Bekleniyor…",
    CycleState.WAIT_FOR_MATERIAL: "Yeni çevrim için ana ekrandan Start verin.",
    CycleState.CLAMP_DOWN: "Şimdi CLAMP (baskı) sensörünü TETİKLEYİN (aşağı).",
    CycleState.WAIT_VISION: "Kamera verisi bekleniyor - otomatik üretiliyor.",
    CycleState.ALIGN_Y: "Y hizalanıyor - bekleyin.",
    CycleState.WAIT_BLADE_REQUEST: "Bıçak talebi (ZDownRequest) gönderiliyor - PLC değerlendiriyor.",
    CycleState.BLADE_DOWN: "Şimdi BLADE (bıçak) sensörünü TETİKLEYİN (aşağı).",
    CycleState.CUTTING: "Kesim sürüyor - beklemede kalın.",
    CycleState.BLADE_UP: "Şimdi BLADE sensörünü BIRAKIN (yukarı).",
    CycleState.RETURN_AXES: "Eksenler dönüyor - beklemede kalın.",
    CycleState.CLAMP_UP: "Şimdi CLAMP sensörünü BIRAKIN (yukarı).",
    CycleState.CYCLE_COMPLETE: "Çevrim tamamlandı - yeni çevrim için Start.",
    CycleState.STOPPING: "Durduruluyor - yeni kesim talebi yok, bekleyin.",
    CycleState.RECOVERY: "Recovery - normal PLC akışını izleyin.",
    CycleState.FAULT: "Arıza - Reset/recovery akışını izleyin.",
    CycleState.MANUAL: "Manuel modda - otomatik kesim paketi üretilmiyor.",
}


def sensor_hint(cycle_state_value: int) -> str:
    try:
        state = CycleState(cycle_state_value)
    except ValueError:
        return "Bilinmeyen durum."
    return SENSOR_HINTS.get(state, "—")


class VisionSimulatorService(QObject):
    armedChanged = Signal(bool)
    packetResult = Signal(bool, str)
    lastErrorChanged = Signal(str)
    autoCameraChanged = Signal(bool)

    def __init__(self, machine_service: "MachineService", parent: QObject | None = None):
        super().__init__(parent)
        self._machine = machine_service
        self.armed = False
        self.source = "REAL"  # "REAL" | "SIMULATOR"
        self._generation = 0
        self._pending_generation = -1
        self._pending_sequence = 0
        self._send_in_flight = False
        self._sequence_value = 0
        self._heartbeat_value = 0
        self.last_error = ""

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.timeout.connect(self._on_heartbeat_tick)

        # Otomatik kamera / düz çizgi masa testi (PLC-HMI-20260917-03).
        self.auto_camera_active = False
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(AUTO_CAMERA_DEFAULT_PERIOD_MS)
        self._auto_timer.timeout.connect(self._on_auto_camera_tick)
        self._last_cut_permit: bool | None = None
        self._last_z_down: bool | None = None
        self._last_state: CycleState | None = None
        self._last_sent_actual_x: float | None = None
        self.last_target_x: float | None = None
        self.last_target_y: float | None = None
        self.last_sensor_hint: str = ""

        # H6: eğimli kamera senaryosu. Referans (x0,y0) yalnız
        # start_auto_camera()'da (scenario "tilted" ise) BİR KEZ
        # yakalanır - "UI değişikliği cycle sırasında referansı
        # sıçratmasın" (görev notu): eğim/senaryo değişikliği yalnız
        # auto_camera_active=False iken kabul edilir.
        self.camera_scenario = "straight"
        self.tilted_slope = 0.0
        self._tilt_reference: tuple[float, float] | None = None

        machine_service.connectionStateChanged.connect(self._on_connection_state)
        machine_service.visionSequentialWriteResult.connect(self._on_packet_result)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(lambda: self.disarm())

    # -- ownership / arm-disarm -------------------------------------------

    def can_arm(self) -> tuple[bool, str]:
        if not self._machine.vision_simulator_enabled:
            return False, "Vision simülatörü özelliği kapalı (config: vision_simulator_enabled)."
        if self.armed:
            return False, "Zaten armed."
        snap = self._machine.snapshot
        if snap.connection_state not in (ConnectionState.CONNECTED, ConnectionState.DEMO):
            return False, "PLC bağlı değil."
        if snap.cycle_active:
            return False, "Çevrim aktif; kaynak devri için önce çevrimi durdurun."
        if abs(snap.x_actual_vel) > AXIS_STOPPED_VELOCITY_TOLERANCE:
            return False, "X ekseni hareket halinde; eksenler durmadan kaynak devri yapılmaz."
        if abs(snap.y_actual_vel) > AXIS_STOPPED_VELOCITY_TOLERANCE:
            return False, "Y ekseni hareket halinde; eksenler durmadan kaynak devri yapılmaz."
        return True, ""

    def arm(self) -> tuple[bool, str]:
        ok, reason = self.can_arm()
        if not ok:
            return False, reason
        snap = self._machine.snapshot
        self.armed = True
        self.source = "SIMULATOR"
        self._generation += 1
        # İlk sequence/heartbeat PLC'nin son bilinen değerinden devam eder,
        # sıfırdan başlamaz (görev notu: "İlk sequence ve heartbeat mevcut
        # PLC değerinden alınır").
        self._sequence_value = snap.vision_sequence
        self._heartbeat_value = snap.vision_heartbeat
        self.armedChanged.emit(True)
        return True, ""

    def disarm(self) -> tuple[bool, str]:
        if not self.armed:
            return True, ""
        snap = self._machine.snapshot
        cycle_active = snap.cycle_active
        self._heartbeat_timer.stop()
        was_auto_camera_active = self.auto_camera_active
        self._stop_auto_camera_internal()
        if was_auto_camera_active:
            self.autoCameraChanged.emit(False)
        # Bekleyen (in-flight) bir paket varsa gerçekten iptal et - kalan
        # alanları (özellikle sequence'i) artık geçersiz bir oturum için
        # PLC'ye yazmasın (görev notu, 2026-09-17: generation sadece sonucu
        # yok saymak değil, gerçek iptal için de kullanılmalı).
        self._machine.request_vision_cancel_pending()
        note = ""
        if not cycle_active and snap.connection_state == ConnectionState.CONNECTED:
            # Planlı, temiz bırakma: çevrim pasifken izin/ready/istek
            # alanlarını geri çek.
            for tag in (
                "vision_ready",
                "line_valid",
                "vision_fault",
                "vision_cut_permit",
                "vision_z_down_request",
            ):
                self._machine.request_vision_write(tag, False)
        elif cycle_active:
            # ÖNEMLİ (2026-09-17, PLC notu: 1635 exportunda heartbeat
            # bypass'ı kaldırılıp orijinal hesaba dönüldü) - bu artık
            # TEORİK değil, GERÇEK bir risk: heartbeat üretimini burada
            # durdurmak, PLC'nin kendi xVisionHeartbeatOK hesabının kısa
            # sürede FALSE olmasına ve dolayısıyla STOPPING/dönüş hareketine
            # yol açabilir. Bool alanları geri çekmeyi ATLAMAK bunu "güvenli
            # kapanış" yapmaz - sadece daha az riskli bırakır.
            note = (
                "Çevrim aktifken bırakıldı: VisionReady/LineValid/CutPermit/"
                "ZDownRequest alanları geri çekilmedi. UYARI: heartbeat "
                "üretimi de durduruldu - PLC'nin gerçek heartbeat kontrolü "
                "(bypass yok) kısa sürede xVisionHeartbeatOK'ı FALSE yapıp "
                "STOPPING/dönüş hareketini tetikleyebilir. Bu 'güvenli "
                "kapanış' değildir, sadece izin alanlarını geri çekmenin "
                "daha büyük riskini önler."
            )
        self.armed = False
        self.source = "REAL"
        self._generation += 1
        self._send_in_flight = False
        self.armedChanged.emit(False)
        return True, note

    def _force_disarm(self, reason: str) -> None:
        """Bağlantı durumu değiştiğinde (kopma/reconnect) çağrılır - temizlik
        yazısı DENENMEZ (bağlantı garantisi yok, görev notu), sadece yerel
        sahiplik durumu sıfırlanır. Bekleyen paket varsa GERÇEKTEN iptal
        edilir (worker'daki eski yazı, sadece sinyal sonucu değil)."""
        if not self.armed:
            return
        self._heartbeat_timer.stop()
        was_auto_camera_active = self.auto_camera_active
        self._stop_auto_camera_internal()
        self._machine.request_vision_cancel_pending()
        self.armed = False
        self.source = "REAL"
        self._generation += 1
        self._send_in_flight = False
        self.last_error = reason
        self.lastErrorChanged.emit(reason)
        self.armedChanged.emit(False)
        if was_auto_camera_active:
            self.autoCameraChanged.emit(False)

    def _on_connection_state(self, _state: str) -> None:
        # Her bağlantı durumu değişimi (ilk bağlanma, kopma, reconnect) için
        # sahiplik asla otomatik taşınmaz/korunmaz - kullanıcı yeniden arm
        # etmelidir (görev notu, Faz 1).
        self._force_disarm("Bağlantı durumu değişti; Vision simülatörü otomatik disarmed.")

    # -- heartbeat ----------------------------------------------------------

    def set_heartbeat_enabled(self, enabled: bool) -> tuple[bool, str]:
        if enabled and not self.armed:
            return False, "Armed değilken heartbeat başlatılamaz."
        if enabled:
            timeout_ms = self._machine.get_parameter_value("t_vision_heartbeat_timeout")
            period_ms = max(200.0, timeout_ms / 3.0) if timeout_ms > 0 else 500.0
            self._heartbeat_timer.start(int(period_ms))
        else:
            self._heartbeat_timer.stop()
        return True, ""

    @property
    def heartbeat_active(self) -> bool:
        return self._heartbeat_timer.isActive()

    def _on_heartbeat_tick(self) -> None:
        if not self.armed:
            self._heartbeat_timer.stop()
            return
        self._heartbeat_value = (self._heartbeat_value + 1) % UINT32_MOD
        self._machine.request_vision_write("vision_heartbeat", self._heartbeat_value)

    # -- otomatik kamera / düz çizgi masa testi (PLC-HMI-20260917-03) --------
    # Kullanıcı manuel paket/CutPermit/ZDownRequest tıklamak istemiyor: ARM
    # edip bunu başlatınca, actual X ve PLC state'i (cycle_state,
    # xTrajectoryValid/Fault) izleyerek Faz C tablosundaki davranışı üretir.
    # PLC state'ine, sensörlerine, motion/valf/readiness/trajectory
    # SONUÇLARINA hiç yazmaz - yalnız Vision->PLC izin listesindeki alanlara.

    def start_auto_camera(self, period_ms: int | None = None) -> tuple[bool, str]:
        if not self.armed or self.source != "SIMULATOR":
            return False, "Önce ARM edin."
        if self.auto_camera_active:
            return True, ""
        if period_ms is not None:
            ok, reason = self.set_auto_camera_period_ms(period_ms)
            if not ok:
                return False, reason
        self.auto_camera_active = True
        self._last_cut_permit = None
        self._last_z_down = None
        self._last_state = None
        self._last_sent_actual_x = None
        # "Happy path" alanları (Faz C: tüm satırlarda VisionReady TRUE,
        # VisionFault FALSE) oturum başında bir kez yazılır - her tick'te
        # tekrar tekrar değil (gereksiz pulse üretme, görev notu).
        self._machine.request_vision_write("vision_ready", True)
        self._machine.request_vision_write("vision_fault", False)
        self._machine.request_vision_write("line_valid", True)
        # BUG (2026-09-17, kullanıcı raporu): "otomatik başlattım ama
        # heartbeat üretmedi" - GVL.xVisionHeartbeatOK hiç TRUE olmadı,
        # dolayısıyla MachineReady formülü (xVisionHeartbeatOK şart)
        # sağlanamadı. Kök neden: manuel "Heartbeat Otomatik Üret" kutusu
        # otomatik kamera aktifken devre dışı bırakılıyordu AMA heartbeat'i
        # `start_auto_camera` hiçbir zaman kendisi başlatmıyordu - iki ayrı
        # mekanizma yanlışlıkla birbirinden bağımsız kaldı. Heartbeat artık
        # otomatik kameranın kendisi tarafından başlatılıyor/durduruluyor;
        # manuel kutu bu modda salt-gösterge (devre dışı + senkron işaretli).
        self.set_heartbeat_enabled(True)
        if self.camera_scenario == "tilted":
            # Sabit çevrim başlangıç referansı - bu andan sonra slope/UI
            # değişikliği bu referansı sıçratmaz (görev notu); değiştirmek
            # isteyen kullanıcı önce durdurup yeniden başlatmalı.
            snap = self._machine.snapshot
            self._tilt_reference = (snap.x_actual_pos, snap.y_actual_pos)
        self._auto_timer.start()
        self.autoCameraChanged.emit(True)
        return True, ""

    def stop_auto_camera(self) -> None:
        self._stop_auto_camera_internal()
        self.autoCameraChanged.emit(False)

    def _stop_auto_camera_internal(self) -> None:
        self.auto_camera_active = False
        self._auto_timer.stop()
        self._heartbeat_timer.stop()
        self._tilt_reference = None

    def set_camera_scenario(self, scenario: str, slope: float = 0.0) -> tuple[bool, str]:
        """H6 (2026-09-18): varsayılan "straight" korunur; "tilted" ikinci,
        açıkça seçilen bir senaryodur. Yalnız auto_camera PASİFKEN
        değiştirilebilir (referansın cycle ortasında sıçramaması için).
        Eğim, PLC'nin GERÇEK `lrMaxAllowedSlope` okumasına ve türetilen Y
        feed-forward hızının `lrY_MaxVelocity`'yi aşmamasına göre ön-
        kontrol edilir (best-effort - PLC nihai otoritedir, bu sadece
        kesin bilinen bir reddi önceden haber verir)."""
        if scenario not in CAMERA_SCENARIOS:
            return False, f"Bilinmeyen senaryo: {scenario}"
        if self.auto_camera_active:
            return False, "Senaryo, otomatik kamera çalışırken değiştirilemez - önce durdurun."
        if scenario == "tilted":
            if not math.isfinite(slope):
                return False, "Eğim sonlu (finite) bir sayı olmalı."
            snap = self._machine.snapshot
            max_slope = snap.lr_max_allowed_slope
            if max_slope > 0 and abs(slope) > max_slope:
                return False, (
                    f"Eğim ({slope:g}) PLC'nin lrMaxAllowedSlope sınırını ({max_slope:g}) aşıyor."
                )
            cut_velocity = self._machine.get_parameter_value("lr_x_cut_velocity")
            max_y_velocity = self._machine.get_parameter_value("lr_y_max_velocity")
            required_y_velocity = abs(slope) * abs(cut_velocity)
            if max_y_velocity > 0 and required_y_velocity > max_y_velocity:
                return False, (
                    f"Bu eğim + X hızı ({cut_velocity:g} mm/s) gereken Y hızını "
                    f"({required_y_velocity:g} mm/s) lrY_MaxVelocity'den ({max_y_velocity:g}) "
                    "fazla yapıyor."
                )
            # Son nokta kontrolü (görev notu, Kabul: "son noktadaki ileri
            # hedef"): referans henüz yakalanmamışsa güncel actual X/Y en
            # iyi tahmindir; gerçek per-paket kontrol send_packet'te de var.
            x0, y0 = self._tilt_reference or (snap.x_actual_pos, snap.y_actual_pos)
            cut_end = self._machine.get_parameter_value("lr_x_cut_end_pos")
            y_min = self._machine.get_parameter_value("lr_y_software_min")
            y_max = self._machine.get_parameter_value("lr_y_software_max")
            y_at_end = y0 + slope * (cut_end - x0)
            if not (y_min <= y_at_end <= y_max):
                return False, (
                    f"Bu eğimle kesim sonunda (X={cut_end:g}) hedef Y ({y_at_end:g}) "
                    f"Y yazılım sınırlarının ({y_min:g}..{y_max:g}) dışına çıkıyor."
                )
        self.camera_scenario = scenario
        self.tilted_slope = float(slope) if scenario == "tilted" else 0.0
        return True, ""

    def set_auto_camera_period_ms(self, period_ms: int) -> tuple[bool, str]:
        if self.auto_camera_active:
            return False, "Periyot, otomatik kamera çalışırken değiştirilemez - önce durdurun."
        if not (AUTO_CAMERA_MIN_PERIOD_MS <= period_ms <= AUTO_CAMERA_MAX_PERIOD_MS):
            return False, (
                f"Periyot {AUTO_CAMERA_MIN_PERIOD_MS}-{AUTO_CAMERA_MAX_PERIOD_MS} ms arasında olmalı."
            )
        self._auto_timer.setInterval(int(period_ms))
        return True, ""

    @property
    def auto_camera_period_ms(self) -> int:
        return self._auto_timer.interval()

    def _compute_lead_distance_mm(self) -> float:
        """İleri bakış mesafesi: gerçek kesim hızı * (paket periyodu *
        güvenlik payı) - hedefin iletim/PLC gecikmesiyle geride kalmaması
        için (görev notu). Alt sınır MIN_LEAD_DISTANCE_MM: hız çok düşük/0
        olsa da anlamlı bir ileri hedef kalsın."""
        cut_velocity = self._machine.get_parameter_value("lr_x_cut_velocity")
        period_s = self._auto_timer.interval() / 1000.0
        lead = abs(cut_velocity) * period_s * LEAD_MARGIN_PACKET_PERIODS
        return max(MIN_LEAD_DISTANCE_MM, lead)

    def _on_auto_camera_tick(self) -> None:
        if not self.armed or self.source != "SIMULATOR" or not self.auto_camera_active:
            self._stop_auto_camera_internal()
            return
        snap = self._machine.snapshot
        self.last_sensor_hint = sensor_hint(snap.cycle_state)
        if snap.stale:
            return  # görev notu: stale/disconnected veriden hedef üretme

        try:
            state = CycleState(snap.cycle_state)
        except ValueError:
            return

        state_changed = state != self._last_state
        self._last_state = state

        # CutPermit / ZDownRequest - yalnız DEĞİŞTİĞİNDE yaz (görev notu:
        # "CUTTING'de permit/line gereksiz pulse üretme"). WAIT_BLADE_
        # REQUEST'te ZDownRequest, PLC'nin trajectory sonucu doğrulanmadan
        # TRUE yapılmaz; BLADE_DOWN/CUTTING'de zaten verilmiş talebi kısa
        # aralıklarla FALSE'a düşürmeden sabit tutulur (görev notu: "aktif
        # talebi kısa aralıklarla yanlışlıkla FALSE yapma").
        cut_permit = state in _CUT_PERMIT_STATES
        if state == CycleState.WAIT_BLADE_REQUEST:
            z_down = bool(snap.trajectory_valid and not snap.trajectory_fault)
        elif state in (CycleState.BLADE_DOWN, CycleState.CUTTING):
            z_down = True
        else:
            z_down = False

        if cut_permit != self._last_cut_permit:
            self._machine.request_vision_write("vision_cut_permit", cut_permit)
            self._last_cut_permit = cut_permit
        if z_down != self._last_z_down:
            self._machine.request_vision_write("vision_z_down_request", z_down)
            self._last_z_down = z_down

        if state not in _PACKET_STATES or self._send_in_flight:
            return

        needs_packet = (
            state_changed
            or self._last_sent_actual_x is None
            or abs(snap.x_actual_pos - self._last_sent_actual_x) >= PACKET_REFRESH_EPSILON_MM
        )
        if not needs_packet:
            return

        lead = self._compute_lead_distance_mm()
        # Sanal ileri bakış hedefi kasıtlı olarak lrX_CutEndPos'a
        # KIRPILMAZ: TargetX_mm bir trajectory REFERANSIDIR, X motion hedefi
        # değildir - gerçek kesim motion hedefi ayrıca lrX_CutEndPos'tur ve
        # bu paketten etkilenmez (görev notu). Kırpma yapmak, kesim sonuna
        # yaklaşırken hedefX-actualX farkını sıfıra düşürüp trajectory'yi
        # geçersiz kılabilirdi - bu yüzden BİLEREK yapılmıyor.
        target_x = snap.x_actual_pos + lead
        # H6: "eğimli" senaryoda TargetY, TargetX'in bir FONKSİYONUDUR
        # (y=y0+m*(x-x0)) - her pakette sabit artış değil (görev notu).
        # PLC'nin ilk Y hizalama / Follow yükselen kenarında eğimi kendi
        # segment referansına göre sıfırlayabileceği not edildi (görev
        # notu) - bu, HMI'nin göndereceği ideal TargetY'yi değiştirmez,
        # sadece PLC'nin bunu nasıl işlediğini etkiler.
        if self.camera_scenario == "tilted" and self._tilt_reference is not None:
            x0, y0 = self._tilt_reference
            target_y = y0 + self.tilted_slope * (target_x - x0)
        else:
            target_y = self._machine.get_parameter_value("lr_y_center_position")
        ok, _reason = self.send_packet(
            target_x=target_x,
            target_y=target_y,
            vision_ready=True,
            line_valid=True,
            vision_fault=False,
        )
        if ok:
            self._last_sent_actual_x = snap.x_actual_pos
            self.last_target_x = target_x
            self.last_target_y = target_y

    # -- packet (TargetX/TargetY/.. -> sequence, in order) -------------------

    def send_packet(
        self,
        target_x: float,
        target_y: float,
        vision_ready: bool,
        line_valid: bool,
        vision_fault: bool,
        confidence: float | None = None,
    ) -> tuple[bool, str]:
        if not self.armed or self.source != "SIMULATOR":
            return False, "Armed değil."
        if self._send_in_flight:
            return False, "Önceki paket hâlâ gönderiliyor; ikinci paket önce beklemeli."
        if not math.isfinite(target_x) or not math.isfinite(target_y):
            return False, "Hedef X/Y sonlu (finite) bir sayı olmalı (NaN/Inf kabul edilmez)."
        if confidence is not None and (not math.isfinite(confidence) or not (0.0 <= confidence <= 1.0)):
            return False, "Confidence 0..1 aralığında ve sonlu bir sayı olmalı."
        snap = self._machine.snapshot
        if snap.stale:
            return False, "PLC verisi stale; paket gönderilmiyor."
        if not (target_x - snap.x_actual_pos > MIN_TARGET_X_LEAD_MM):
            return False, (
                f"Hedef X ({target_x:g}) güncel X'ten ({snap.x_actual_pos:g}) en az "
                f"{MIN_TARGET_X_LEAD_MM:g} mm ileride olmalı."
            )
        # H6 (2026-09-18): "sınır dışı yolun reddi" - hem düz çizgi hem
        # eğimli senaryoda geçerli. Y yazılım sınırları gerçek PLC
        # okumasından (Settings parametresi) alınır, sabit sayı değil.
        y_min = self._machine.get_parameter_value("lr_y_software_min")
        y_max = self._machine.get_parameter_value("lr_y_software_max")
        if not (y_min <= target_y <= y_max):
            return False, (
                f"Hedef Y ({target_y:g}) Y yazılım sınırlarının ({y_min:g}..{y_max:g}) dışında."
            )

        fields: list[tuple[str, object]] = [
            ("vision_target_x", float(target_x)),
            ("vision_target_y", float(target_y)),
            ("vision_ready", bool(vision_ready)),
            ("line_valid", bool(line_valid)),
            ("vision_fault", bool(vision_fault)),
        ]
        if confidence is not None:
            fields.append(("vision_confidence", float(confidence)))
        next_seq = (self._sequence_value + 1) % UINT32_MOD
        fields.append(("vision_sequence", next_seq))  # EN SON yazılır (görev notu)

        self._send_in_flight = True
        self._pending_generation = self._generation
        self._pending_sequence = next_seq
        dispatched = self._machine.request_vision_sequential_write(fields)
        if not dispatched:
            self._send_in_flight = False
            return False, "Gönderim başlatılamadı (PLC bağlı değil)."
        return True, ""

    def _on_packet_result(self, ok: bool, message: str) -> None:
        if self._pending_generation != self._generation:
            # Önceki bir arm oturumundan kalan gecikmiş sonuç - yok say.
            return
        self._send_in_flight = False
        if ok:
            self._sequence_value = self._pending_sequence
            self.packetResult.emit(True, "")
        else:
            self.last_error = message
            self.lastErrorChanged.emit(message)
            self.packetResult.emit(False, message)

    # -- explicit, single-field operator actions -----------------------------
    # Bıçak talebi (ZDownRequest) ve process permit (CutPermit) sayfaya
    # girişle veya arm ile OTOMATİK oluşmaz; ayrı, açık operatör aksiyonudur
    # (görev notu, Faz 3).

    def send_cut_permit(self, value: bool) -> tuple[bool, str]:
        if not self.armed or self.source != "SIMULATOR":
            return False, "Armed değil."
        self._machine.request_vision_write("vision_cut_permit", bool(value))
        return True, ""

    def send_z_down_request(self, value: bool) -> tuple[bool, str]:
        if not self.armed or self.source != "SIMULATOR":
            return False, "Armed değil."
        self._machine.request_vision_write("vision_z_down_request", bool(value))
        return True, ""
