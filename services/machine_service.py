"""Single, central machine service (brief section 26: "Her sayfada ayrı OPC
UA client oluşturma; tek merkezi service kullan"). Every UI page talks to
this service only — never to `plc.opcua_client` directly.

Owns:
- the OPC UA worker thread when a real endpoint is configured,
- the demo/simulation fallback when it is not (`config/opcua.json` empty
  endpoint => Demo mode, brief acceptance criterion #9),
- the shared MachineSnapshot cache, refreshed to the UI on a fixed timer
  (brief section 20: PLC/vision acquisition can be fast, the operator
  screen only needs 10-20 FPS),
- alarm history and engineering parameter persistence.

UI is never the source of truth: it only requests commands and displays
whatever this service reports (brief section 32).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

from core.cycle_state import AUTO_CYCLE_ACTIVE_STATES, CycleState
from core.models import ConnectionState, MachineSnapshot
from core.parameters import PARAMETER_SPECS
from persistence.alarms import SEVERITY_ALARM, AlarmEvent, AlarmRepository
from persistence.settings_store import SettingsStore
from plc.opcua_client import OpcUaWorker
from plc.tag_map import TagMap, load_config, save_config

logger = logging.getLogger(__name__)

UI_TICK_MS = 50


PARAM_WRITE_CONFIRM_TIMEOUT_S = 2.0

# "Eksenler durmuş" kabulü için actual velocity toleransı (mm/s) - PLC-HMI-
# 20260921-09 ortak izin şartı. vision_simulator.py'deki aynı değerle
# tutarlı tutulur (orada da aynı gerekçeyle kullanılıyor); modüller arası
# bağımlılık kurmamak için burada ayrı bir sabit olarak tutulur.
AXIS_STOPPED_VELOCITY_TOLERANCE = 0.5

# Geçici mühendislik Vision veri simülatörü (PLC-HMI-20260917-02) - kapalı
# izin listesi. Yalnız gerçek kameranın normalde yazdığı Vision->PLC alanları;
# PLC'nin hesapladığı/authoritative state, sensör, motion execute veya valf
# taglarına bu yoldan ASLA yazılmaz (services/vision_simulator.py bu listenin
# dışına çıkamaz - MachineService burada zorunlu kılar).
VISION_SIM_WRITABLE_TAGS = frozenset(
    {
        "vision_ready",
        "line_valid",
        "vision_fault",
        "vision_target_x",
        "vision_target_y",
        "vision_confidence",
        "vision_cut_permit",
        "vision_z_down_request",
        "vision_heartbeat",
        "vision_sequence",
    }
)

# PLC-HMI-20260921-09 (C0.4 takip notu): bıçak/baskı pulse komutlarının
# gerçek OPC UA yazma sonucu, parametre yazmaları gibi UI'ya taşınır (yalnız
# log'a değil) - "yalnız demo testi yeterli değil, gerçek yazma sonucunu
# göster" talebi.
PNEUMATIC_COMMAND_TAGS = frozenset(
    {"cmd_blade_retract", "cmd_clamp_retract", "cmd_blade_down", "cmd_clamp_down"}
)

# PLC-HMI-20260921-10/11 (C5, "Başlangıç Konumuna Dön" tek buton, 3s basılı
# tutuş): aynı "gerçek yazma sonucunu göster" ilkesi bu komut için de geçerli.
MOTION_COMMAND_TAGS = frozenset({"cmd_move_to_start"})


@dataclass(frozen=True)
class _AlarmCondition:
    """PLC-HMI-20260921-16 (C6.1 katalog): HATA sınıfı bildirimlerin PLC
    tarafındaki tek gerçek kaynağı - `MachineSnapshot` üzerindeki bir BOOL
    alan (gerekirse tersiyle, örn. H16: NOT xEmergencyOK). Kesin sensör/parça
    nedeni burada UYDURULMAZ - metinler görev notundaki katalogla birebir."""

    catalog_id: str
    attr: str
    invert: bool
    source: str
    message: str


# H12-H15 (xX_StopError/xY_StopError/xX_AxisError/xY_AxisError) ve H20-H22
# (xAlarmModeChangedDuringCycle/xAlarmClampLostDuringCycle/
# xAlarmBladeNotClearDuringReturn, PLC-HMI-20260922-17) - PLC-HMI-20260922-
# 18 (C06_1 audit) ile export'ta VAR olduğu doğrulandı, yalnız online node/
# erişim testi hâlâ bekliyor (C6.1/C6 aday tag'leri) - config'te eşleme yok,
# bu yüzden ilgili `MachineSnapshot` alanları hep False kalır ve bu maddeler
# online doğrulanana kadar hiç tetiklenmez (C0.4/C5 dersiyle aynı disiplin).
ALARM_CATALOG: tuple[_AlarmCondition, ...] = (
    _AlarmCondition("H01", "alarm_clamp_lost_during_cut", False, "PNEUMATIC", "Kesimde baskı aşağı sensörü kayboldu."),
    _AlarmCondition("H02", "alarm_blade_lost_during_cut", False, "PNEUMATIC", "Kesimde bıçak aşağı sensörü kayboldu."),
    _AlarmCondition("H03", "alarm_clamp_down_timeout", False, "PNEUMATIC", "Baskı belirtilen sürede aşağı konuma ulaşamadı."),
    _AlarmCondition("H04", "alarm_blade_down_timeout", False, "PNEUMATIC", "Bıçak belirtilen sürede aşağı konuma ulaşamadı."),
    _AlarmCondition(
        "H05",
        "move_to_start_error",
        False,
        "X AXIS",
        "Başlangıç konumuna dönüş sırasında arıza oluştu. Eksenlerin durmasını "
        "bekleyin. Bıçak/baskı konumlarını ve eksen arızasını kontrol edin. "
        "Nedeni giderdikten sonra Reset verin. Manuel modda Bıçak Yukarı ve "
        "Baskı Yukarı düğmelerine istediğiniz sırada basın. Açıklıklar "
        "sağlanınca Başlangıç Konumuna Dön düğmesini 3 saniye basılı tutun.",
    ),
    _AlarmCondition("H06", "x_fault", False, "X AXIS", "X servo etkinleştirme hatası."),
    _AlarmCondition("H07", "y_fault", False, "Y AXIS", "Y servo etkinleştirme hatası."),
    _AlarmCondition("H08", "x_cut_error", False, "X AXIS", "X kesim hareketi hatası."),
    _AlarmCondition("H09", "x_return_error", False, "X AXIS", "X dönüş hareketi hatası."),
    _AlarmCondition("H10", "y_move_error", False, "Y AXIS", "Y konumlandırma hatası."),
    _AlarmCondition("H11", "y_follow_error", False, "Y AXIS", "Y takip hareketi hatası."),
    _AlarmCondition("H12", "x_stop_error", False, "X AXIS", "X durdurma bloğu hata verdi. Tam duruşu kontrol edin."),
    _AlarmCondition("H13", "y_stop_error", False, "Y AXIS", "Y durdurma bloğu hata verdi."),
    _AlarmCondition("H14", "x_axis_error", False, "X AXIS", "X eksen/sürücü arıza durumu."),
    _AlarmCondition("H15", "y_axis_error", False, "Y AXIS", "Y eksen/sürücü arıza durumu."),
    _AlarmCondition("H16", "emergency_ok", True, "PLC", "Emniyet geri bildirimi yok. Acil stop/emniyet zincirini kontrol edin."),
    _AlarmCondition("H17", "vision_fault", False, "VISION", "Vision uygulaması arıza bildiriyor."),
    _AlarmCondition("H18", "trajectory_fault", False, "VISION", "Yorumlanan hedef/çizgi geçersiz."),
    _AlarmCondition(
        "H20",
        "alarm_mode_changed_during_cycle",
        False,
        "PLC",
        "Çalışan çevrimde mod değiştirme talebi alındı; makine durduruldu.",
    ),
    _AlarmCondition(
        "H21",
        "alarm_clamp_lost_during_cycle",
        False,
        "PNEUMATIC",
        "Çevrim sırasında baskı aşağı sensörü kayboldu; makine durduruldu.",
    ),
    _AlarmCondition(
        "H22",
        "alarm_blade_not_clear_during_return",
        False,
        "PNEUMATIC",
        "Eksenler dönerken bıçak açıklığı kayboldu; makine durduruldu.",
    ),
)


class MachineService(QObject):
    snapshotUpdated = Signal(MachineSnapshot)
    connectionStateChanged = Signal(str)
    alarmsChanged = Signal()
    parameterWriteConfirmed = Signal(str)
    parameterWriteFailed = Signal(str)
    # 2026-09-18 bug report: "HATA — PLC onaylamadı" tek başına gerçek nedeni
    # gizliyor (Vision paketlerinde aynı sınıf hatayı düzelttik, burada da
    # aynı sorun vardı). Bir yazma OPC UA seviyesinde gerçekten reddedilirse
    # (`errorOccurred`), o an bekleyen parametre yazmasıyla eşleşiyorsa bu
    # sinyal gerçek nedeni taşır; SettingsPage bunu status/uyarıda gösterir.
    parameterWriteError = Signal(str, str)
    # PLC-HMI-20260921-09 takip notu: bıçak/baskı pulse komutlarının (Yukarı/
    # Aşağı) gerçek OPC UA reddi - tag adı + gerçek hata metni. ManualPage bunu
    # gösterir; "gönderildi" iyimserliği tek başına yeterli değil.
    commandWriteError = Signal(str, str)
    visionSequentialWriteResult = Signal(bool, str)

    def __init__(self, config_path=None, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._config = load_config(config_path)
        self._tag_map = TagMap(self._config)
        self._snapshot = MachineSnapshot()
        self._alarms = AlarmRepository()
        self._settings_store = SettingsStore()
        self._worker: OpcUaWorker | None = None

        self.demo_mode = not self._config.is_configured
        self.vision_simulator_enabled = self._config.vision_simulator_enabled

        stored_params = self._settings_store.get_all()
        self._param_cache: dict[str, float] = {
            spec.key: float(stored_params.get(spec.key, spec.default)) for spec in PARAMETER_SPECS
        }
        # Ayarlar ekranı, gerçek PLC değeri gelene kadar bu default/yerel
        # önbellek değerlerini "PLC'den okundu" gibi göstermemeli (2026-09-16
        # düzeltmesi). Demo modda gerçek PLC olmadığı için hepsi baştan
        # "onaylı" sayılır; gerçek modda yalnızca _on_raw_snapshot'ta bir
        # tag fiilen raw içinde görüldüğünde onaylanır.
        self._param_confirmed: set[str] = (
            {spec.key for spec in PARAMETER_SPECS} if self.demo_mode else set()
        )
        # key -> (written_value, monotonic_time_written). A write is only
        # "confirmed" once a later read of the SAME tag actually reports the
        # written value back - not just because we set our own local cache
        # optimistically. Without this, the continuous 100ms read loop can
        # silently overwrite a just-sent value with a stale PLC read that
        # arrived before the PLC processed the write, making a failed write
        # look identical to a slow one (2026-09-16, real-PLC bug report).
        self._param_pending: dict[str, tuple[float, float]] = {}

        # PLC-HMI-20260921-09: "jog requestleri bırakılmış" ortak izin şartı
        # için yerel takip - PLC'ye jog request geri-okuması yapmadan, HMI'nin
        # kendi son gönderdiği durumu (UI thread'de senkron güncellenir).
        self._jog_x_active = False
        self._jog_y_active = False
        # Aynı mekanizmanın Yukarı pulse'u "iş başında" sayılan pencerede
        # (command_pulse_ms) Aşağı'yı reddetmek için - "Yukarı talebi seviyesi
        # TRUE iken Aşağı da reddedilir" (görev notu).
        self._blade_retract_pulse_until = 0.0
        self._clamp_retract_pulse_until = 0.0

        # PLC-HMI-20260921-10/11 (C5): "yeni isteğin readback geçişlerini
        # izle, belirsizse tamamlandı iddia etme" - bir pulse gönderdikten
        # sonra Done/Aborted/Error'ın ESKİ (önceki komuttan kalma, latched)
        # değerini yeni komutun sonucu saymamak için basit bir yükselen-kenar
        # takibi. "cleared" = pulse'tan SONRA en az bir kez ya Busy TRUE
        # görüldü ya da üçü de FALSE görüldü (PLC eski latch'i temizledi) -
        # ancak o noktadan sonra bir Done/Aborted/Error TRUE'su güvenilir.
        self._move_to_start_sent = False
        self._move_to_start_cleared = False
        self._move_to_start_status = "idle"

        # PLC-HMI-20260921-16 (C6.1): katalog kimliği -> o an açık olan
        # AlarmEvent'in id'si. Bir HATA koşulu ilk kez TRUE görüldüğünde
        # (rising edge) buraya eklenir ve AlarmRepository'ye bir kez yazılır;
        # PLC'nin kendi okuması FALSE'a döndüğünde (falling edge - HMI'nin
        # Reset tıklamasıyla DEĞİL) buradan çıkarılır ve o kayıt kapatılır.
        self._active_alarm_events: dict[str, int] = {}
        # PLC-HMI-20260922-18 (HMI-A02): yukarıdaki dict RAM'de başlar - her
        # yeniden başlatmada boş, ama alttaki SQLite kalıcı. İlk gerçek koşul
        # değerlendirmesinden önce DB'deki hâlâ açık kayıtlarla bir kez
        # uzlaştırılır (`_reconcile_alarm_state_with_persisted_events`).
        self._alarm_state_reconciled = False

        from services.demo_simulator import DemoSimulator

        self._demo: DemoSimulator | None = DemoSimulator() if self.demo_mode else None
        if self._demo is not None:
            self._demo.params.update(self._param_cache)
            self._demo.apply_initial(self._snapshot)

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._on_tick)

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        if self.demo_mode:
            self._snapshot.connection_state = ConnectionState.DEMO
            self._snapshot.stale = False
            self.connectionStateChanged.emit(ConnectionState.DEMO)
        else:
            self._worker = OpcUaWorker(self._config, self._tag_map)
            self._worker.snapshotReady.connect(self._on_raw_snapshot)
            self._worker.connectionStateChanged.connect(self._on_connection_state)
            self._worker.errorOccurred.connect(self._on_error)
            self._worker.sequentialWriteResult.connect(self.visionSequentialWriteResult)
            self._worker.start()
        self._ui_timer.start(UI_TICK_MS)

    def shutdown(self) -> None:
        self._ui_timer.stop()
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(2000)

    @property
    def snapshot(self) -> MachineSnapshot:
        return self._snapshot

    @property
    def endpoint(self) -> str:
        return self._config.endpoint

    # -- PLC state ingestion (real mode) -----------------------------------

    def _on_connection_state(self, state: str) -> None:
        self._snapshot.connection_state = state
        self.connectionStateChanged.emit(state)

    def _on_error(self, message: str) -> None:
        logger.warning("PLC error: %s", message)
        # `_write_checked` mesaj biçimi: "Write failed for '<tag>': <sebep>".
        # O tag şu an bekleyen bir parametre yazmasıysa gerçek sebebi ayrı
        # bir sinyalle taşı - Settings ekranı jenerik timeout mesajı yerine
        # (veya yanında) bunu gösterebilsin.
        match = re.match(r"Write failed for '([^']+)': (.*)", message)
        if match:
            key, reason = match.group(1), match.group(2)
            if key in self._param_pending:
                self.parameterWriteError.emit(key, reason)
            elif key in PNEUMATIC_COMMAND_TAGS or key in MOTION_COMMAND_TAGS:
                if key == "cmd_move_to_start":
                    # PLC hiç görmediyse Busy/Done/Aborted/Error asla
                    # değişmeyecek - "sent" durumunda sonsuza dek asılı
                    # kalmak yerine bunu da gerçek bir "error" say.
                    self._move_to_start_sent = False
                    self._move_to_start_status = "error"
                self.commandWriteError.emit(key, reason)

    def _on_raw_snapshot(self, raw: dict) -> None:
        snap = self._snapshot
        snap.timestamp = time.monotonic()
        snap.stale = False

        def b(name: str, default: bool) -> bool:
            v = raw.get(name)
            return bool(v) if v is not None else default

        def f(name: str, default: float) -> float:
            v = raw.get(name)
            return float(v) if v is not None else default

        def i(name: str, default: int) -> int:
            v = raw.get(name)
            return int(v) if v is not None else default

        snap.machine_ready = b("machine_ready", snap.machine_ready)
        snap.manual_mode = b("manual_mode", snap.manual_mode)
        snap.auto_mode = not snap.manual_mode
        snap.cycle_state = i("cycle_state", snap.cycle_state)
        snap.cut_active = b("cut_active", snap.cut_active)
        snap.emergency_active = b("emergency_active", snap.emergency_active)
        # PLC-HMI-20260921-09: manuel bıçak/baskı "ortak izin" şartları.
        snap.emergency_ok = b("emergency_ok", snap.emergency_ok)
        snap.alarm_stop_request = b("alarm_stop_request", snap.alarm_stop_request)
        snap.motion_stop = b("motion_stop", snap.motion_stop)
        snap.manual_preparation_required = b(
            "manual_preparation_required", snap.manual_preparation_required
        )
        # PLC-HMI-20260921-16 (C6.1): C0.3 pnömatik alarm bitleri - latched,
        # yalnız gerçek xAlarmResetAccepted ile FALSE olurlar.
        snap.alarm_clamp_lost_during_cut = b(
            "alarm_clamp_lost_during_cut", snap.alarm_clamp_lost_during_cut
        )
        snap.alarm_blade_lost_during_cut = b(
            "alarm_blade_lost_during_cut", snap.alarm_blade_lost_during_cut
        )
        snap.alarm_clamp_down_timeout = b(
            "alarm_clamp_down_timeout", snap.alarm_clamp_down_timeout
        )
        snap.alarm_blade_down_timeout = b(
            "alarm_blade_down_timeout", snap.alarm_blade_down_timeout
        )
        # PLC-HMI-20260921-10/11 (C5): "Başlangıç Konumuna Dön" salt okunur
        # durumu. Allowed PLC'nin nihai izni - HMI bunu yeniden üretmez.
        snap.move_to_start_allowed = b("move_to_start_allowed", snap.move_to_start_allowed)
        snap.move_to_start_busy = b("move_to_start_busy", snap.move_to_start_busy)
        snap.move_to_start_done = b("move_to_start_done", snap.move_to_start_done)
        snap.move_to_start_aborted = b("move_to_start_aborted", snap.move_to_start_aborted)
        snap.move_to_start_error = b("move_to_start_error", snap.move_to_start_error)
        self._update_move_to_start_status(snap)

        # xCycleActive and xStartPermitted are real, authoritative PLC tags
        # (2026-09-16 duzeltmesi) - HMI reads them, it does not recompute
        # them. PLC's xStartPermitted formula (for reference only, NOT
        # duplicated here): MachineReady AND NOT xManualMode AND NOT
        # xCycleActive AND xX_AtStart AND xY_AtCenter.
        snap.cycle_active = b("cycle_active", snap.cycle_active)
        snap.start_permitted = b("start_permitted", snap.start_permitted)

        # X/Y servo ready is derived from two separate PLC bits (görev planı §3).
        x_power_status = b("x_power_status", snap.x_servo_ready)
        x_power_error = b("x_power_error", snap.x_fault)
        snap.x_servo_ready = x_power_status and not x_power_error
        snap.x_fault = x_power_error
        snap.x_fault_code = i("x_fault_code", snap.x_fault_code)
        snap.x_actual_pos = f("x_actual_pos", snap.x_actual_pos)
        snap.x_actual_vel = f("x_actual_vel", snap.x_actual_vel)
        snap.x_at_start = b("x_at_start", snap.x_at_start)  # diagnostic only
        snap.x_cut_error = b("x_cut_error", snap.x_cut_error)
        snap.x_return_error = b("x_return_error", snap.x_return_error)
        snap.x_stop_error = b("x_stop_error", snap.x_stop_error)
        snap.x_axis_error = b("x_axis_error", snap.x_axis_error)

        y_power_status = b("y_power_status", snap.y_servo_ready)
        y_power_error = b("y_power_error", snap.y_fault)
        snap.y_servo_ready = y_power_status and not y_power_error
        snap.y_fault = y_power_error
        snap.y_fault_code = i("y_fault_code", snap.y_fault_code)
        snap.y_move_error = b("y_move_error", snap.y_move_error)
        snap.y_follow_error = b("y_follow_error", snap.y_follow_error)
        snap.y_stop_error = b("y_stop_error", snap.y_stop_error)
        snap.y_axis_error = b("y_axis_error", snap.y_axis_error)
        snap.operator_stop_active = b("operator_stop_active", snap.operator_stop_active)
        # PLC-HMI-20260922-17 (C6 toplu teslim): 3 yeni aday latched HATA -
        # config'te eşleme olmadığı sürece hep False (H20-H22, ALARM_CATALOG).
        snap.alarm_mode_changed_during_cycle = b(
            "alarm_mode_changed_during_cycle", snap.alarm_mode_changed_during_cycle
        )
        snap.alarm_clamp_lost_during_cycle = b(
            "alarm_clamp_lost_during_cycle", snap.alarm_clamp_lost_during_cycle
        )
        snap.alarm_blade_not_clear_during_return = b(
            "alarm_blade_not_clear_during_return", snap.alarm_blade_not_clear_during_return
        )
        snap.y_actual_pos = f("y_actual_pos", snap.y_actual_pos)
        snap.y_actual_vel = f("y_actual_vel", snap.y_actual_vel)
        snap.y_set_pos = f("y_set_pos", snap.y_set_pos)
        snap.y_set_vel = f("y_set_vel", snap.y_set_vel)
        snap.y_at_center = b("y_at_center", snap.y_at_center)  # diagnostic only

        # ClampDown/BladeZDown are single PLC bits now; the "up" counterpart
        # is derived, not a separate sensor tag.
        snap.clamp_down = b("clamp_down", snap.clamp_down)
        snap.clamp_up = not snap.clamp_down
        snap.blade_down = b("blade_down", snap.blade_down)
        snap.blade_up = not snap.blade_down
        # PLC-üretimli, salt okunur - HMI yazmaz (PLC-HMI-20260918-06).
        snap.blade_retract_accepted = b("blade_retract_accepted", snap.blade_retract_accepted)
        snap.clamp_retract_accepted = b("clamp_retract_accepted", snap.clamp_retract_accepted)

        snap.feed_forward_input = b("feed_forward_input", snap.feed_forward_input)
        snap.feed_reverse_input = b("feed_reverse_input", snap.feed_reverse_input)
        snap.feed_running = b("feed_active", snap.feed_running)
        snap.feed_complete = b("feed_complete", snap.feed_complete)
        snap.feed_manual_allowed = b("feed_manual_allowed", snap.feed_manual_allowed)
        snap.vision_ready = b("vision_ready", snap.vision_ready)
        snap.line_valid = b("line_valid", snap.line_valid)
        snap.vision_fault = b("vision_fault", snap.vision_fault)
        snap.vision_heartbeat_ok = b("vision_heartbeat_ok", snap.vision_heartbeat_ok)
        snap.trajectory_fault = b("trajectory_fault", snap.trajectory_fault)
        snap.trajectory_valid = b("trajectory_valid", snap.trajectory_valid)
        snap.lr_max_allowed_slope = f("lr_max_allowed_slope", snap.lr_max_allowed_slope)
        snap.vision_target_x = f("vision_target_x", snap.vision_target_x)
        snap.vision_target_y = f("vision_target_y", snap.vision_target_y)
        snap.vision_confidence = f("vision_confidence", snap.vision_confidence)
        snap.vision_slope = f("vision_slope", snap.vision_slope)
        snap.vision_cut_permit = b("vision_cut_permit", snap.vision_cut_permit)
        snap.vision_z_down_request = b("vision_z_down_request", snap.vision_z_down_request)
        snap.vision_heartbeat = i("vision_heartbeat", snap.vision_heartbeat)
        snap.vision_sequence = i("vision_sequence", snap.vision_sequence)
        snap.alarm_active = b("alarm_active", snap.alarm_active)
        snap.alarm_code = i("alarm_code", snap.alarm_code)
        snap.alarm_count = i("alarm_count", snap.alarm_count)

        # Kesim ilerlemesi ayrı bir PLC tagı değil; 2026-09-16'da onaylanan
        # kesin formülle türetiliyor: (ActualX_mm - lrX_CutStartPos) /
        # (CutEndX_mm - lrX_CutStartPos), %0-100 clamp. CutEndX_mm çalışma
        # zamanı (Vision) değeridir; lrX_CutStartPos ayarlar parametresidir
        # ("lr_x_cut_start_pos" anahtarıyla okunur).
        cut_start = raw.get("lr_x_cut_start_pos")
        cut_end = raw.get("cut_end_x")
        if cut_start is not None and cut_end is not None:
            span = float(cut_end) - float(cut_start)
            if span:
                progress = 100.0 * (snap.x_actual_pos - float(cut_start)) / span
                snap.cycle_progress = max(0.0, min(100.0, progress))

        for spec in PARAMETER_SPECS:
            if spec.key not in raw:
                continue
            read_value = float(raw[spec.key])
            self._param_confirmed.add(spec.key)

            pending = self._param_pending.get(spec.key)
            if pending is None:
                self._param_cache[spec.key] = read_value
                continue
            written_value, written_at = pending
            if abs(read_value - written_value) < 1e-6:
                self._param_cache[spec.key] = read_value
                del self._param_pending[spec.key]
                self.parameterWriteConfirmed.emit(spec.key)
            elif time.monotonic() - written_at > PARAM_WRITE_CONFIRM_TIMEOUT_S:
                # PLC never echoed the written value back - treat as a
                # failed write and trust what the PLC actually reports,
                # rather than keep showing our own optimistic guess.
                self._param_cache[spec.key] = read_value
                del self._param_pending[spec.key]
                self.parameterWriteFailed.emit(spec.key)
            # else: still within the confirmation window - keep the
            # optimistic value in _param_cache (set by set_parameter) so the
            # UI doesn't flicker back to the old value while we wait.

        self._update_alarm_conditions(snap)

    def _update_alarm_conditions(self, snap: MachineSnapshot) -> None:
        """PLC-HMI-20260921-16 (C6.1): HATA sınıfı bildirimleri PLC'nin
        kendi latched bitlerinden üretir. Rising edge'de (koşul ilk kez
        TRUE görülür) `AlarmRepository`'ye BİR KEZ yazılır; falling edge'de
        (PLC'nin kendi okuması FALSE'a döner - HMI'nin Reset'e tıklamasıyla
        DEĞİL) yalnız O kayıt kapatılır. İlk okuma zaten TRUE ise (örn.
        bağlantı/reconnect sonrası) yine aktif listede görünür - bu bir
        kayıp değil, doğru davranıştır."""
        if not self._alarm_state_reconciled:
            self._reconcile_alarm_state_with_persisted_events()
            self._alarm_state_reconciled = True

        changed = False
        known_cause_active = False
        for cond in ALARM_CATALOG:
            value = getattr(snap, cond.attr)
            active = (not value) if cond.invert else value
            if active:
                known_cause_active = True
            is_open = cond.catalog_id in self._active_alarm_events
            if active and not is_open:
                event = self._alarms.log_event(
                    SEVERITY_ALARM, cond.source, cond.message, catalog_id=cond.catalog_id
                )
                self._active_alarm_events[cond.catalog_id] = event.id
                changed = True
            elif not active and is_open:
                self._alarms.clear_event(self._active_alarm_events.pop(cond.catalog_id))
                changed = True

        # H19: FAULT'tayken yukarıdaki bilinen nedenlerin hiçbiri aktif
        # değilse jenerik yedek mesaj - sahte bir neden uydurmak yerine.
        # Bilinen bir neden VARSA burada ikinci kez saydırılmaz.
        fault_no_known_cause = snap.cycle_state == int(CycleState.FAULT) and not known_cause_active
        is_h19_open = "H19" in self._active_alarm_events
        if fault_no_known_cause and not is_h19_open:
            event = self._alarms.log_event(
                SEVERITY_ALARM,
                "PLC",
                "PLC arıza durumunda; ayrıntılı neden bilgisi mevcut değil.",
                catalog_id="H19",
            )
            self._active_alarm_events["H19"] = event.id
            changed = True
        elif not fault_no_known_cause and is_h19_open:
            self._alarms.clear_event(self._active_alarm_events.pop("H19"))
            changed = True

        if changed:
            self.alarmsChanged.emit()

    def _reconcile_alarm_state_with_persisted_events(self) -> None:
        """PLC-HMI-20260922-18 (HMI-A02, C06_1 audit): `_active_alarm_events`
        RAM'de her yeniden başlatmada boş başlar ama alttaki SQLite kalıcı.
        Uzlaştırma olmadan: (a) önceki oturumdan kalan hâlâ-açık bir kayıt,
        PLC şimdi FALSE okusa bile hiç kapanmaz (servis onun varlığından
        habersiz - falling edge asla tetiklenmez, kayıt sonsuza dek "aktif"
        görünür); (b) koşul hâlâ TRUE ise ikinci bir kopya kayıt açılır.
        İlk gerçek koşul değerlendirmesinden ÖNCE, bir kez çağrılır: DB'deki
        hâlâ açık VE bir catalog_id taşıyan kayıtlar belleğe geri yüklenir.
        DB'ye hiçbir YENİ satır yazılmaz - yalnız eski bug'lardan kalma
        (aynı catalog_id için birden fazla açık kayıt) varsa en yenisi
        tutulur, geri kalanı `clear_event` ile kapatılır (SİLİNMEZ,
        yalnız cleared_at set edilir - geçmiş korunur)."""
        seen: set[str] = set()
        for event in self._alarms.open_catalog_events():  # en yeniden en eskiye
            if event.catalog_id in seen:
                self._alarms.clear_event(event.id)
                continue
            seen.add(event.catalog_id)
            self._active_alarm_events[event.catalog_id] = event.id

    def active_alarm_count(self) -> int:
        """C6.1: ana ekranın ALARM sayacı, hayali `MachineSnapshot.alarm_
        count`'a değil, gerçek aktif HATA kayıtlarına dayanır (Uyarı/Mesaj
        sayılmaz). PLC-HMI-20260922-18 (HMI-A02): `recent(limit=100)`
        DEĞİL, sınırsız `active_events()` - 100+ geçmiş kayıt varken bile
        aktif bir HATA gizlenmez."""
        return sum(1 for e in self._alarms.active_events() if e.severity == SEVERITY_ALARM)

    # H06/H07'nin `MachineSnapshot` alanı (`x_fault`/`y_fault`) türetilmiş -
    # gerçek config anahtarı `x_power_error`/`y_power_error`'dır (bkz.
    # `_on_raw_snapshot`: `snap.x_fault = x_power_error`). Diğer tüm katalog
    # `attr`'ları config anahtarıyla birebir aynı isimdedir.
    _CATALOG_ATTR_TO_CONFIG_KEY = {"x_fault": "x_power_error", "y_fault": "y_power_error"}

    def pending_candidate_catalog_ids(self) -> list[str]:
        """PLC-HMI-20260922-18 (HMI-A04, C06_1 audit): hangi H/U kodlarının
        gerçek `config/opcua.json`'da HENÜZ bir NodeId eşlemesi olmadığını
        (bu yüzden hiç tetiklenemeyeceğini) döndürür - config'ten canlı
        okunur, statik bir metne bağlı değildir; PLC online doğrulayıp
        gerçek config'e eklendiği an otomatik listeden düşer. Katalogdaki
        her giriş kendi config anahtarının config'te olup olmadığıyla
        kontrol edilir - H01-H11/H16-H19 zaten eşlenmiş olduğu için listeye
        hiç girmez, yalnız gerçek adaylar (H12-H15/H20-H22) çıkar. U06
        (operator_stop_active) ALARM_CATALOG'da değildir (bir UYARI, HATA
        değil), ayrıca kontrol edilir."""
        if self.demo_mode:
            return []
        ids = [
            cond.catalog_id
            for cond in ALARM_CATALOG
            if self._CATALOG_ATTR_TO_CONFIG_KEY.get(cond.attr, cond.attr) not in self._config.nodes
        ]
        if "operator_stop_active" not in self._config.nodes:
            ids.append("U06")
        return ids

    def active_alarms(self) -> list[AlarmEvent]:
        """PLC-HMI-20260922-18 (HMI-A02): "Güncel Alarmlar" ve ana ekranın
        Hata/Uyarı/Mesaj panosu için - `recent_alarms()`'ın aksine (geçmiş
        görünümü, son 100 ile sınırlı) burada bir üst sınır YOK."""
        return self._alarms.active_events()

    def _update_move_to_start_status(self, snap: MachineSnapshot) -> None:
        """PLC-HMI-20260921-11: "yeni isteğin readback geçişlerini izle,
        belirsizse tamamlandı iddia etme". Bir pulse gönderilmemişse (`_move_
        to_start_sent` False) hiçbir şey yapmaz - Done/Aborted/Error'ın eski,
        önceki komuttan kalma (latched) değeri asla yeni bir sonuç olarak
        yorumlanmaz. Gönderim sonrası önce "cleared" (PLC eski latch'i
        gerçekten temizledi - ya Busy TRUE görüldü ya da üçü de FALSE
        görüldü) beklenir; ancak ondan sonra bir Done/Aborted/Error TRUE'su
        BU isteğin sonucu sayılır.

        PLC-HMI-20260921-13 düzeltmesi (gerçek PLC'de yakalanan bir kullanıcı
        senaryosu): PLC, MANUAL_RETURN_STOP'ta dururken Busy=TRUE ile
        AYNI ANDA Aborted=TRUE de tutabiliyor - bu ara/duruş evresi, terminal
        bir sonuç değil. Busy TRUE olduğu SÜRECE Done/Aborted/Error'a hiç
        bakılmaz (isteğin takibi de kapanmaz) - "REDDEDİLDİ" gibi bitmiş bir
        sonuç, makine hâlâ meşgulken asla gösterilmez.

        PLC-HMI-20260921-14: Busy+Aborted birlikteyse ayrı bir "stopping"
        durumu ("Dönüş durduruluyor") - salt Busy'den (MANUAL_RETURN, 130,
        hedefe doğru hareket) ayırt edilir; Busy+Aborted MANUAL_RETURN_STOP
        (140)'a karşılık gelir. Terminal sonuçlarda Error önceliklidir -
        kaynakta talep reddi ile iptal aynı bitten geldiği için Aborted TEK
        BAŞINA ayrıştırılamaz ("talep reddedildi VEYA dönüş iptal edildi")."""
        if not self._move_to_start_sent:
            return
        if not self._move_to_start_cleared:
            if snap.move_to_start_busy or not (
                snap.move_to_start_done or snap.move_to_start_aborted or snap.move_to_start_error
            ):
                self._move_to_start_cleared = True
        if not self._move_to_start_cleared:
            return
        if snap.move_to_start_busy:
            self._move_to_start_status = "stopping" if snap.move_to_start_aborted else "busy"
            return
        if snap.move_to_start_error:
            self._move_to_start_status = "error"
        elif snap.move_to_start_done:
            self._move_to_start_status = "done"
        elif snap.move_to_start_aborted:
            self._move_to_start_status = "aborted"
        else:
            return  # Busy az önce kalktı, henüz bir sonuç okunmadı - bekle.
        self._move_to_start_sent = False

    def _on_tick(self) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.tick(UI_TICK_MS / 1000.0, self._snapshot, self._alarms, self.alarmsChanged.emit)
            self._update_move_to_start_status(self._snapshot)
            self._update_alarm_conditions(self._snapshot)
        else:
            age_ms = (time.monotonic() - self._snapshot.timestamp) * 1000
            self._snapshot.stale = age_ms > self._config.stale_timeout_ms
        self.snapshotUpdated.emit(self._snapshot)

    # -- commands (called from the UI thread) ------------------------------

    def _manual_allowed(self) -> bool:
        # PLC-HMI-20260921-10: "Başlangıç Konumuna Dön" hareketi xCycleActive
        # DEĞİL (otomatik çevrim sayılmaz) - bu yüzden PLC'nin kendi cycle
        # kilidi bunu kapsamaz; HMI Busy'yi burada AYRICA kilitler.
        if self._snapshot.move_to_start_busy:
            return False
        try:
            state = CycleState(self._snapshot.cycle_state)
        except ValueError:
            return self._snapshot.manual_mode
        return self._snapshot.manual_mode and state not in AUTO_CYCLE_ACTIVE_STATES

    def request_start(self) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.request_start()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_start")

    def request_stop(self) -> None:
        # Yalnizca GVL.Stop'a pulse gonderir; baska hicbir state/motion
        # tagina dokunmaz (Faz 2, 2026-09-16).
        if self.demo_mode and self._demo is not None:
            self._demo.request_stop()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_stop")

    def request_reset(self) -> None:
        # Yalnizca GVL.Reset'e pulse gonderir; xAxisReset/xMotionStop/
        # eMachineState gibi internal taglara HMI dokunmaz (Faz 2).
        if self.demo_mode and self._demo is not None:
            self._demo.request_reset()
            return
        if self._worker is not None:
            self._worker.request_pulse("cmd_reset")
        # PLC-HMI-20260921-16 (C6.1 bulgusu, gerçek hata): burada ARTIK
        # `_alarms.clear_active()` çağrılmıyor. Reset kabul edilmeden aktif
        # hata ekrandan kaybolmamalı - temizlik yalnızca PLC'nin kendi
        # readback'i (alarm biti gerçekten FALSE okunduğunda) ile olur,
        # `_update_alarm_conditions`'ta ele alınır.
        self.alarmsChanged.emit()

    def _mode_change_allowed(self) -> bool:
        """H2 (2026-09-18, kullanıcı test notu): "otomatik mod aktifken ve
        kesim devam ederken Manuel Modu Etkinleştir butonu aktif kalıyor,
        disable olmalı." UI tarafı (ManualPage) zaten butonu görsel olarak
        engelliyor; bu, çağrının UI dışından (veya devre dışı bir butondan
        gecikmeli sinyalle) gelmesi durumunda da GERÇEK engeldir. Stale/
        bağlantısız/bilinmeyen durumda fail-closed - PLC'nin gerçek modunu
        bilmeden yazma yapılmaz."""
        snap = self._snapshot
        if snap.stale:
            return False
        if not self.demo_mode and snap.connection_state != ConnectionState.CONNECTED:
            return False
        # PLC-HMI-20260921-10: move-to-start busy'de mod değişimi de kilitli
        # (xCycleActive bunu kapsamaz, ayrıca kontrol edilir).
        return not snap.cycle_active and not snap.move_to_start_busy

    def set_manual_mode(self, manual: bool) -> None:
        """xManualMode: TRUE=MANUAL, FALSE=AUTO. Duz yazma, pulse degil -
        PLC bunu bir R_TRIG ile degil dogrudan mod biti olarak okuyor."""
        if not self._mode_change_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.set_mode(not manual)
        elif self._worker is not None:
            self._worker.request_write("manual_mode", manual)

    def jog_x(self, direction: int, active: bool) -> None:
        if active and not self._manual_allowed():
            return
        self._jog_x_active = active
        if self.demo_mode and self._demo is not None:
            self._demo.set_jog_x(direction, active)
        elif self._worker is not None:
            # Kullanıcı isteği (2026-09-21): ayrı "JOG Yavaş/Hızlı" seçimi
            # kaldırıldı - gerçek jog hızı artık doğrudan PLC parametresinden
            # (`lr_x_jog_velocity`) geliyor, Manuel sayfasında düzenlenebilir.
            tag = "jog_x_plus_request" if direction > 0 else "jog_x_minus_request"
            self._worker.request_write(tag, active)

    def jog_y(self, direction: int, active: bool) -> None:
        if active and not self._manual_allowed():
            return
        self._jog_y_active = active
        if self.demo_mode and self._demo is not None:
            self._demo.set_jog_y(direction, active)
        elif self._worker is not None:
            tag = "jog_y_plus_request" if direction > 0 else "jog_y_minus_request"
            self._worker.request_write(tag, active)

    def release_all_jog(self) -> None:
        """Guvenlik: buton birakildiginda, pencere odagi kaybedildiginde
        veya Manuel sayfasindan cikildiginda tum jog request tag'lerini
        FALSE'a ceker. manual_allowed kontrolune tabi degildir - birakma
        her zaman calismalidir."""
        self._jog_x_active = False
        self._jog_y_active = False
        if self.demo_mode and self._demo is not None:
            self._demo.set_jog_x(0, False)
            self._demo.set_jog_y(0, False)
            return
        if self._worker is None:
            return
        for tag in (
            "jog_x_plus_request",
            "jog_x_minus_request",
            "jog_y_plus_request",
            "jog_y_minus_request",
        ):
            self._worker.request_write(tag, False)

    def y_center(self) -> None:
        if not self._manual_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.request_y_center()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_y_center")

    def _pneumatic_common_allowed(self) -> bool:
        """PLC-HMI-20260921-09 "ortak izin": bıçak/baskı Yukarı VE Aşağı
        pulse butonlarının paylaştığı ön koşul (eskiden yalnız `_manual_
        allowed()` kullanılıyordu - bu tag'lerin fiziksel bir valfi tetiklemesi
        nedeniyle şimdi daha eksiksiz kontrol edilir). HMI yalnız gördüğü
        kadarını kontrol eder; fiziksel Stop/bazı PLC iç hesapları tam
        yayınlı değil - PLC'nin kendi kabul/red kararı esastır, bu yalnız
        erken/görsel bir engeldir."""
        snap = self._snapshot
        if snap.stale:
            return False
        if not self.demo_mode and snap.connection_state != ConnectionState.CONNECTED:
            return False
        try:
            state = CycleState(snap.cycle_state)
        except ValueError:
            return False
        if state != CycleState.MANUAL or not snap.manual_mode:
            return False
        if not snap.emergency_ok or snap.alarm_stop_request or snap.motion_stop:
            return False
        if abs(snap.x_actual_vel) > AXIS_STOPPED_VELOCITY_TOLERANCE:
            return False
        if abs(snap.y_actual_vel) > AXIS_STOPPED_VELOCITY_TOLERANCE:
            return False
        if self._jog_x_active or self._jog_y_active:
            return False
        # PLC-HMI-20260921-10: move-to-start busy'de pnömatik de kilitli.
        if snap.move_to_start_busy:
            return False
        # PLC-HMI-20260922-18 (HMI-A06, C06_1 audit): "PLC reddetse de HMI
        # butonu açık kalabilir" - operator_stop_active aday tag (U06),
        # gerçek config'e eklenene kadar hep False (C0.4/C5 disiplini) -
        # bu satır online doğrulanana kadar hiçbir şeyi etkilemez, yalnız
        # tag geldiğinde otomatik aktive olur.
        if snap.operator_stop_active:
            return False
        return True

    def _settings_write_allowed(self) -> bool:
        """PLC-HMI-20260922-18 (HMI-A01, C06_1 audit): mühendislik ayar
        yazmalarının (`set_parameter`) paylaştığı ortak izin - `_pneumatic_
        common_allowed`'la aynı disiplin, ayarlar için: veri taze/bağlı
        olmalı, otomatik çevrim aktif olmamalı, jog talebi veya gerçek eksen
        hareketi sürmemeli. C5 (move_to_start_busy) `set_parameter`'da ayrı,
        özel bir mesajla zaten kontrol ediliyor - burada TEKRAR edilmez."""
        snap = self._snapshot
        # Demo modda gerçek bir bağlantı/tazelik kavramı yok (görev notu:
        # "gerçek modda taze/bağlı") - `.start()` çağrılmadan (birçok testte
        # olduğu gibi) `stale` varsayılanı hep True kalır; bu iki şart yalnız
        # gerçek modda anlamlıdır. cycle_active/jog/eksen hareketi HER İKİ
        # modda da kontrol edilir (demo simülatörü de bunları üretebilir).
        if not self.demo_mode:
            if snap.stale:
                return False
            if snap.connection_state != ConnectionState.CONNECTED:
                return False
        if snap.cycle_active:
            return False
        if self._jog_x_active or self._jog_y_active:
            return False
        if abs(snap.x_actual_vel) > AXIS_STOPPED_VELOCITY_TOLERANCE:
            return False
        if abs(snap.y_actual_vel) > AXIS_STOPPED_VELOCITY_TOLERANCE:
            return False
        return True

    def _manual_down_extra_allowed(self) -> bool:
        """Aşağı için ek şart (Yukarı'da aranmaz): hazırlıkta Aşağı pasif
        kalmalı, fiziksel besleme pushbuttonları/komutu kapalı olmalı."""
        snap = self._snapshot
        if snap.manual_preparation_required:
            return False
        if snap.feed_forward_input or snap.feed_reverse_input or snap.feed_running:
            return False
        return True

    def _tags_configured(self, *names: str) -> bool:
        """Demo modda taglar anlamsız (gerçek node yok, her zaman True).
        Gerçek modda: `config/opcua.json` içinde bu isimlerin HEPSİ için bir
        NodeId eşlemesi var mı? PLC-HMI-20260921-09 C0.4 takip notu: "eksik
        tag varken butonu etkinleştirme" - Aşağı taleplerinin hem kendi pulse
        tag'i hem paylaştığı ortak-izin okumaları (alarm_stop_request,
        manual_preparation_required) burada zorunlu tutulur."""
        if self.demo_mode:
            return True
        return all(name in self._config.nodes for name in names)

    def blade_down_tags_configured(self) -> bool:
        return self._tags_configured("cmd_blade_down", "alarm_stop_request", "manual_preparation_required")

    def clamp_down_tags_configured(self) -> bool:
        return self._tags_configured("cmd_clamp_down", "alarm_stop_request", "manual_preparation_required")

    def manual_pneumatic_allowed(self) -> bool:
        """Public: UI'nin Yukarı (Geri Çek) butonlarını göstermek için
        kullandığı tek kaynak - mantık burada tekrar edilmesin."""
        return self._pneumatic_common_allowed()

    def manual_blade_down_allowed(self) -> bool:
        return (
            self.blade_down_tags_configured()
            and self._pneumatic_common_allowed()
            and self._manual_down_extra_allowed()
        )

    def manual_clamp_down_allowed(self) -> bool:
        return (
            self.clamp_down_tags_configured()
            and self._pneumatic_common_allowed()
            and self._manual_down_extra_allowed()
        )

    def request_blade_retract(self) -> bool:
        """GVL.xBladeRetractRequest: pulse (TRUE~150ms~FALSE), PLC-HMI-
        20260918-06. PLC kabulü `blade_retract_accepted` readback'inden
        okunur, bu yazının başarısı (dönen True) kabul kanıtı değildir -
        yalnız pulse'ın gönderime kalktığını gösterir; gerçek OPC UA reddi
        `commandWriteError` ile ayrıca gelir."""
        if not self._pneumatic_common_allowed():
            return False
        self._blade_retract_pulse_until = time.monotonic() + self._config.command_pulse_ms / 1000
        if self.demo_mode and self._demo is not None:
            self._demo.request_blade_retract()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_blade_retract")
        else:
            return False
        return True

    def request_clamp_retract(self) -> bool:
        """GVL.xClampRetractRequest - bkz. request_blade_retract() notu."""
        if not self._pneumatic_common_allowed():
            return False
        self._clamp_retract_pulse_until = time.monotonic() + self._config.command_pulse_ms / 1000
        if self.demo_mode and self._demo is not None:
            self._demo.request_clamp_retract()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_clamp_retract")
        else:
            return False
        return True

    def request_blade_down(self) -> bool:
        """GVL.xBladeDownRequest (YENİ, PLC-HMI-20260921-09): pulse. PLC'de
        bu talep için ayrı bir "kabul" biti YOK (görev notu, bilinçli) -
        gönderim fiziksel konum kanıtı değildir, yalnız Sensör (BladeZDown)
        gerçek durumu gösterir. Aynı mekanizmanın Yukarı pulse'u hâlâ iş
        başındaysa (command_pulse_ms penceresi) reddedilir - Yukarı öncelikli.
        Tag eksikse (config'te yok) hiç denemez - dönen False, UI'nin
        "gönderildi" göstermesini engeller."""
        if not self.blade_down_tags_configured():
            return False
        if time.monotonic() < self._blade_retract_pulse_until:
            return False
        if not self.manual_blade_down_allowed():
            return False
        if self.demo_mode and self._demo is not None:
            self._demo.request_blade_down()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_blade_down")
        else:
            return False
        return True

    def request_clamp_down(self) -> bool:
        """GVL.xClampDownRequest - bkz. request_blade_down() notu."""
        if not self.clamp_down_tags_configured():
            return False
        if time.monotonic() < self._clamp_retract_pulse_until:
            return False
        if not self.manual_clamp_down_allowed():
            return False
        if self.demo_mode and self._demo is not None:
            self._demo.request_clamp_down()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_clamp_down")
        else:
            return False
        return True

    # -- C5 "Başlangıç Konumuna Dön" (PLC-HMI-20260921-10/11) ----------------

    def move_to_start_tags_configured(self) -> bool:
        """C5 henüz online doğrulanmadı (aday sözleşme) - demo modda anlamsız
        (her zaman True), gerçek modda pulse tag'i + 5 salt okunur durum
        tag'inin HEPSİ config'te olmalı, yoksa buton hiç etkinleşmez."""
        if self.demo_mode:
            return True
        required = (
            "cmd_move_to_start",
            "move_to_start_allowed",
            "move_to_start_busy",
            "move_to_start_done",
            "move_to_start_aborted",
            "move_to_start_error",
        )
        return all(name in self._config.nodes for name in required)

    def move_to_start_allowed_now(self) -> bool:
        """PLC-HMI-20260921-11: "İzin HMI'da yeniden üretilmez, Allowed
        okunur" - burada bıçak/baskı'daki gibi ayrıntılı bir ön koşul listesi
        TEKRARLANMAZ, yalnız PLC'nin kendi `xMoveToStartAllowed`'ı okunur."""
        if not self.move_to_start_tags_configured():
            return False
        snap = self._snapshot
        if snap.stale:
            return False
        if not self.demo_mode and snap.connection_state != ConnectionState.CONNECTED:
            return False
        return snap.move_to_start_allowed and not snap.move_to_start_busy

    def move_to_start_status(self) -> str:
        """"idle" (hiç gönderilmedi) | "sent" | "busy" | "done" | "aborted"
        | "error" - bkz. `_update_move_to_start_status`."""
        return self._move_to_start_status

    def request_move_to_start(self) -> bool:
        """GVL.xMoveToStartRequest: pulse (TRUE~150ms~FALSE). Gönderim PLC
        kabul kanıtı değildir - gerçek OPC UA reddi `commandWriteError` ile,
        PLC'nin kendi reddi Busy/Done/Aborted/Error readback'iyle gelir.
        Çağıran (ManualPage) 3 saniyelik basılı tutuşu ve iptal koşullarını
        kendisi yönetir; burada yalnız TEK pulse'ın koşulları/gönderimi var -
        bu metod kaç kez çağrılırsa çağrılsın izin yoksa hiçbir şey göndermez."""
        if not self.move_to_start_allowed_now():
            return False
        self._move_to_start_sent = True
        self._move_to_start_cleared = False
        self._move_to_start_status = "sent"
        if self.demo_mode and self._demo is not None:
            self._demo.request_move_to_start()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_move_to_start")
        else:
            return False
        return True

    # -- temporary Vision data simulator (PLC-HMI-20260917-02) --------------
    # Narrow, allow-listed write gateway used only by
    # services/vision_simulator.py so the UI/simulator never touches
    # plc.opcua_client directly and can never write outside
    # VISION_SIM_WRITABLE_TAGS (real Vision->PLC fields only - never PLC-
    # computed state, sensors, motion execute or valve tags).

    def request_vision_write(self, tag: str, value) -> None:
        if tag not in VISION_SIM_WRITABLE_TAGS:
            raise ValueError(f"Vision simülatörü '{tag}' yazamaz (izin listesinde değil).")
        if self.demo_mode:
            return  # Demo modda gerçek yazılacak PLC yok; teşhis amaçlı no-op.
        if self._worker is not None:
            self._worker.request_write(tag, value)

    def request_vision_sequential_write(self, fields: list[tuple[str, object]]) -> bool:
        """Returns True if the write was dispatched (result arrives later via
        `visionSequentialWriteResult`), False if there is nowhere to send it
        (real mode, no worker) - the caller must not treat False as success."""
        for tag, _value in fields:
            if tag not in VISION_SIM_WRITABLE_TAGS:
                raise ValueError(f"Vision simülatörü '{tag}' yazamaz (izin listesinde değil).")
        if self.demo_mode:
            QTimer.singleShot(0, lambda: self.visionSequentialWriteResult.emit(True, ""))
            return True
        if self._worker is None:
            return False
        self._worker.request_write_sequence(fields)
        return True

    def request_vision_cancel_pending(self) -> None:
        """Bekleyen (in-flight) bir sıralı Vision paketi varsa gerçekten
        iptal eder - PLC'ye kalan alanları yazmadan durur. Disarm/reconnect
        anında çağrılır (2026-09-17 görev notu)."""
        if not self.demo_mode and self._worker is not None:
            self._worker.cancel_pending_sequence()

    # -- engineering parameters ---------------------------------------------

    def get_parameter_value(self, key: str) -> float:
        return self._param_cache.get(key, 0.0)

    def is_parameter_confirmed(self, key: str) -> bool:
        """True once a real value has come back from the PLC for this
        parameter (always True in Demo mode). Settings screen must not
        present a value as real until this is True (2026-09-16)."""
        return key in self._param_confirmed

    def set_parameter(self, key: str, value: float) -> None:
        # PLC-HMI-20260921-10: move-to-start busy'de ayar yazmaları da kilitli
        # ("mode/jog/feed/pnömatik/ayar yazmalarını AYRICA kilitler" - xCycle
        # Active bunu kapsamaz).
        if self._snapshot.move_to_start_busy:
            raise ValueError("Başlangıç konumuna dönüş sürüyor - ayar değişikliği şu an kilitli.")
        # PLC-HMI-20260922-18 (HMI-A01, C06_1 audit): yalnız move_to_start_
        # busy kontrolü yetersizdi - cycle_active/stale/bağlantı/jog/eksen
        # hareketi şartları eksikti. UI (SettingsPage) yalnız cycle_active'i
        # ve yalnız onay penceresi AÇILIRKEN kontrol ediyor - onay penceresi
        # açıkken koşullar değişebilir; gerçek kaynak burası olmalı. UI zaten
        # bu ValueError'ı yakalayıp gösteriyor (_apply_parameter), yeni bir
        # UI katmanı gerekmez.
        if not self._settings_write_allowed():
            raise ValueError(
                "Şu an ayar yazılamaz - bağlantı taze/bağlı değil, otomatik "
                "çevrim aktif veya eksen hareket ediyor."
            )
        spec = next((s for s in PARAMETER_SPECS if s.key == key), None)
        if spec is None:
            raise ValueError(f"Bilinmeyen parametre: {key}")
        if not (spec.min_value <= value <= spec.max_value):
            raise ValueError(
                f"{spec.label_tr} aralık dışı ({spec.min_value:g}-{spec.max_value:g} {spec.unit})"
            )
        cross_error = self._validate_cross_field(key, value)
        if cross_error:
            raise ValueError(cross_error)
        self._settings_store.set(key, str(value))
        self._param_cache[key] = value
        if self.demo_mode and self._demo is not None:
            self._demo.params[key] = value
            self.parameterWriteConfirmed.emit(key)  # no real PLC round-trip to wait for
        elif self._worker is not None:
            self._param_pending[key] = (value, time.monotonic())
            self._worker.request_write(key, value)
        else:
            self.parameterWriteFailed.emit(key)

    def _validate_cross_field(self, key: str, value: float) -> str | None:
        """Cross-parameter sanity rules (2026-09-16, user requirement):
        these can never hold at the PLC without breaking motion, so an
        OPC UA write must never be attempted if they would be violated.
        Checked against the OTHER field's current (last-known) value - each
        row is applied independently, so changing a pair (e.g. widening both
        Y Yazılım Min and Max) may need to be done in the order that keeps
        every intermediate step valid too."""
        g = self.get_parameter_value
        if key == "lr_x_cut_start_pos":
            end = g("lr_x_cut_end_pos")
            if not value < end:
                return f"X Kesim Başlangıç ({value:g}) değeri X Kesim Bitiş ({end:g}) değerinden küçük olmalı."
        elif key == "lr_x_cut_end_pos":
            start = g("lr_x_cut_start_pos")
            if not start < value:
                return f"X Kesim Bitiş ({value:g}) değeri X Kesim Başlangıç ({start:g}) değerinden büyük olmalı."
        elif key == "lr_y_software_min":
            center = g("lr_y_center_position")
            y_max = g("lr_y_software_max")
            if not value < y_max:
                return f"Y Yazılım Min ({value:g}) değeri Y Yazılım Max ({y_max:g}) değerinden küçük olmalı."
            if not value < center:
                return f"Y Yazılım Min ({value:g}) değeri Y Merkez Konum ({center:g}) değerinden küçük olmalı."
        elif key == "lr_y_software_max":
            center = g("lr_y_center_position")
            y_min = g("lr_y_software_min")
            if not y_min < value:
                return f"Y Yazılım Max ({value:g}) değeri Y Yazılım Min ({y_min:g}) değerinden büyük olmalı."
            if not center < value:
                return f"Y Yazılım Max ({value:g}) değeri Y Merkez Konum ({center:g}) değerinden büyük olmalı."
        elif key == "lr_y_center_position":
            y_min = g("lr_y_software_min")
            y_max = g("lr_y_software_max")
            if not y_min < value < y_max:
                return (
                    f"Y Merkez Konum ({value:g}) değeri Y Yazılım Min ({y_min:g}) ile "
                    f"Y Yazılım Max ({y_max:g}) arasında olmalı."
                )
        return None

    def update_endpoint(self, endpoint: str) -> None:
        """Persists a new OPC UA endpoint to config; takes effect on restart."""
        self._config.endpoint = endpoint
        save_config(self._config, self._config_path)

    # -- alarms --------------------------------------------------------------

    def recent_alarms(self) -> list[AlarmEvent]:
        return self._alarms.recent()
