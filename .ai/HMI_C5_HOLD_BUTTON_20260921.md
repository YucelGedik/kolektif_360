# PLC-HMI-20260921-11 — Tek buton, 3 saniye basili tutarak baslangica donus
Kullanici talebi: tek buton olsun;3 saniye basili tutulunca iki eksen otomatik baslangica donsun. C5 PLC uygulama/test durumu henuz teyit edilmedi. Mevcut10 numarali sozlesmeye UI davranis ekidir, PLC state/motion degismez.

## Gorev
- Manuel ekranda tek "Baslangic Konumuna Don" butonu. Alt metin "3 saniye basili tutun — X + Y". Bu islev icin ikinci/ucuncu donus butonu ekleme; mevcut Y=0/Merkeze Git butonunu bu tek butonla degistir. Jog butonlarini koru.
- Sifir burada ayarlanmis hedeflerdir: X=GVL.lrX_CutStartPos, Y=GVL.lrY_CenterPosition. Sabit0 yazma, MC_Home/counter sifirlama yapma. Ayarlar0 ise sonuc0 olur. Hedefleri kisa bilgi olarak gosterebilirsin.
- Basma aninda baglanti ve veri tazeligi, xMoveToStartAllowed TRUE ve BusyFALSE olmali; kosullar 3 saniye boyunca korunmali. Monotonic sureyle3 saniye kesintisiz tutus; gorunur ilerleme/geri sayim. PLC request'i bu bekleme boyuncaFALSE kalir.
- 3 saniye dolunca tekrar izin/tazelik kontrolu; bir kez GVL.xMoveToStartRequest TRUE->yaklasik100-250ms->FALSE pulse gonder. Mevcut pulse/write servisinden gecsin. Fiziksel cikis veya motion execute/valf taglarina dogrudan yazma.
- 3 saniyeden once birakma, pointer buton disina cikma, pencere odak kaybi, sayfa degisimi, mod/izin kaybi, veri stale veya baglanti kaybi: sayaci iptal/sifirla; kuyruklanmis gecikmeli hareket yok. Tekrar denemede yeni basma gerekir.
- 3 saniyeden sonra parmak basili kalsa da yalniz bir pulse. Yeni talep icin birakip yeniden3 saniye basilmali. Auto-repeat kapali; klavye repeat/gecikmis timer ikinci pulse uretemez. UI disabled/yeniden etkin olsa da eski basma yeniden baslamaz.
- Pulse kabulunden SONRA birakmak Stop degildir; iki eksen hedefe otomatik gider. Bu deadman/jog butonu degil. Ayrica gorunur Stop mevcut GVL.Stop pulse'u ile kullanilabilir. Busy boyunca diger hareket/mod/ayar kontrolleri kilitli; Stop acik.
- Sonuc PLC readback: Busy hareket/durus, Done tamamlandi, Aborted reddedildi/iptal, Error ariza. Gonderim PLC kabul kaniti degildir; yazma hatasini goster. Onceki latched DoneTRUE'yu yeni komutun sonucu sayma; yeni istegin readback gecislerini izle, belirsizse tamamlandi iddia etme. Hizli zaten-hedefte tamamlanma durumunu da test et.
- Eksik NodeId/baglanti/stale durumunda buton aktif olmaz. Gercek config ile example config birlikte guncel; yalniz demo yeterli degil. C5 node yayini dogrulanmadan aktif hareket testi yapma.
- PLC HMI oturum kaybini algilamiyor: kabul edilmis donus baglanti kopsa da hedefe devam eder. Yeniden baglantida request tekrar gonderilmez. Onaylama sayaci baglanti oncesinden surdurulmez.

## Testler — H5-HOLD-T01..T08
1.2.9s tut/birak: hic TRUE yazisi yok.
2.3s tut: tam bir pulse; birakmadan5s daha tut: ikinci pulse yok.
3.Yeni birak/bas: yeni3s gerekir.
4.Sure dolmadan izin/stale/disconnect: iptal, reconnectte otomatik talep yok.
5.Pointer cikisi/odak kaybi/sayfa degisimi: iptal; gecikmis callback hareket uretmez.
6.Busy veya AllowedFALSE: sayac/talep yok; Stop kullanilabilir.
7.Yazma hatasi/eksik node: basari veya tamamlandi gosterilmez; eskiDone yeni sonuc sayilmaz.
8.PLC testine kullanici hazir oldugunda iki eksen hedefe gider; birakma hareketi durdurmaz, Stop durdurur. Zaten hedefte durum da dogrulanir.
Uygulama/test sonucunu Codex_Codesys.md uzerinden bildir. Mevcut tasarimi koru. PLC C5 masa testleri henuz gecti sayilmaz.
