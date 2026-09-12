# UI Tasarim Sistemi

Bu belge UI degisikligi oncesi okunur. Proje ozel component adlari yerine
genel tasarim ilkeleri icerir.

## Temel Ilkeler

- Mevcut tasarim sistemine ve component yapisina uy.
- Sayfa ilk ekranda kullanilabilir deneyimi gostermeli; gereksiz landing/hero ekleme.
- Kontroller ekranda birbirini ezmemeli, metinler buton/kart disina tasmamali.
- Sabit piksel yerine mevcut spacing, token, theme veya layout helper kullan.
- Yeni renk/font eklemeden once mevcut theme/palette icinde ara.

## Yerlesim

- Dikey akis: yeni kontrol, onceki kontrolun altindan tutarli boslukla baslar.
- Uc veya daha fazla kontrol yan yana/grid ise framework'un layout sistemini kullan.
- Responsive sinirlar tanimla: min/max width, grid track, aspect-ratio veya container constraint.
- Kart icine kart koyma; kartlari tekrar eden item, modal veya gercek arac yuzeyi icin kullan.

## Kontrol Secimi

- Ikili ayarlar icin checkbox/toggle.
- Sayisal degerler icin input, stepper veya slider.
- Mod secimi icin segmented control/tabs.
- Komutlar icin ikonlu buton; anlasilmayan ikonlarda tooltip.
- Uzun secenek listeleri icin menu/select.

## Gorsel Kontrol Listesi

- [ ] Text overflow yok.
- [ ] UI elemanlari ust uste binmiyor.
- [ ] Hover/focus/disabled/loading state dusunuldu.
- [ ] Renk kontrasti okunabilir.
- [ ] Mobil ve masaustu genisliklerde ana is akisi bozulmuyor.
- [ ] Proje palette'i tek renge sikismiyor.

