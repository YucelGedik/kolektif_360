"""PLC-HMI-20260921-16 (C6.1 Hata/Uyarı/Mesaj kataloğu) - kullanıcı isteği
(2026-09-22): "Operatör alarm listesine bakıp alarmların anlamlarını
okuyabilsin... oradan bakıp bize feedback verebilir."

Bu modül CANLI veri okumaz. Alarmlar sayfasındaki "Alarm Listesi" sekmesinde
gösterilen, TÜM olası bildirimlerin (Hata/Uyarı/Mesaj) statik bir sözlüğüdür
- operatörün "az önce görünen bu neydi" diye arayabileceği bir referans.
Metinler `services/machine_service.py::ALARM_CATALOG` ve `ui/machine/
machine_page.py::compute_start_inhibit_reasons`'da GERÇEKTEN kullanılanlarla
birebir tutulur (elden geldiğince); biri değişirse öbürü de güncellenmeli."""

from __future__ import annotations

from dataclasses import dataclass

from persistence.alarms import SEVERITY_ALARM, SEVERITY_MESSAGE, SEVERITY_WARNING


@dataclass(frozen=True)
class NotificationCatalogEntry:
    catalog_id: str
    severity: str
    context: str  # ne zaman/hangi durumda görünür
    text: str  # operatöre gösterilen (veya PLC tag'i gelince gösterilecek) tam metin


NOTIFICATION_CATALOG: tuple[NotificationCatalogEntry, ...] = (
    # -- HATA (services/machine_service.py::ALARM_CATALOG ile birebir) ------
    NotificationCatalogEntry("H01", SEVERITY_ALARM, "Kesim sırasında", "Kesimde baskı aşağı sensörü kayboldu."),
    NotificationCatalogEntry("H02", SEVERITY_ALARM, "Kesim sırasında", "Kesimde bıçak aşağı sensörü kayboldu."),
    NotificationCatalogEntry("H03", SEVERITY_ALARM, "Baskı aşağı inerken", "Baskı belirtilen sürede aşağı konuma ulaşamadı."),
    NotificationCatalogEntry("H04", SEVERITY_ALARM, "Bıçak aşağı inerken", "Bıçak belirtilen sürede aşağı konuma ulaşamadı."),
    NotificationCatalogEntry(
        "H05",
        SEVERITY_ALARM,
        "\"Başlangıç Konumuna Dön\" sırasında",
        "Başlangıç konumuna dönüş sırasında arıza oluştu. Eksenlerin durmasını "
        "bekleyin. Bıçak/baskı konumlarını ve eksen arızasını kontrol edin. "
        "Nedeni giderdikten sonra Reset verin. Manuel modda Bıçak Yukarı ve "
        "Baskı Yukarı düğmelerine istediğiniz sırada basın. Açıklıklar "
        "sağlanınca Başlangıç Konumuna Dön düğmesini 3 saniye basılı tutun.",
    ),
    NotificationCatalogEntry("H06", SEVERITY_ALARM, "Her an", "X servo etkinleştirme hatası."),
    NotificationCatalogEntry("H07", SEVERITY_ALARM, "Her an", "Y servo etkinleştirme hatası."),
    NotificationCatalogEntry("H08", SEVERITY_ALARM, "Kesim hareketi sırasında", "X kesim hareketi hatası."),
    NotificationCatalogEntry("H09", SEVERITY_ALARM, "Dönüş hareketi sırasında", "X dönüş hareketi hatası."),
    NotificationCatalogEntry("H10", SEVERITY_ALARM, "Y konumlandırma sırasında", "Y konumlandırma hatası."),
    NotificationCatalogEntry("H11", SEVERITY_ALARM, "Kesim sırasında (Y takip)", "Y takip hareketi hatası."),
    NotificationCatalogEntry(
        "H12", SEVERITY_ALARM, "Durdurma sırasında (PLC aday tag - henüz build/export edilmedi, bu HATA şu an hiç tetiklenmez)",
        "X durdurma bloğu hata verdi. Tam duruşu kontrol edin.",
    ),
    NotificationCatalogEntry(
        "H13", SEVERITY_ALARM, "Durdurma sırasında (PLC aday tag - henüz build/export edilmedi, bu HATA şu an hiç tetiklenmez)",
        "Y durdurma bloğu hata verdi.",
    ),
    NotificationCatalogEntry(
        "H14", SEVERITY_ALARM, "Her an (PLC aday tag - henüz build/export edilmedi, bu HATA şu an hiç tetiklenmez)",
        "X eksen/sürücü arıza durumu.",
    ),
    NotificationCatalogEntry(
        "H15", SEVERITY_ALARM, "Her an (PLC aday tag - henüz build/export edilmedi, bu HATA şu an hiç tetiklenmez)",
        "Y eksen/sürücü arıza durumu.",
    ),
    NotificationCatalogEntry("H16", SEVERITY_ALARM, "Her an", "Emniyet geri bildirimi yok. Acil stop/emniyet zincirini kontrol edin."),
    NotificationCatalogEntry("H17", SEVERITY_ALARM, "Her an", "Vision uygulaması arıza bildiriyor."),
    NotificationCatalogEntry("H18", SEVERITY_ALARM, "Kesim/hizalama sırasında", "Yorumlanan hedef/çizgi geçersiz."),
    NotificationCatalogEntry(
        "H19", SEVERITY_ALARM, "Arıza durumunda, bilinen bir neden (H01-H18) yoksa",
        "PLC arıza durumunda; ayrıntılı neden bilgisi mevcut değil.",
    ),
    # H20-H22: PLC-HMI-20260922-17 (C6 toplu teslim) - kod/test teslim edildi,
    # PLC tarafında build/online doğrulama henüz YAPILMADI (aday tag).
    NotificationCatalogEntry(
        "H20", SEVERITY_ALARM,
        "Çalışan çevrimde (PLC aday tag - henüz build/online doğrulama yapılmadı, bu HATA şu an hiç tetiklenmez)",
        "Çalışan çevrimde mod değiştirme talebi alındı; makine durduruldu.",
    ),
    NotificationCatalogEntry(
        "H21", SEVERITY_ALARM,
        "Çevrim sırasında, baskı tutulması gereken adımlarda (PLC aday tag - henüz build/online doğrulama yapılmadı, bu HATA şu an hiç tetiklenmez)",
        "Çevrim sırasında baskı aşağı sensörü kayboldu; makine durduruldu.",
    ),
    NotificationCatalogEntry(
        "H22", SEVERITY_ALARM,
        "Eksenler başlangıca dönerken (PLC aday tag - henüz build/online doğrulama yapılmadı, bu HATA şu an hiç tetiklenmez)",
        "Eksenler dönerken bıçak açıklığı kayboldu; makine durduruldu.",
    ),
    # -- UYARI (ui/machine/machine_page.py::compute_start_inhibit_reasons ile birebir) --
    NotificationCatalogEntry("U01", SEVERITY_WARNING, "Start istenirken", "X başlangıç konumunda değil (ayarlı X başlangıç konumuna göre)."),
    NotificationCatalogEntry("U02", SEVERITY_WARNING, "Start istenirken", "Y merkez konumunda değil (ayarlı Y merkez konumuna göre)."),
    NotificationCatalogEntry("U03", SEVERITY_WARNING, "Manuel moddayken", "Start için Otomatik modu seçin."),
    NotificationCatalogEntry(
        "U04", SEVERITY_WARNING, "Manuel hazırlık gerekirken",
        "Manuel hazırlığı tamamlayın: eksik bıçak/baskı Yukarı kabulü, hâlâ "
        "aşağıda kalan mekanizma, konum veya servo koşulu varsa ayrıca belirtilir.",
    ),
    NotificationCatalogEntry("U05", SEVERITY_WARNING, "Start istenirken, bıçak aşağıdaysa", "Start için bıçağı kaldırın."),
    NotificationCatalogEntry(
        "U06", SEVERITY_WARNING, "Stop aktifken (PLC aday tag - henüz build/export edilmedi, bu UYARI şu an hiç tetiklenmez)",
        "Stop talebi aktif; Start engelli.",
    ),
    NotificationCatalogEntry("U07", SEVERITY_WARNING, "Servo hazır değilken (bilinen bir HATA yoksa)", "X servo hazır değil. / Y servo hazır değil."),
    NotificationCatalogEntry("U08", SEVERITY_WARNING, "Vision bağlantısı zayıfken", "Vision heartbeat alınmıyor/güncellenmiyor. PLC bağlantısı taze olmalı."),
    NotificationCatalogEntry("U09", SEVERITY_WARNING, "Vision hazır değilken (VisionFault yoksa)", "Vision hazır değil."),
    NotificationCatalogEntry("U10", SEVERITY_WARNING, "PLC verisi bayatken", "PLC verisi güncel değil; izin/konum bilgisi doğrulanamıyor."),
    NotificationCatalogEntry("U11", SEVERITY_WARNING, "Bilinen tüm koşullar sağlanmışken", "PLC Start izni yok; ek koşul bilgisi gerekli."),
    # -- MESAJ (normal durum bilgisi - eMachineState etiketleriyle uyumlu) --
    NotificationCatalogEntry("M01", SEVERITY_MESSAGE, "\"Kamera Bekleniyor\" durumunda", "Kamera verisi bekleniyor."),
    NotificationCatalogEntry("M02", SEVERITY_MESSAGE, "\"Bıçak Talebi Bekleniyor\" durumunda", "Bıçak talebi / geçerli yörünge bekleniyor."),
    NotificationCatalogEntry("M03", SEVERITY_MESSAGE, "\"Baskı/Bıçak İniyor\" durumunda", "Baskı/bıçak aşağı sensörü bekleniyor."),
    NotificationCatalogEntry("M04", SEVERITY_MESSAGE, "\"Bıçak/Baskı Kalkıyor\" durumunda", "Bıçak/baskı aşağı sensöründen çıkış bekleniyor."),
    NotificationCatalogEntry("M05", SEVERITY_MESSAGE, "\"Başlangıca Dönüyor\" durumunda", "Başlangıç konumuna dönülüyor."),
    NotificationCatalogEntry("M06", SEVERITY_MESSAGE, "\"Başlangıca Dönüş Durduruldu\" durumunda", "Dönüş durduruluyor; talepleri bırakın."),
    NotificationCatalogEntry("M07", SEVERITY_MESSAGE, "\"Recovery\" durumunda", "Manuel modu seçerek hazırlığı yapın."),
    NotificationCatalogEntry("M08", SEVERITY_MESSAGE, "\"Başlangıç Konumuna Dön\" tamamlanınca", "Başlangıç konumuna dönüş tamamlandı."),
    NotificationCatalogEntry("M09", SEVERITY_MESSAGE, "\"Durduruluyor\" durumunda", "Otomatik çevrim durduruluyor; mevcut devam yolu bıçak yukarı/eksen dönüşü."),
)
