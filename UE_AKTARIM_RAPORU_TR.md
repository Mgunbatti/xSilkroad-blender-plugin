# Jangan UE aktarımı — v2.4.2

Gerçek Holigan Data.pk2 ve Map.pk2 ile Blender 5.2.2 → Unreal Engine 5.8.3. Ana şehir ve yakın çevresi: 16 bölge, X=166–169 ve Y=96–99. Bütün Çin haritası bu kapsamda değildir.

## Sonuç

- 16 arazi ve 219 farklı model; toplam 235 Static Mesh.
- 2.128 model yerleşimi ve 16 arazi: yeni projede 2.144 Static Mesh Actor.
- 379 farklı PNG içeriği ve sahnede kullanılan 579 materyal.
- Saray ve altın ejder kaynak konumlarında mevcut; çatı ve sur dış yüzleri görünür.
- Üretim betiğiyle yeni UE projesi oluşturuldu, kaydedilip yeniden açıldı. 2.128 konum ve dönüş kontrolü geçti: en büyük konum farkı 0 cm, yaw farkı 0,000236 derece.
- Kullanıcının açık projesi ayrıca onarıldı ve kaydedildi. Eski navigasyon nesneleri silinmeden gizlenip Archive/NavigationOnly klasörüne taşındı; bu nedenle açık projede fiziksel actor sayısı yeni projeden fazla olabilir.

## Düzeltmeler

Önceki aktarım NVM navigasyon nesnelerine dayanıyordu. Görsel şehir yerleşimlerinin bir kısmı yalnızca Map.pk2 içindeki .o2 dosyalarındadır. Aktarım artık bu dosyalar varsa görsel object.ifo tablosunu ve .o2 kayıtlarını kullanır. Dosya yolu Y/X.o2 şeklindedir. Blok ve LOD kapsamlarında tekrarlanan kayıtlar RID, UID ve varlık kimliğiyle tekilleştirilir. Çelişen kayıt, bozuk uzunluk ve geçersiz sayılar hata verir. .o2 yoksa mevcut NVM akışı korunur. Parçacık kaynakları statik modele dönüşmez; atlanan efektler raporlanır. Bu kaynak kümesinde atlanan efekt yoktur.

BMS okurken Y/Z eksenlerinin yer değiştirmesi üçgen yönünü ters çeviriyordu. Üçgen sırası dönüşüme göre düzeltildi. BMS kaydederken oyun biçiminin sırası geri uygulanır. Gerçek çatı mesh'inde 532 yüz kaynak normalleriyle aynı yönde; yeniden kaydedilen BMS'nin yüz indeksleri kaynakla aynı. Çift taraflı materyalle hatayı gizlemek gerekmedi.

Önceki yatay dönüş düzeltmesi korunur: UE dönüşleri isimli pitch/yaw/roll parametreleriyle uygulanır ve sahnede doğrulanır. Mevcut doku, rig, animasyon ve FBX+PNG akışı korunur. Daha önce bildirilen iki kaynak mesh'teki toplam 12 geçersiz UV loop düzeltmesi manifestte kayıtlıdır.

## Eklenti kullanım oranı

Varlık sayısına göre **235/235 = %100**. Arşiv okuma, bağımlılık çözme, Blender içe aktarma ve FBX+PNG üretimi eklenti koduyla yapıldı. Bu yenilemede 219 model yeniden işlendi; 16 arazi önceki gerçek eklenti aktarımından korundu. UE içeriklerini eklentinin üretim aktarım betiği oluşturdu. Açık projeyi koruyan onarım ve doğrulama betikleri ayrıca çalıştırıldı. Oran toplam çalışma süresi veya fare tıklaması yüzdesi değildir.

## Testler

- 87 birim/regresyon testi geçti; altı importer yönlendirmesi ve önceki testler korunuyor.
- Gerçek BMS, Blender 5.2.2'de okundu ve yeniden kaydedildi; 532 yüzün yönü ve kaynak yüz indekslerinin korunması doğrulandı.
- Güncel 219 model gerçek PK2 → Blender → FBX+PNG zincirinden geçti. 16 arazi önceki doğrulanmış çıktıdan kullanıldı.
- Native extension ZIP oluşturuldu, izole Blender profiline kuruldu ve 2.4.2 operatör kaydı doğrulandı.
- Yeni UE projesi üretim betiğiyle oluşturuldu, kaydedilen harita ikinci UE işleminde yeniden açılarak 2.144 statik nesne kontrol edildi.
- Açık UE sahnesindeki 2.128 yerleşim, materyaller ve iki eksik yapı kontrol edildi. Saray, ejder ve genel görünüm ekran görüntüleri Preview klasöründe bulunur.

Bu sürümde panel düğmesi fiziksel fareyle baştan sona yeniden çalıştırılmadı; düğmenin kullandığı aktarım işi gerçek Blender'da ve üretim UE betiği gerçek Unreal'da çalıştırıldı. Önceki tam operatör testi tarihsel PluginTestReport.json dosyasında bulunur. FreshValidation.json güncel yeni proje testini, VisualValidation.json güncel açık proje kontrolünü ve VisualRepairReport.json onarımı gösterir. ImportReport.json üretim betiğinin yeni proje sonucudur.

## Kullanım

Eklenti ZIP'ini Blender'da Install from Disk ile kurun. Data.pk2 açın, taramanın bitmesini bekleyin ve **4. Unreal Projesi → Jangan UE Projesi Oluştur** düğmesine basın. Yeni proje adı seçin. Aynı oyun klasöründeki Map.pk2 mevcut olmalı. Dolu proje üzerine yazılmaz. FBX içe aktarma ve materyal derleme ilk çalıştırmada birkaç dakika sürebilir; panel durumunu ve proje logunu takip edin.

Hazır xSilkroadJangan_Plugin.uproject dosyasını UE'de açabilirsiniz. Başlangıç haritası /Game/Jangan/Maps/Jangan. SourceAssets/manifest.json kaynakları, yerleşimleri ve kullanılan .o2 dosyalarını listeler.

## Sınırlar ve kaynaklar

Statik şehir çevresi aktarılmıştır. NPC, görev, oynanış, hareketli su, rüzgâr ve parçacık animasyonları eklenmedi. Rig içeren çevre nesneleri mevcut pozlarıyla statikleştirilir. Paketlenmiş oyun ve performans testi yapılmadı. Tüm oyun varlıkları veya tüm arazi UV dönüşleri oyun içi görüntüyle birebir karşılaştırılmadı.

Özgün kaynak telif ve GPL koşulları korundu. Oyun verileri Git deposuna veya eklenti kaynak/test ZIP'ine eklenmedi. .o2 düzeni gerçek arşiv kayıtlarıyla doğrulandı; karşılaştırma için [harita biçimi notları](https://github.com/y-xLeo/ikarus-map-editor/blob/main/SRO_MAP_FORMAT_NOTES.md) incelendi.
