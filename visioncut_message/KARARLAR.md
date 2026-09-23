# Kararlar

Yalnızca **iki insanın da onayladığı** kararlar buraya yazılır. Ajanlar
önerir, insanlar karar verir (bkz. README, kural 1 ve 5).

| # | Tarih | Karar | Onaylayan |
|---|---|---|---|
| 1 | 2026-09-23 | İki program **ayrı süreç, ayrı tam ekran pencere** olarak çalışacak (tek süreç/gömme planı iptal). Geçiş PLC tag'i olmadan, karşılıklı öne getirme/küçültme ile: VisionCut'ta "Makine Ekranı" bizim exe'yi başlatır/öne getirir; bizde "KAMERA EKRANI" VisionCut'ın exe'sini başlatır/öne getirir. Pencere eşleme başlıkla ("Makine Ekran" alt dizesi bizde korunur). Gerekçe: mesaj `07` (kare hızı/GIL/arıza izolasyonu ölçümleri). | Murat Turan (mesaj `08`), Yücel Gedik (mesaj `10`) |
