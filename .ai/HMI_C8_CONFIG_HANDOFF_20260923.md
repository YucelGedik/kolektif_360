# PLC-HMI-20260923-23 — C8 config eksikliği / yanlış yükleme çıkarımı

Kullanıcı C8 PLC kodunu ve güncel Symbol Configuration'ı gerçek PLC'ye indirdiğini açıkça bildirdi. Not21'deki henüz uygulanmadı ifadesi yeni C8E EMG pnömatik düzeltmesi içindi; C08_2 sıfırlama özelliğinin yüklenmediğine kanıt DEĞİLDİR. C8E'nin yüklenmesi C8 sıfırlama ekranının önkoşulu değildir.

Kaynakta doğrulandı:
- config/opcua.example.json: cmd_set_zero_request + X/Y için Done/Busy/Error/ErrorID/CommandAborted 11 alan var.
- config/opcua.json: bu 11 alan YOK.
- services/machine_service.py set_zero_tags_configured yalnız `all(name in self._config.nodes for name in required)` yapıyor; online PLC sorgusu yapmıyor.
- ui/machine/set_zero_dialog.py bu durumda PLC henüz doğrulamadı/tamamlanmadı diyor. Bu çıkarım yanlış. Doğru metin: “HMI bağlantı ayarında sıfırlama alanları eksik. PLC sembollerinin erişimi kontrol edilip HMI eşlemesi tamamlanmalı.” Eksik anahtarları teşhiste gösterin.

Sıradaki iş:
1. Kullanıcı yükleme bilgisini güncelleyin; tekrar PLC kodu istemeyin ve C8E'yi önkoşul yapmayın.
2. Mevcut OPC UA bağlantısında salt okunur browse/read ile 11 alanın gerçek NodeId/DataType/StatusCode/AccessLevel bilgisini doğrulayın. Namespace indexini/FB iç yolunu online görmeden kesin diye bildirmeyin. MC_Home örnekleri Motion_Control altında, Power_Control altında DEĞİL. Aday yollar example config'te var; çalışan gerçek config ön eki ns=4;s=|var|MAT LC-C07.Application olsa da FB yolları henüz tarafımızdan online teyit edilmedi.
3. Talebe TRUE yazmadan alanları doğrulayın; cmd_set_zero_request BOOL ve yazma izni, 8 durum BOOL, iki ErrorID gerçek sunucu tipini kontrol edin. Başarılı erişim sonrası mevcut gerçek config'i yedekleyip yalnız bu11eşlemeyi ekleyin, diğerlerini koruyun. Yeniden yükleme/uygulama yeniden açılması gerekiyorsa kullanıcıya belirtin.
4. Bulunamayan alan varsa tam adı ve gerçek OPC hata kodunu verin. Örnek config var diye gerçek config tamamlandı demeyin. Sahada erişim yoksa online doğrulama YAPILMADI deyin; kullanıcıdan OPC browse çıktısı/ilgili sembol listesi isteyin.
5. Otomatik Home/force/PLC download yapmayın. HMI modal/3s davranışı ve testleri korunur; cihaz denemesini kullanıcı yapar.

11 alan, PLC'ye 11 yeni GVL eklemek demek değil: yalnız xSetZeroRequest yeni; kalan10 mevcut iki Home örneğinin sonuç alanlarıdır. Mevcut sade sözleşme değişmiyor.
