# Jangan UE aktarımı — v2.4.0

10 Ekim 2026. Gerçek Holigan Data.pk2 ve Map.pk2 arşivleriyle Blender 5.2.2 LTS → Unreal Engine 5.8.3 aktarımı tamamlandı.

## Kapsam ve sonuç

Ana Jangan şehri, surları ve yakın çevresi aktarıldı. Harita 16 NVM parçasından oluşur: X bölge indeksleri 166–169, Y indeksleri 96–99 (`60a6`–`63a9`). Bu kapsam bütün Çin avlanma haritası değildir.

- 16 arazi, her biri 9.409 vertex ve 192 × 192 metre.
- 140 farklı model kaynağı, 577 nesne yerleşimi.
- UE'de 156 farklı Static Mesh ve 593 Static Mesh Actor.
- 323 farklı PNG içeriği; sahnede kullanılan 509 materyal.
- UE aktarımında sıfır hata; bütün kayıtlı yerleşimler yeniden açılan haritada bulundu.
- 577 konum kontrolünde en büyük sapma: 0 cm. FBX eksen dönüşümü ayrı kalibrasyon modeliyle ölçüldü.

Ortak modeller bir kere içe aktarılır; tekrar eden binalar ve ağaçlar aynı UE varlığını kullanır. Kaynak birim, UE'de 10 cm olarak eşlenir. Başlangıç haritası `/Game/Jangan/Maps/Jangan`.

## Eklenti kullanım oranı

Ölçüm varlık sayısına dayanır: **156 / 156 = %100**. Bu 16 NVM arazi ve 140 BSR modelinin arşivden çıkarılması, bağımlılıklarının bulunması, Blender'a aktarılması ve FBX+PNG üretilmesi eklentinin koduyla yapıldı. İşlem fiziksel fare tıklamasıyla değil, panel düğmesinin kullandığı gerçek Blender operatörü üzerinden çalıştırıldı.

| Aşama | İlk aktarım | v2.4.0 düğmesi |
|---|---|---|
| PK2 okuma ve bağımlılık çıkarma | Eklenti | Eklenti |
| NVM/BSR → Blender | Eklenti | Eklenti |
| FBX ve PNG üretimi | Eklenti; seçim/ölçek için ek aktarım betiği | Eklenti içinde geçici sahne ve seçim yönetimi |
| Harita seçimi, yerleşim manifesti, iskeleti sabitleme | Ayrı aktarım betiği | Eklentiye eklendi |
| UE proje, doku, materyal ve harita oluşturma | Ayrı UE betiği | Eklentinin paketlediği ve otomatik çalıştırdığı UE betiği |

Son akışın tamamı **Jangan UE Projesi Oluştur** düğmesi tarafından başlatılıp takip edilir. Blender ve Unreal motorları kendi işleri için kullanılmaya devam eder. %100 değeri toplam çalışma süresinin veya kod satırlarının ölçümü değildir; işlenen oyun varlıklarının oranıdır.

## Karşılaşılan sorunlar ve düzeltmeler

1. Arşivde başka haritalar için kullanılan Jangan kopyaları vardı. Ana şehir ve yakın çevresi için 16 kaynak bölge seçildi; komşu NVM'de tekrar görünen nesneler RID üzerinden elendi.
2. İlk toplu FBX denemesinde Blender seçimi bazı kaynaklarda yalnızca iskeleti, arazi kaynaklarında ise hiçbir mesh'i içeriyordu. Bütün çıktı mesh'leri açıkça seçildi. İskeletli ağaçların mevcut pozları değerlendirildi ve statik geometriye sabitlendi.
3. FBX materyal adlarında boşluk, tire ve sayısal ekler vardı. Slot adları normalize edilerek doğru kaynak materyalle eşleştirildi. Eşleşmeyen slot artık açık hata verir.
4. Otomatik FBX materyal bağlantıları ilk komut satırı kontrolünde doğrulanamadı. PNG dokuları ayrı içe alınıp Base Color ve gerekiyorsa Opacity Mask bağlantıları açık oluşturuldu. Yaprak dokularına çift taraflı masked materyal verildi.
5. İki mesh'te geçersiz UV değerleri bulundu: `W_CD_mc_cata` için 5, `CJ_lamp02` için 7 loop. Bu 12 değere (0,0) verildi; düzeltmeler manifestin `repairs` listesinde tutuldu. Bu yüzlerde kaynak UV yeniden oluşturulmuş değildir.
6. Blender metre / UE santimetre ve sağ/sol el eksen farkı, kalibrasyon FBX'iyle ölçüldü. Harita konumları ve yaw dönüşümleri buna göre uygulandı.
7. UE 5.8 kamera API'sinin ek `viewport_config_key` parametresi düzeltildi.
8. Importer'ların aynı materyal adını yeniden kullanması açık Blender sahnesini etkileyebilirdi. Aktarım geçici sahnede izole edildi; mevcut materyal adları ve verileri işlem sonunda korundu.

## Doğrulama

- 75 birim/regresyon testi geçti. Eski PK2, altı importer dispatch, materyal/animasyon, dil ve PNG testleri korundu. Yeni testler bölge konumları, dosya tablosu, CPD döngüsü, yabancı RID, mükerrer UID, geçersiz konum, mevcut proje koruması ve taşınabilir proje üretimini kapsar.
- Yeni `silkroad_editor.export_ue_project` operatörü gerçek arşivlerle baştan sona çalıştırıldı. 156 varlık ve 593 UE sahne nesnesi doğrulandı.
- Blender'daki başlangıç nesneleri, materyal adı/rengi ve panel seçeneklerinin değişmediği gerçek bpy ile kontrol edildi.
- Native extension ZIP build ve izole Blender profiline kurulum geçti. Yeni operatör kurulu pakette kayıtlı.
- Kaydedilen UE haritası yeniden açıldı. Bütün arazi ölçüleri, mesh materyalleri ve 577 nesne konumu kontrol edildi. UE'de genel görünüm ve şehir kapısı görüntüleri üretildi.

## Kullanım

Eklentiyi güncelleyin, Data.pk2 arşivini açın ve tarama bitince **4. Unreal Projesi → Jangan UE Projesi Oluştur** düğmesine basın. Yeni bir proje adı seçin. Unreal otomatik bulunur; bulunamazsa UnrealEditor-Cmd.exe yolunu belirtin. Dolu proje klasörünün üstüne yazılmaz. Aktarım panelden takip ve iptal edilebilir.

Hazır `.uproject` dosyasını UE'de açın. `SourceAssets/manifest.json` kaynak ve yerleşimleri; `ImportReport.json` UE sonucunu; `PluginTestReport.json` eklenti testini; `VisualValidation.json` harita kontrolünü içerir.

## Sınırlar

Statik şehir çevresi aktarılmıştır. NPC, görev, oynanış, rüzgâr animasyonu ve hareketli su sistemi bu aktarımın parçası değildir. Paketlenmiş çalıştırılabilir oyun veya performans testi yapılmadı. Panelin modal akışı fiziksel fare ile ayrıca test edilmedi; aynı düğmenin Blender operatörü uçtan uca çalıştırıldı. Oyun içi görüntüyle bütün terrain tile flag/dönüş varyantlarının birebir eşleşmesi doğrulanmadı; mevcut importer UV davranışı korunur. UE ışıklandırması ayrı oluşturuldu.

Eklenti kaynaklarının özgün telif ve GPL başlıkları korundu. Oyun varlıklarının hakları kaynak oyuna aittir; oyun verileri eklenti kaynak/test ZIP'ine veya Git deposuna eklenmedi.
