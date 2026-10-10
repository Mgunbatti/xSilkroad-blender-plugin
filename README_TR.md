# Silkroad PK2 Editor 2.3.3 — Blender 5.2

Kanka, bu sürüm PK2 listesinden altı Jelly formatını çağırır: BMS, BSK, BAN, BSR, DOF ve NVM.

## Kurulum

1. Eski Silkroad PK2 Editor kopyasını devre dışı bırak. Ayrı kurulu Jelly eklentileri aynı operatör adlarını kullanıyorsa onları da devre dışı bırak; bu paket altısını içerir.
2. Blender → Edit → Preferences → Get Extensions → sağ üst menü → Install from Disk. **Silkroad_PK2_Editor_v2_3_3.zip** dosyasını seç ve etkinleştir. Source_Tests ZIP kurulum paketi değildir.
3. 3D Viewport'ta N tuşu → Silkroad PK2 Editor. Dil seçimini Türkçe yapabilirsin.
4. Panelde gerekiyorsa **PK2 Motorunu Kur** düğmesine bas. İnternet bağlantısı gerekir; motor pk2api 1.5.0'dır.

## İçe aktarma

1. Data.pk2 aç; aynı klasördeki Map.pk2, Media.pk2 ve Particles.pk2 bağımlılık için okunur. Harita dokuları için Map.pk2 erişilebilir olmalı.
2. Taramayı bekle. Klasörlerde gezin veya dosya adını ara.
3. Desteklenen dosyanın adına tıkla. Bu sürümde ad doğrudan içe aktarma düğmesidir. Alternatif: satırı seç ve **Seçili Modeli Blender’a Aktar** düğmesine bas.
4. NVM zemini varsayılan olarak gelir. Haritadaki nesneler için **Harita nesnelerini de çıkar** seçeneğini aç. DOF için aynı seçenek zindan içindeki ek nesneleri açar. Büyük zindanlar yüzlerce mesh içerebilir ve işlem sürebilir.
5. Karakter için BSR seç; mesh, BMT/doku ve varsa skeleton birlikte çözülür. **Animasyonları da çıkar** seçeneği BAN dosyalarını da getirir.
6. Tek BAN aktarıyorsan uygun BSK/BSR armature'ünü önce seç. Kemik adları uyuşmayan veya action üretmeyen animasyon hata verir.

Tek BMS dosyasında BMT yolu bulunmadığından panel materyal dosyasını tahmin etmez; dokulu model için ilgili BSR'yi kullan. BSK tek başına rig oluşturur.

## Sonuç ve hata kayıtları

Panelin durum satırını ve Blender bildirimini kontrol et. Blender Text Editor'ın veri listesinde şu kayıtlar bulunur:

- `Silkroad import .NVM` ve diğer beş formatın karşılığı: dosya yolu, okuma/işleme hatası, tam traceback ve üretilen nesne/action adları.
- `Silkroad dependency log`: eksik veya bozuk isteğe bağlı materyal, doku, skeleton ve animasyon bağımlılıkları.
- `Silkroad PK2 errors`: arşiv/çıkarma/panel çağrısı hataları.

Eksik zorunlu mesh/resource importu durdurur. Eksik isteğe bağlı doku veya skeleton kaydedilir; mümkün olan geometri korunur. İçe aktarma sırasında sonradan oluşan hata kısmi nesneler bırakabilir; log'da başarısız işlem açıkça görünür. Sahneye hiç geometri gelmemesi veya BAN'ın hiç action üretmemesi başarı sayılmaz.

## Kaydetme ve dışa aktarma

Mevcut .blend ve FBX + PNG akışı korunur. FBX dışa aktarırken mesh ve gerekiyorsa armature seç. PNG'ler FBX'in yanındaki texture klasörüne yazılır; orijinal DDS/image ve materyaller dönüştürülmez. FBX ile texture klasörünü birlikte taşı.

BMS'yi PK2'ye geri yazma mevcut doğrulama, yedek ve geçici arşiv akışını kullanır. NVM/DOF/BSR/BAN/BSK için PK2 geri yazma eklenmedi; Jelly NVM exporter'ı zaten tamamlanmamış olduğundan etkinleştirilmedi.

## Testleri tekrarlama

Kaynak ZIP'ini çıkar. Python 3.11+ ile:

```text
python -m unittest discover -s tests -v
python -m pip install pk2api==1.5.0 --target engine
python tests/scan_assets.py "OYUN_KLASORU"
blender --background --factory-startup --python tests/blender_failure_checks.py
blender --background --factory-startup --python tests/blender_e2e.py -- "OYUN_KLASORU"
```

Gerçek testin oyun varlıkları ve FBX çıktıları yerel `real_test_output` klasöründe kalır. Oyun dosyaları paketlere dahil değildir. Ayrıntılı sonuçlar TEST_RAPORU_TR.md ve test_evidence klasöründedir.

## Sınırlar ve lisans

Testler seçilmiş gerçek Holigan varlıkları ve sentetik bozuk girdiler içindir; her Silkroad istemcisi veya arşivdeki bütün dosyalar doğrulanmış değildir. Mevcut NVM düzeni 96×96 tile / 97×97 height vertex bekler. Farklı veya eksik veri bu sürümde açık hata verir. Oyun içi görünüşle bütün tile dönüş/flag kombinasyonlarının eşleşmesi ayrıca doğrulanmadı.

JellyBitz / Engels Quintero telif başlıkları ve GPL-3.0-or-later koşulları korundu. Binary reader ve map parser'dan türetilen dosyalar aynı başlıkları taşır. Lisans metni kaynak ve kurulabilir pakette bulunur. pk2api ayrı MIT lisanslı bağımlılıktır; bu ZIP'e gömülmedi.
