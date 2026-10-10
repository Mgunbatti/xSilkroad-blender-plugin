# Test ve kaynak denetimi — 2.3.3

10 Ekim 2026. Blender **5.2.2 LTS**, build d13f752e3b9c (15 Eylül 2026), Windows.

## Kaynak doğrulaması

v2.3.2 Source_Tests ZIP temel alındı. İçindeki bütün eklenti dosyaları başlangıçtaki v2.3.2 PNG Fix paketiyle byte-byte aynı. Tam paketin 54 testi ham kaynakta da geçti. Son kaynakta 54 eski + 12 yeni = **66 unittest** geçti. Altı dosya biçiminin kaynakları ve lisans başlıkları korundu. SHA-256 ve değişen/değişmeyen dosya listesi SOURCE_PROVENANCE.json içinde.

## Gerçek testler

Yerel Holigan Data.pk2 ve kardeş Map/Media/Particles arşivleri salt okunur açıldı. Paketlenen kaynaklara hiçbir oyun binary'si veya oyun FBX/PNG çıktısı eklenmedi. Blender background modunda gerçek UI region → VIEW_3D WINDOW override ile panel çağrısı çalıştırıldı; fiziksel fareyle UI tıklaması yapılmadı. Son satır düğmesi/entry_index seçimi ayrıca gerçek bpy ile test edildi.

| Format / seçenek | Gerçek örnek | Sahne nesneleri | Mesh vertex toplamı | Sonuç |
|---|---|---:|---:|---|
| .bms | prim/mesh/mob/europe/wolf01.bms | 1 | 371 | Geçti |
| .bsk | prim/skel/mob/europe/wolf.bsk | 1 | 0 | Geçti |
| .ban | prim/ani/mob/europe/wolf/wolf_stand01.ban | 1 | 0 | Geçti |
| .bsr | res/mob/arabia/baruswolf_adonis1.bsr | 4 | 1223 | Geçti |
| FBX+PNG | — | — | — | Geçti |
| FBX roundtrip | — | 4 | — | Geçti |
| .nvm | navmesh/nv_1315.nvm | 1 | 9409 | Geçti |
| .dof | dungeon/asiam/r1_cv/pha_cv.dof | 829 | 435132 | Geçti |
| .nvm (nesneler açık) | navmesh/nv_1315.nvm | 22 | 12182 | Geçti |
| .dof (nesneler açık) | dungeon/asiam/r1_cv/pha_cv.dof | 2479 | 709098 | Geçti |

Nesne/vertex sayıları sahnede ölçüldü; başarısızlığın yalnızca FINISHED kontrolüyle kaçması engellendi. JSON'daki `actions` ve `images` Blender oturumundaki toplam datablock sayılarını gösterir; yeni eklenen sayılar olarak yorumlanmamalı. BSR örneği 37 kemik ve NLA slotlarına bağlı 102.494 keyframe ile doğrulandı. Standalone BAN'da da gerçekten bağlı NLA keyframe'leri kontrol edildi. FBX+PNG export iki dokuyu dönüştürdü, eksik doku raporu boştu. FBX yeniden içe alındı; rig ve okunabilir PNG image verileri doğrulandı.

Ek olarak: altı formatta bozuk/sadece-imza dosyası ve yanlış uzantı için **12 gerçek bpy hata senaryosu** geçti. Format log'ları traceback içeriyor; hata FINISHED olmuyor. Synthetic unittest'ler recursive DOF/BSR/BMT extraction, NVM Map kökü ve tile extraction, object.ifo kaynakları/eksik ID'ler, traversal, binary sınırları, altı LoadFile çağrı imzası, False/boş sonuç/gerçek exception durumlarını kapsar. Önceki PK2 geri yazma, async scan, viewport, slotted animation, i18n ve PNG regresyon testleri de geçti.

Native Blender extension ZIP build ve ZIP manifest doğrulaması geçti. ZIP, çalışma klasöründe izole Blender config/extensions profiline install-file ile kuruldu, etkinleştirildi ve yeni Blender başlangıcında operatör kayıtları doğrulandı. Kullanıcının asıl Blender tercihlerine yazılmadı.

## Altı çağrı zincirinin denetimi

| Uzantı | Operatör | Çıkarma ve bağımlılık | Sahne doğrulaması |
|---|---|---|---|
| .bms | jmxvbms_0110 | Seçili mesh; materyal için ilgili BSR gerekli | Yeni mesh + vertex |
| .bsk | jmxvbsk_0110 | BSK; signature 0101 (operatör adı tarihsel olarak 0110) | Yeni armature + kemik |
| .ban | jmxvban_0102 | BAN; önceden seçili uygun rig | Yeni action; gerçek testte NLA slot/keyframe |
| .bsr | jmxvres_0109 | BMS, isteğe bağlı BMT/doku/BSK/BAN | Mesh, rig, material, bağlı NLA |
| .dof | jmxvdof_0101 | Block BSR → mesh/BMT/doku; seçeneğe göre object BSR | Yeni mesh vertex; block/object dalları |
| .nvm | jmxvnvm_1000 | Data/navmesh; ayrı Map/tile2d.ifo + kullanılan dokular; seçeneğe göre object.ifo → CPD/BSR | 97×97 height mesh + UV; nesne dalı |

Seçim → satır indeksi → uzantı kontrolü → prepare_asset → gerçek Jelly operatörü → nested operatörler aynı viewport context'inde yürür. Map ve Data kökleri karıştırılmaz. İsteğe bağlı eksikler listelenir; zorunlu mesh/resource yoksa import durur. LoadFile exception, yanlış extension/signature, bozuk binary, boş geometri/rig/action başarı sayılmaz. Her formatın Text log'u ve PK2 hazırlık hata kaydı vardır.

## Pratik sınırlar

Bu sonuçlar bütün 23.370 BMS, 6.064 NVM veya her Silkroad sürümüne garanti değildir. Seçilmiş gerçek örnekler uçtan uca test edildi. Oyun içi görüntü ile bütün tile dönüş/flag varyantları, her skeleton/animation kombinasyonu ve her BMT varyantı görsel olarak karşılaştırılmadı. Eski Jelly NVM düzeni korunur: 96×96 tile ve 97×97 height vertex bekler; farklı/eksik layout açık hata verir. NVM/DOF import testleri, bu formatlara export/PK2 geri yazma desteği anlamına gelmez. NVM exporter hâlâ tamamlanmamış olduğu için açılmadı.

Hata sırasında daha önce oluşturulan nesneler sahnede kalabilir; başarısız işlem log'da görünür. Standalone BMS için güvenilir olmayan materyal tahmini yapılmaz. Geçici Data/Map workspace'leri resim dosyaları Blender'da kullanılırken korunur. Paketlerin GPL koşulları ve telif başlıkları saklanmıştır.
