# xSilkroad Blender Plugin

Silkroad PK2 arşivlerindeki modelleri, karakterleri, animasyonları ve haritaları Blender'a aktaran eklenti.

PK2 dosyalarını Blender içinden açabilir, arşivde arama yapabilir ve seçtiğiniz dosyayı sahneye aktarabilirsiniz. Modellerin bağlı olduğu mesh, materyal, doku ve iskelet dosyaları birlikte çıkarılır. Karakter animasyonları seçili iskelete yüklenir; harita ve zindanlar nesneleriyle birlikte açılabilir.

Düzenlenen sahneler `.blend` olarak kaydedilebilir veya PNG dokularıyla birlikte FBX'e aktarılabilir. BMS dosyaları yedek alınarak PK2 arşivine geri yazılabilir.

**Jangan UE Projesi Oluştur** düğmesi, ana şehri ve surların yakın çevresini ayrı bir Unreal projesine aktarır. Arazi ve modeller PK2'den çıkarılır, PNG dokular bağlanır ve nesneler kaynak konumlarına yerleştirilir. Kurulu Unreal editörü otomatik bulunur; işlem açık Blender sahnesini korur.

## Desteklenen dosyalar

| Dosya | İçerik |
|---|---|
| BSR | Model ve bağlı dosyaları |
| BMS | Mesh |
| BSK | İskelet |
| BAN | Animasyon |
| NVM | Harita zemini ve nesneleri |
| DOF | Zindan blokları ve nesneleri |

## Kurulum

1. [Eklenti ZIP'ini indirin](releases/Silkroad_PK2_Editor_v2_4_2.zip).
2. Blender'da **Edit → Preferences → Get Extensions → Install from Disk** yolunu açın.
3. ZIP'i seçip eklentiyi etkinleştirin.
4. 3D Viewport'ta **N** tuşuna basıp **Silkroad PK2 Editor** panelini açın. Gerekirse panelden **PK2 Motorunu Kur** düğmesine basın.

**Blender 5.2.2'de test edilmiştir.** Arayüz Türkçe ve İngilizce kullanılabilir.

## Kullanım

Data.pk2 dosyasını açın, bir klasöre girin veya dosya adıyla arama yapın. Desteklenen dosyanın adına tıklayarak içe aktarın. Animasyonları ve harita nesnelerini paneldeki seçeneklerden açabilirsiniz. Dokulu karakterler için BSR dosyasını seçin; tek bir BAN dosyası yüklemek için önce uygun iskeleti seçin.

[Kullanım kılavuzu](README_TR.md) · [Değişiklikler](CHANGELOG.md) · [Test raporu](TEST_RAPORU_TR.md) · [UE aktarım raporu](UE_AKTARIM_RAPORU_TR.md) · [Kaynak ve testler](releases/Silkroad_PK2_Editor_v2_4_2_Source_Tests.zip)

## Lisans

[GPL-3.0-or-later](silkroad_pk2_bridge/LICENSE-GPL-3.0.txt)
