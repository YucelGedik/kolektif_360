# Bufera Makine Ekranı - Teknik Kararlar

Yeni teknik kararlar en uste eklenir.

## 2026-09-12 - VisionCut kaynagi olmadan bagimsiz teslim paketi olarak insa et

- Baglam: Brif, "mevcut VisionCut repository'sini incele, mevcut tema/
  component/navigation yapisini kullan" varsayimiyla yazilmis. Ancak VisionCut
  baska bir sirkete ait ve kaynak kodu bizimle paylasilmiyor; diskte sadece
  kurulum `.exe` dosyalari bulundu, kaynak repo yok.
- Secenekler: (a) VisionCut kaynagi gelene kadar bekle, (b) VisionCut'in
  gercek bilesenlerini tahmin ederek/uydurarak yazmaya calis, (c) bagimsiz,
  kendi test kabugu olan, entegrasyona hazir bir paket olarak insa et ve
  teslim notu (`INTEGRATION.md`) ile birlikte gonder.
- Karar: (c). Kendi `theme.py`/`widgets.py` setimizi brif SS31'deki renk
  tokenlarina birebir uyacak sekilde yazdik; `app/main.py` sadece bizim
  gelistirme/demo kabugumuz, VisionCut'in yerine gecmiyor.
- Sonuc: Proje `D:\work\GitProjects\Bufera_Tekstil_Project` altinda bagimsiz
  calisir durumda; VisionCut'i yapan sirket `INTEGRATION.md`'deki adimlarla
  `ui/machine/`, `core/`, `plc/`, `services/`, `persistence/`'i kendi
  `ui/plc/services/core` klasorlerine tasiyabilir.
- Geri alma kosulu: VisionCut kaynak kodu paylasilirsa, `ui/machine/theme.py`
  ve `widgets.py` VisionCut'in gercek tema/component'leriyle degistirilmeli;
  geri kalan katmanlar (core/plc/services/persistence) degismeden kalabilir.

## 2026-09-12 - OpenCV/NumPy disarida birakildi

- Baglam: Brif'teki VisionCut teknoloji yigininda OpenCV 5.0.0 ve NumPy
  2.5.1 listeleniyor.
- Secenekler: (a) brifteki tam yigini birebir kur, (b) sadece makine
  ekraninin gercekten kullandigi kutuphaneleri kur.
- Karar: (b). Kamera/goruntu isleme VisionCut'in isi; makine ekrani sadece
  PLC durumu gosterip komut gonderiyor, goruntu islemiyor.
- Sonuc: `requirements.txt` sadece PySide6, asyncua, pydantic, SQLAlchemy,
  pytest iceriyor. Kurulum daha hafif ve hizli.
- Geri alma kosulu: Ileride makine ekrani gercekten bir kamera/goruntu
  onizlemesi gostermek zorunda kalirsa eklenir.

## 2026-09-12 - PLC yokken calisan Demo/Simulasyon modu

- Baglam: Bu makinede gercek PLC/OPC UA sunucusu yok; ekranlarin
  gelistirilip test edilebilmesi gerekiyordu (kabul kriteri: "fake/demo
  snapshot ile ekran test edilebiliyor").
- Secenekler: (a) sadece sabit/mock veriyle statik ekran, (b) tam davranissal
  bir simulator (cevrim, stop/recovery, alarm dahil).
- Karar: (b). `services/demo_simulator.py` tum normal cevrimi (brif SS6),
  stop/recovery akisini (brif SS17) ve bir alarm senaryosunu (brif SS9)
  simule ediyor.
- Sonuc: `config/opcua.json` icinde `endpoint` bossa uygulama otomatik
  Demo moda geciyor; `MachineService` bu ayrimi UI'dan tamamen gizliyor.
- Geri alma kosulu: Gercek PLC baglandiginda `endpoint` doldurulup uygulama
  yeniden baslatilinca Demo mod otomatik devre disi kalir.

## Karar Kaydi Sablonu

### YYYY-MM-DD - Karar basligi

- Baglam: TODO
- Secenekler: TODO
- Karar: TODO
- Sonuc: TODO
- Geri alma kosulu: TODO
