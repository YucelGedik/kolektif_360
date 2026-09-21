# PLC-HMI-20260921-12 — C5 gercek config eksigi
Kullanici PLC'de xMoveToStartRequest TRUE yazarak iki eksenin hedefe geldigini bildirdi. Bu C5'in tum testleri gecti demek degil; request->hareket yolu kullanici tarafindan denendi. OPC node yayini ayrica teyit edilmeli.
Kaynak incelemesi: buton3s sonunda request_move_to_start() -> request_pulse("cmd_move_to_start") dogru. move_to_start_tags_configured alti mapping ariyor. config/opcua.example.json alti mappingi iceriyor; gercek config/opcua.json icermiyor. Bu nedenle yanlis buton degil, gercek baglanti eksik.
Gorev: Symbol Configuration yayini/online node'lari dogrula ve mevcut config formatinda alti mappingi gercek config'e de ekle:
cmd_move_to_start -> GVL.xMoveToStartRequest (BOOL write pulse)
move_to_start_allowed -> GVL.xMoveToStartAllowed (BOOL read)
move_to_start_busy -> GVL.xMoveToStartBusy (BOOL read)
move_to_start_done -> GVL.xMoveToStartDone (BOOL read)
move_to_start_aborted -> GVL.xMoveToStartAborted (BOOL read)
move_to_start_error -> GVL.xMoveToStartError (BOOL read)
Example mevcut namespace/path ile gercek online NodeId'yi dogrula; namespace tahminini kanit sayma. Uygulamayi/config'i yeniden yukleyip gercek tag okuma/yazma sonucunu dogrula. Eksik tag varsa kisa acik neden goster; bos tireyle birakma. 3s tutus sonunda bir pulse; hareket PLC'de yonetilir. Kullanici elle requestTRUE biraktiysa FALSE yapip yeni kenar olusturmasi gerektigini belirt. UI otomatik motion/servo testi baslatmasin; kullanici kontrollu dener.
Basitlik: Tek buton, tek request, PLC Allowed ve sonuc okumasi. Yeni katman, ek onay ekrani, gereksiz state/tag veya paralel PLC izin hesabi ekleme. Temel kilitleri ve yazma hata bilgisini koru. Onceki11 notunun3s davranisi ayni. Sonucu kopruye bildir.
