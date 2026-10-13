# Kullanım kılavuzu

## Kurulum

Blender'da **Edit → Preferences → Get Extensions → Install from Disk** yolundan `Silkroad_PK2_Editor_v2_7_0.zip` dosyasını kurun. Eski sürüm etkinse önce devre dışı bırakın. Aynı dosya biçimlerini açan başka eklentiler kayıt çakışmasına yol açabilir.

3D Viewport'ta **N** tuşuna basıp **Silkroad PK2 Editor** panelini açın. Gerekiyorsa **PK2 Motorunu Kur** düğmesini kullanın. Motor kurulumu internet bağlantısı gerektirir.

## PK2 dosyalarını açma

**Data.pk2** dosyasını seçin ve taramanın tamamlanmasını bekleyin. Aynı klasördeki Map.pk2, Media.pk2 ve Particles.pk2 dosyaları bağlı dosyaları bulmak için okunur. Harita dokularının yüklenmesi için Map.pk2 dosyasının da bulunması gerekir.

Klasörlerde gezinin veya dosya adıyla arama yapın. BSR, BMS, BSK, BAN, NVM ve DOF dosyalarının adına tıklayarak içe aktarabilirsiniz. Satırı seçip **Seçili Modeli Blender’a Aktar** düğmesini de kullanabilirsiniz.

## Modeller ve animasyonlar

Dokulu model veya karakter yüklemek için **BSR** dosyasını seçin. Mesh, materyal, doku ve varsa iskelet birlikte yüklenir. **Animasyonları da çıkar** seçeneği bağlı animasyonları da getirir.

**BMS** yalnızca mesh, **BSK** ise iskelet yükler. Tek bir **BAN** dosyası için önce uygun iskeleti seçin. Animasyondaki kemik adları seçili iskeletle uyuşmalıdır.

## Haritalar ve zindanlar

**NVM** harita zeminini açar. **Harita nesnelerini de çıkar** seçeneği ağaç, kaya ve diğer harita nesnelerini yükler. **DOF** zindan bloklarını açar; aynı seçenek zindandaki ek nesneleri de yükler. Büyük zindanların aktarımı birkaç dakika sürebilir.

## Kaydetme

Sahneyi `.blend` olarak kaydedebilir veya **FBX + PNG** olarak dışa aktarabilirsiniz. FBX için mesh ve gerekiyorsa iskeleti birlikte seçin. FBX dosyasını yanındaki doku klasörüyle birlikte taşıyın.

BMS dosyaları PK2 arşivine geri yazılabilir. İşlemden önce arşiv yedeklenir ve yazılan dosya doğrulanır. Diğer beş biçim için PK2'ye geri yazma desteği yoktur.

## Jangan'ı Unreal'a aktarma

Data.pk2 arşivini açıp taramanın bitmesini bekleyin. **4. Unreal Projesi → Jangan UE Projesi Oluştur** düğmesine basın. Proje adını ve kaydedileceği konumu seçin. Seçtiğiniz adla yeni bir klasör oluşturulur; mevcut, dolu bir proje klasörünün üstüne yazılmaz.

**Unreal içine otomatik aktar** açıkken kurulu UnrealEditor-Cmd.exe otomatik bulunur. Gerekirse dosya seçicisinde bu yolu değiştirin. Kapalıyken FBX+PNG kaynakları ve Unreal aktarım betiği hazırlanır; UE içeriklerini oluşturmak için betiği Unreal'da çalıştırmanız gerekir.

Görsel nesneler mevcutsa Map.pk2 içindeki .o2 dosyalarından alınır; saray ve dekorlar da aktarılır. .o2 bulunmazsa NVM nesneleri kullanılır.

Blender açık sahnesini koruyarak Jangan ve çevresindeki 174 harita parçasını ve çevre nesnelerini geçici bir sahnede işler. Ardından Unreal ayrı bir işlemde modelleri ve dokuları içe alır, materyalleri oluşturur ve kaynak yerleşimlere göre tam haritayı kurar. Panel durum satırından sonucu takip edin. İptal için **UE Aktarımını İptal Et** veya Escape kullanın; kısmi proje hata kaydıyla korunur. Proje adı en fazla 20 karakter olmalıdır.

Hazır `.uproject` dosyasını UE'de açın. Başlangıç haritası `/Game/Jangan/Maps/Jangan`. `SourceAssets/manifest.json` kaynakları ve konumları; `ImportReport.json` UE sonucunu; `UnrealImport.log` ayrıntıları içerir. Aynı model şehirde tekrar kullanıldığında ortak Static Mesh'e başvurur.

Bu aktarım ana Jangan şehri, Bandit Fortress, çevredeki yollar, ormanlar ve dağları kapsar. Sonradan harita onarımı çalıştırmadan eklentinin ürettiği sonuç kullanılır. Çevre statik geometri olarak aktarılır; ağaç iskeletleri mevcut pozlarıyla sabitlenir. Veritabanındaki mob doğma noktaları, görev, hareketli su, rüzgâr animasyonu veya prototip oynanış/UI sistemi bu çevre aktarımına dahil değildir. Animasyonlu karakter ve Landscape aktarım düğmeleri ayrı kullanılabilir.

## Mob ve animasyonları Unreal’a aktarma

PK2 listesinden bir BSR mob/karakter seçip **Mob + Animasyonları UE’ye Aktar** düğmesine basın. Mevcut `.uproject` dosyasını seçin; projede Python Editor Script Plugin etkin olmalı. Otomatik aktarım için hedef UE projesini kapatın.

Mesh, iskelet, dokular ve BSR’nin bağlı animasyonları `/Game/Silkroad/Characters` altında yeni bir klasöre aktarılır. Animasyonlar ayrı klipler olarak aynı iskelete bağlanır. Proje dosyası ve haritalar korunur; eski varlıkların üzerine yazılmaz. Proje açık kalacaksa otomatik aktarımı kapatıp hazırlanan `import_character.py` betiğini UE Python konsolunda çalıştırın.

Bu özellik NPC davranışı, Animation Blueprint veya haritaya otomatik mob yerleştirme oluşturmaz. Birden fazla iskeleti olan ya da iskelete bağlanmamış mesh içeren kaynaklar açık hata verir.

## Hata kayıtları

İşlem sonucunu panelin durum satırından takip edebilirsiniz. Blender **Text Editor** içinde format bazlı `Silkroad import .NVM` gibi kayıtlar bulunur. `Silkroad dependency log` eksik bağlı dosyaları, `Silkroad PK2 errors` ise arşiv ve içe aktarma hatalarını gösterir.

Eksik doku veya iskelet kaydedilir; yüklenebilen geometri sahnede kalır. Zorunlu mesh eksikse işlem durur. Aktarım sırasında hata oluşursa bazı nesneler sahnede kalabilir.

## Testler

```text
python -m unittest discover -s tests -v
python -m pip install pk2api==1.5.0 --target engine
python tests/scan_assets.py "OYUN_KLASORU"
blender --background --factory-startup --python tests/blender_failure_checks.py
blender --background --factory-startup --python tests/blender_e2e.py -- "OYUN_KLASORU"
```

Gerçek oyun dosyalarıyla yapılan testlerin çıktıları `real_test_output` klasörüne yazılır. [Test raporu](TEST_REPORT.md) destek ve doğrulama sınırlarını açıklar.


## Jangan Landscape (2.6.0)
2.7.0 sürümünde tam harita için iki ayrı proje düğmesi bulunur: **Jangan UE Projesi Oluştur (Tile)** özgün kareli zemini; **Jangan UE Projesi Oluştur (Landscape)** yumuşak geçişli, boyanabilir UE arazisini oluşturur. İkisi de 174 bölge ve kaynak çevre yerleşimlerini aktarır. Landscape sürümü eski zemin mesh'lerini oluşturmaz. Yükseklik, boya maskeleri, özgün çim/toprak/kaya dokuları ve editör köprüsü otomatik hazırlanır.

Windows/UE 5.8 için uyumlu köprü DLL'si ve kaynak kodu dahildir. Seçilen editörün BuildId değeri uyuşmazsa eklenti köprüyü kaynak koddan derler; bu durumda Unreal C++ geliştirme araçları gerekir. Mevcut projenin üstüne yazılmaz; her düğmede yeni bir proje klasörü seçin.

Silkroad panelindeki **Jangan Landscape Aktar** düğmesi şehir merkezi, Bandit Fortress denemesi veya 174 bölgeli Jangan kapsamı için yükseklik ve boya katmanları üretir. Unreal 5.8 aktarımı için paketteki editör köprüsü derlenmelidir. Ayrıntılar: [JANGAN_LANDSCAPE.md](JANGAN_LANDSCAPE.md).
