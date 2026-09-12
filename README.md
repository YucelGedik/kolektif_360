# Bufera Makine Ekranı

Perde/kumaş boylamasına kesim yapan yarı otomatik makinenin operatör /
manuel-servis / mühendislik / alarm kontrol ekranları.

Bu **VisionCut'ın kendisi değildir**. VisionCut başka bir şirkete ait bir
Windows uygulaması olup kaynak kodu bizimle paylaşılmıyor. Bu repo, o
uygulamaya sonradan entegre edilmek üzere hazırlanan **bağımsız ama
entegrasyona hazır** bir Makine Ekranı paketidir. Detaylar için
[`INTEGRATION.md`](INTEGRATION.md) ve [`docs/BUFERA_MAKINE_EKRANI_CODEX_ENTEGRASYON_BRIFI.md`](docs/BUFERA_MAKINE_EKRANI_CODEX_ENTEGRASYON_BRIFI.md).

## Kurulum

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma (bağımsız geliştirme kabuğu)

```powershell
python -m app.main
```

Gerçek bir PLC/OPC UA endpoint'i tanımlı değilse (`config/opcua.json` içinde
`endpoint` boşsa) uygulama otomatik olarak **Demo mod**'da açılır: normal
kesim çevrimini, dur/toparlanma akışını ve bir alarm senaryosunu simüle eder.
Bu sayede gerçek makine olmadan tüm ekranlar test edilebilir.

## Gerçek PLC'ye bağlanmak

1. `config/opcua.example.json` dosyasını referans alarak `config/opcua.json`
   içindeki `endpoint` alanını gerçek PLC adresine ayarlayın
   (`opc.tcp://<ip>:4840`).
2. `nodes` altındaki NodeId'leri UaExpert ile doğrulanmış gerçek CODESYS
   NodeId'leriyle güncelleyin (`ns=4` sabit kabul edilmemeli — deployment'a
   göre değişebilir; brif bölüm 10).
3. Uygulamayı yeniden başlatın. Bağlantı durumu üst status bar'da görünür:
   `Disconnected / Connecting / Connected / Degraded / Error`.
4. Bağlantı sorunlarında brif bölüm 10'daki kontrol listesini izleyin
   (server çalışıyor mu, port 4840 erişilebilir mi, security policy uyumlu
   mu, GVL değişkeni publish edilmiş mi, vb.).

## Testler

```powershell
pytest
```

## Proje yapısı

```
core/        CycleState, MachineSnapshot, parametre tanımları — Qt'den bağımsız
plc/         OPC UA config modeli, tag mapping, asyncua worker (QThread)
services/    Tek merkezi MachineService + demo simülatörü
persistence/ SQLite: alarm geçmişi, mühendislik parametre override'ları
ui/machine/  4 ekran: machine_page (operatör), manual_page, settings_page, alarm_page
app/         Bağımsız geliştirme/test kabuğu (main.py) — VisionCut'ın yerine geçmez
config/      OPC UA endpoint + node map (deployment'a özgü, git'e girmez)
tests/       pytest ile tag_map ve cycle_state sanity testleri
```

Mimari ve tasarım kararlarının brif ile eşlemesi için `INTEGRATION.md`'ye
bakın.
