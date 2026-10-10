# 2.3.3 — 10 Ekim 2026

- Altı desteklenen formatın PK2 satır adı doğrudan doğru import operatörünü çağırır; satır indeksinin aktarılması yanlış seçili dosyanın importunu önler. Klasöre gir çağrısı dosyada da import yapar.
- NVM'ye ayrı Data ve Map kökleri verilir. Kullanılan tile ID'lerine göre tile2d.ifo ve ilgili dokular çıkarılır.
- NVM nesne seçeneği object.ifo → BSR/CPD → mesh/BMT/doku zincirini çıkarır. DOF block ve isteğe bağlı object resource zincirleri aynı çözümlemeyi kullanır.
- CPD resource çözümlemesi döngülere karşı tekrarı engeller. Arşiv yolları mevcut traversal kontrolünden geçirilir. İsteğe bağlı önce eksik görülen bağımlılığın sonradan zorunlu istenmesi hata üretir.
- Jelly execute çağrıları ortak doğrulama ve sonuç kontrolü kullanır. Yanlış uzantı, geçersiz imza, LoadFile=False, sıfır geometri ve boş BAN action artık FINISHED değildir.
- BinaryReader okuma/seek sınırlarını kontrol eder ve konum içeren hata verir. LoadFile'ın gerçek parser hatası tekrar yükseltilir; traceback log'a yazılır.
- Başarılı ve başarısız importlar format bazlı Blender Text log'larına yazılır. PK2 hazırlık hataları ve isteğe bağlı bağımlılıklar ayrıca kaydedilir. Materyal resim yükleme hatası artık sessizce geçilmez.
- NVM hexadecimal bölge adı kontrolü düzeltildi; eksik tile ID/doku log'a yazılır. Tile başına boş kalan UV koordinatları dolduruldu.
- Eksik isteğe bağlı BSR skeleton/animasyonlar log'lanır ve kalan mesh akışı korunur.
- Mevcut Blender 5 slotted action, NLA, mesh/skeleton ve v2.3.2 PNG save_render düzeltmeleri korundu. Başarısız nested importta mod ve aktif collection geri yüklenir.
- Extension manifest'in eski tagline/izin metinlerinin Blender'ın 64 karakter sınırını aşması düzeltildi.
- v2.3.2'nin save_render, boş DDS format enum'u ve özel geçici sahne testleri korundu; 12 yeni unittest metodu ve gerçek Blender test scriptleri eklendi.

Kaynak temeli: kullanıcının verdiği **v2.3.2 Source_Tests ZIP**. İçindeki bütün eklenti kaynakları başlangıçta bulunan v2.3.2 PNG Fix kaynaklarıyla byte-byte aynı çıktı. Tam paketteki 54 önceki test esas alındı; 12 yeni unittest metodu eklendi. Önceki konuşmanın erişilebilir API görünümünde bağımsız yüklenmiş dosya ekleri yoktu; ZIP içindeki altı Jelly kaynağı kullanıldı. Orijinal ZIP ve dosyaların SHA-256 bilgileri SOURCE_PROVENANCE.json içindedir.
