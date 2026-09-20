# PLC-HMI-20260918-04 — Test bulguları / HMI iş listesi
Durum: kullanıcıya sunulan uygulama planı; henüz bu dosyayla otomatik uygulama başlatılmadı. Kullanıcı HMI agent'a verdiğinde bağımsız işleri uygulayabilir. PLC sözleşmesi bekleyen işlerde tag/state uydurulmaz. Mevcut mimari ve ana ekran tasarımı korunur.
Kaynak: PLC Bufera_Perde_Kesme_20260918_1510.export. PLC kökü C:/Users/agedik/Documents/ChatGPT/Bufera Tekstil PLC/BUFERA_TEKSTIL_MASTER_CONTEXT_PACK_2026-09-16. Ortak ayrıntılı plan docs/18_PLC_HMI_TASK_PLAN.md, inceleme docs/reports/2026-09-18_03_EXPORT_1510_REVIEW.md.

## Güncel bilgi
Heartbeat orijinal hesapta. IPC_Pk/Pb atamaları kaldırılmış, GVL deklarasyonları duruyor; aliasları veri kaynağı kabul etmeyin, BladeZDown/ClampDown esas. Kullanıcı düz çizgi tam masa çevrimi tamamlandı bildirdi; mekanik sistem bağlı değil. Y follow eğim testi henüz yok. PLC sensör-kaybı/timeout/alarm/Home değişiklikleri henüz uygulanmadı.

## H1 — Metin / state tutarlılığı (bağımsız)
- [ ] Feed izin göstergesi MANUEL AKTİF -> OPERATÖR KONTROLÜ. Kilitli görünümü korunur; feed izni MANUAL veya WAIT_FOR_MATERIAL olabilir.
- [ ] Üst durum metninin PLC eMachineState'ten geldiğini kontrol et. Seçili mod ile gerçek state farklıysa ayrı göster; yalnız xManualMode'a bakarak PLC state'ini değiştirmiş gibi sunma.
Kabul: MANUAL, WAIT_FOR_MATERIAL, CUTTING ekranları; stale/bağlantısız durumda yanlış hazır gösterimi yok.

## H2 — Mod değiştirme kilidi (UI/servis bağımsız)
- [ ] manual_page mod butonu cycle_active sırasında disable; yalnız CUTTING değil hazırlık ve dönüş çevrimi de kapsanır.
- [ ] MachineService.set_manual_mode aynı engeli uygulasın; UI dışından çağrıda yazı gitmesin. Stale/disconnected/unknown durumlarında fail closed; devam eden jog/hareket ile mod değişimi değerlendirilir.
- [ ] Düğmenin checked durumu PLC readback'inden gelir; engellenen istek seçili modu değiştirmiş gibi gösterilmez.
Kabul: active cycle/stale/disconnected -> sıfır mode write; izinli ve durmuş durumda mode write/readback. PLC mode kabul tarafı C6'da ayrıca değerlendirilecek.

## H3 — Başlatma engeli bilgisi (mevcut tag yayınını doğrula)
- [ ] StartPermitted FALSE için neden listesi: xX_AtStart, xY_AtCenter, servo/emergency, VisionReady/heartbeat/fault, Stop basılı, manuel, cycle. Gerçek mapping'i doğrula; bulunmayan tag için bool tahmini yapma.
- [ ] “X başlangıç konumunda değil”, “Y merkez konumunda değil”; sıfır yerine ayarlı lrX_CutStartPos/lrY_CenterPosition. İki neden birlikte gösterilebilir.
- [ ] Bilgilendirme/start inhibit arıza alarmından ayrı; HMI xStartPermitted'i kendi hesabıyla ikame etmez.
Kabul: X-only, Y-only, ikisi, Vision eksik, Stop, stale senaryolarında doğru açıklama. Eksik yayın varsa köprüden PLC'ye bildir.

## H4 — Alarm merkezi (PLC C2 sözleşmesini BEKLER)
- [ ] Ekran/tarihçe modeli hazırlanabilir; canlı alarm tagları tahmin edilmez.
- [ ] PLC active/latched/ilk neden/eşzamanlı nedenler ve varsa ack request sözleşmesi geldiğinde bağla.
- [ ] TRUE geçişinde olay kaydı; her poll'da tekrar kayıt yok. Aktif/latched/onaylı/koşul kalktı ayrımı.
- [ ] Reset'te yerel clear_active ile PLC'de süren hatayı yok gösterme. PLC readback/koşul otoritesi; mevcut hata mesajları korunur.
Kabul: iki eşzamanlı alarm, koşul sürerken reset, koşul kalktı ama latch sürüyor, reconnect ve tekrarsız geçmiş. İzin/risk kararları PLC tarafındadır.

## H5 — Başlangıç Konumuna Git (PLC C5 sözleşmesini BEKLER)
- [ ] Etiket Home/homing değil “Başlangıç Konumuna Git”. X ayarlı başlangıca, Y ayarlı merkeze; koordinat sıfırlamaz.
- [ ] Request + busy/done/error ve izin sözleşmesi PLC'den gelmeden canlı buton açma/internal execute yazma.
- [ ] İşlem sürüyor, reddedildi ve hata durumlarını göster; normal jog/mode çakışmalarını engelle.
Kabul: sadece kabul edilen request yazımı; xX_ReturnExecute/xY_MoveExecute doğrudan yazılmıyor.

## H6 — Eğimli otomatik kamera simülasyonu / teşhis (mevcut Vision sözleşmesi)
- [ ] Varsayılan düz çizgi modu korunur. İkinci açık seçilen senaryo: y(x)=y0+m*(x-x0); TargetY=f(TargetX). Her pakette sabit Y arttırma yok.
- [ ] Sabit çevrim başlangıç referansı kullan; UI değişikliği cycle sırasında referansı sıçratmasın. Gerçek kesim mesafesi, ileri bakış hedefi, Y yazılım sınırları, lrMaxAllowedSlope, lrY_MaxVelocity ve X hızı birlikte doğrulanır.
- [ ] İlk Y hizalama ve PLC Follow yükselen kenarında eğimin sıfırlanması dikkate alınır; kesimde yeni paket gerekir. Follow açıkken PLC başlangıç Y'si command setpoint olabilir; yalnız ideal çizgi eğimi yeterli valid garantisi değil.
- [ ] Hedef/actual/PLC setpoint ayrı gösterilir. Diagnostic sayfada TargetX/TargetY + source/valid/freshness/sequence. Ana ekrana hedef alanı zorunlu değil; layout değişikliği ayrıca kararlaştırılacak.
- [ ] PLC valid/fault/sensor/state'lerine yazılmaz. Kalıcı konum/hız limitlerini testi geçirmek için değiştirme. Özellik geçici/varsayılan kapalı ve gerçek kamera tek-yazıcı koşulu korunur.
Kabul: pozitif/negatif küçük eğim, sıfır eğim, sınır dışı yolun reddi, son noktadaki ileri hedef, reconnect/cancel; tüm testler izole. Gerçek motor testini kullanıcı başlatır.

## H7 — Timeout ayarları (PLC C4 sözleşmesini BEKLER)
- [ ] Kesin tag adı/tip/default/limit/persistence geldikten sonra iki TIME ayarını ekle; ms/s dönüşümü açık.
- [ ] Existing cycle/hareket ayar kilitleri ve gerçek write/readback hata mesajları korunur.
Kabul: birim, range, yazma hatası, readback ve reconnect. Bir dakika örneği kesin default değildir.

## Teslim / koordinasyon
Her H görevi ayrı durumla raporlansın. Kullanıcı başlatınca H1/H2, H3 mapping ve H6 izole geliştirme bağımsız yürüyebilir; H4/H5/H7 PLC sözleşmesini bekler. Yeni bağımlılıkları .ai/Codex_Codesys.md içine yaz. Kaynak ve aktif/example config uyumu, izole pytest ve UI kontrolü, .ai hafızası güncellensin. PLC'ye otonom write/test/hareket yok. PLC kodunu değiştirme; CODESYS uygulamasını kullanıcı yapar.
