# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260921-12: C5 ("Başlangıç Konumuna Dön") gerçek config eksiği
tamamlandı.** Kullanıcı PLC'de elle `xMoveToStartRequest=TRUE` yazıp iki
eksenin hedefe gittiğini doğruladı - PLC kod incelemesinde buton mantığının
zaten doğru olduğu, yalnızca 6 NodeId'nin gerçek `config/opcua.json`'a hiç
eklenmediği bulundu (önceki turda C5 online doğrulanmadığı için kasıtlı
bırakılmıştı). Artık gerçek config'e eklendi (example ile birebir).
Eksik-tag durumunda "Başlangıç Konumu" kartı artık "—" değil "TAG EKSİK"
gösteriyor. **Kullanıcıya iletildi:** PLC'de elle TRUE bırakılan request
varsa önce FALSE'a çekilmeli (HMI pulse'u zaten-TRUE bitten yeni kenar
oluşturmayabilir). Butonun PLC'ye karşı uçtan uca çalıştığını (Allowed/
Busy/Done readback dahil) doğrulamak kullanıcının sıradaki adımı.

**Aynı gün, önceki tamamlanan işler (detay CHANGELOG_MEMORY.md'de,
kronolojik sırayla):** PLC-HMI-20260921-09 (manuel Aşağı talepleri) ->
C0.4 takibi (gerçek config + eksik-tag koruması) -> PLC-HMI-20260921-10/11
(C5 "Başlangıç Konumuna Dön" 3s tek buton) -> kullanıcı UI geri bildirimi
(buton yerleşimi, X/Y hizalama, jog hızı girişi) -> bugünkü C5 config fix.

**Ayrı bulgu (beklemede, kullanıcı talimatı):** VisionCut'tan 3 yeni mesaj
(07/08/09) geldi - ayrı süreç mimarisi, paketlenmiş exe + 4 kusur yaması,
pencere başlığı/build sahipliği. Kullanıcı: "önce biz işimizi bitirelim" -
dokunulmadı.

## Siradaki Gorevler

- [ ] Kullanıcı: "Başlangıç Konumuna Dön" butonunu HMI üzerinden gerçek
      PLC'ye karşı uçtan uca denemeli (config artık tam; önce PLC'deki elle
      bırakılmış TRUE'yu FALSE'a çekmeli).
- [ ] VisionCut 07/08/09 mesajları: kullanıcı "sonra ilgilenelim" dedi.
- [ ] H4/H7: PLC C2 (alarm) kararı gelince başlanacak (H7 iptal edildi).
- [ ] SettingsStore `data/bufera.db` test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 235/235 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - PLC-HMI-20260921-12: C5 gerçek config eksiği + "TAG EKSİK"
  gösterimi (detay: CHANGELOG_MEMORY.md aynı tarihli en üst girişi).
- 2026-09-21 - Manuel sayfa UI geri bildirimi: buton yerleşimi/hizalama +
  jog hızı girişi.
- 2026-09-21 - PLC-HMI-20260921-10/11: "Başlangıç Konumuna Dön" tek buton.
- 2026-09-21 - C0.4 takibi + PLC-HMI-20260921-09: manuel Aşağı talepleri.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR (bilinen).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun el ile senkronlanan
  bir aynası, otomatik güncellenmiyor.
