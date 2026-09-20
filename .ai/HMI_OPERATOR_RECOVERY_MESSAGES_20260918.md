# PLC-HMI-20260918-05 — Operatör hata/hazırlık mesajları
Durum: kullanıcı isteğiyle HMI iş listesine ek. C0.2a PLC uygulaması kullanıcı tarafından deneniyor; yeni export doğrulaması henüz açık. Uygun kaynak/tag yayını doğrulandıktan sonra bağlanacak.

Operatör akışı kısa kalacak: arıza -> duruş -> Reset -> manuel -> Bıçak Yukarı ve Baskı Yukarı (istenen sırada) -> başlangıç konumları -> Auto / yeni Start. İki butonun sırası zorlanmayacak. Kullanıcı iki geri çekmenin çalıştığını bildirdi. Sensör kaybının Reset olmadan RECOVERY'ye atladığı doğrulanmış değil; mevcut kod beklentisi önce FAULT, kabul edilen Reset sonrası RECOVERY.

## State'e göre ana mesaj
- FAULT / hareket henüz sürüyor: “Kesim durduruluyor. [Gerçek alarm nedeni]. Eksenlerin durmasını bekleyin.”
- FAULT / durmuş: “Kesim durduruldu. [Gerçek alarm nedeni]. Nedeni kontrol edin, ardından Reset'e basın.” Reset uygunluk kontrolü PLC'dedir; HMI reset kabulünü varsaymaz.
- RECOVERY (510): “Manuel hazırlık bekleniyor. Manuel modu seçin.” Eski otomatik dönüş/recovery ifadesi kullanılmamalı.
- MANUAL ve xManualPreparationRequired: “Bıçak Yukarı ve Baskı Yukarı düğmelerine istediğiniz sırada basın. Açıklıklar sağlandıktan sonra eksenleri başlangıç konumlarına getirin.”
- Hazırlık tamam: “Hazırlık tamamlandı. Perdeyi kontrol edin. Otomatik modu seçerek yeni Start verin.” State/readback ve diğer hazır koşullarıyla tutarlı göster; Ready veya StartPermitted'i sahte TRUE gösterme.

## Alt satır: yalnız eksik koşulları göster
- NOT xBladeRetractAccepted: “Bıçak Yukarı talebi bekleniyor.”
- NOT xClampRetractAccepted: “Baskı Yukarı talebi bekleniyor.”
- BladeZDown: “Bıçak aşağı sensörü hâlâ aktif.”
- ClampDown: “Baskı aşağı sensörü hâlâ aktif.”
- İlgili valf aşağı komutu TRUE: “Bıçak/Baskı aşağı komutu henüz kapanmadı.”
- Konumlar eksik: “X başlangıç / Y merkez konumuna dönüş bekleniyor.” Mevcut aşamada jog; Başlangıç Konumuna Git sonraki pakette.

Butonlar request'e pulse yazar. Kabul bitleri PLC'nin read-only bilgisidir; HMI set etmez. Mesajlar komut üretmez/otomatik Reset vermez; hata geçmişi açıklama değişince silinmez. Sensör FALSE, kullanıcının kabul ettiği mekanik açıklıktır; ayrı yukarı sensörü gibi sunulmaz. Alarm/hazırlık ekranı sade tutulur, ayrı bir işlem sihirbazı eklenmez.

## Sonraki PLC paketi
C0.3: Clamp Down ve Blade Down için iki ayrı ayarlanabilir watchdog, başlangıç T#60s. Süre dolunca alarm; süreyle konum tamam kabulü yok. HMI Ayarlar tag/tip/birimleri PLC teslimiyle kesinleşecek, şu an tahmin edilmez. CUTTING sensör kaybı 60s bekletilmez.
