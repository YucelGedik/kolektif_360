# PLC → HMI koordinasyon notu

Mesaj ID: PLC-HMI-20260916-01
Kaynak: Bufera Tekstil PLC / güncel 1730 exportu.
Durum: bilgilendirme ve HMI tarafında değerlendirme; PLC sensör dönüşümü henüz uygulanmadı.

## Doğrulanan PLC durumu
- Üç MoveAbsolute Error bağlantısı düzeltildi.
- 20 persistent parametre + PersistentVars instance path listesi doğrulandı.
- GVL tag adları korunuyor; online/power-cycle testleri ayrıca açık.
- Fiziksel kapasite 10 PNP DI (%IX40.0–40.7, %IX41.0–41.1), 8 PNP DO (%QX30.0–30.7).
- Fiziksel adlar için xDI_/xDO_ öneriliyor; HMI mapping bu ham adlara taşınmayacak.

## İki sensör kararı ve somut HMI farkı
- Yalnız Blade Down / Clamp Down sensörü var; yukarı sensörü yok.
- TRUE aşağı doğrulandı; FALSE aşağıda değil. Kesin yukarı konumu anlamı verilmemeli.
- services/machine_service.py:181–186, clamp_up/blade_up değerlerini NOT down olarak türetiyor.
- ui/machine/machine_page.py:180,183 ve manual_page.py:227,230 FALSE için YUKARI gösteriyor.
- HMI tarafında bu göstergeleri aşağıda değil semantiğine uyarlayın; up alanları kullanılıyorsa
  sensör teyidi sayılmamalı. Veri bilinmiyor/bağlantı kopuk durumu ayrıca korunmalı.
- Bu not manuel Yukarı komutunun adını değiştirme talebi değildir; komut ile doğrulanmış konum farklıdır.
- GVL.BladeZDown ve GVL.ClampDown korunacak. Mevcut PLC kodunda hâlâ timer kabulü var;
  sensör kaynaklı davranışın PLC'de devreye alındığı ayrıca bildirilecek.

## Sözleşme sınırları
- Start/Stop/Reset pulse, xManualMode ve dört jog request tagı korunuyor.
- Fiziksel butonlar bu HMI taglarına ikinci yazıcı olmayacak; PLC'de ayrı kaynaklar birleştirilecek.
- Manuel blade/clamp ve Y center requestleri henüz PLC'de açılmadı; iç motion/valf taglarına yazmayın.
- Settings'te cycle dışındaki manuel hareketi de yazma izni bakımından değerlendirin.
- Aktif config/opcua.json ve example birlikte kontrol edilmeli; mevcut bağlantı değiştirilmemeli.

## Doküman tutarlılığı
HMI SESSION_BRIEF, güncel PLC bağlantısı ve 46/46 geçmiş test bildiriyor.
CLAUDE.md eski varsayılan demo/boş endpoint açıklaması içeriyor.
SESSION_BRIEF'teki Vision Zaman Aşımı hard-coded ifadesi PLC tarafıyla uyuşmuyor:
pnömatik 500 ms timerlar var, ayrı Vision Wait Timeout yok; heartbeat timeout farklıdır.
Bu geçmiş kayıtları güncel durumdan ayırın.

## Yanıt alanı
Yanıtı bu dosyanın sonuna tarih + HMI → PLC başlığıyla ekleyebilirsiniz.
İlgili kod değişikliği, test sonucu ve PLC'den gereken tag/kararları belirtin.
Bu not HMI testlerini yeniden çalıştırdığımız veya karşı tarafın okuduğu iddiasını içermez.


## PLC -> HMI | 2026-09-17 | PLC-HMI-20260917-02
Kullanıcı geçici mühendislik diagnostic/Vision simülatörü uygulamasını istedi. Görev ve Faz 0-5: .ai/HMI_TEMP_VISION_SIMULATOR_TASK.md. Bu yeni görevdeki güncel PLC bilgileri önceki tarihsel notların ilgili kısımlarının yerini alır. Sensör dönüşümü uygulandı; heartbeat kaynakta geçici TRUE, saha kabulünden önce orijinal hesap geri yüklenmeli. Ana HMI korunacak, simülatör varsayılan kapalı, gerçek Vision ile tek yazıcı ilkesi ve kaynak devri zorunlu. Bu kayıt yalnız görev teslimidir; HMI kodu/testi bu oturumda yapılmadı.
