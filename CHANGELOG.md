# 2.4.2 — 10 Ekim 2026

- UE aktarımı nesne yerleşimlerini mevcutsa Map.pk2 içindeki .o2 görsel kayıtlarından alır; yalnızca navigasyon nesneleriyle sınırlı kalmaz. .o2 bulunmazsa NVM akışı korunur.
- Saray, altın ejder, yan binalar ve dekorların kaynak yerleşimleri aktarılır. LOD/blok kayıtlarında yinelenen nesneler tekilleştirilir; bozuk kayıtlar hata verir.
- BMS Y/Z dönüşümünde üçgen sırası düzeltilir; çatı ve surların dış yüzleri görünür. BMS kaydederken oyun biçiminin yüz sırası geri uygulanır.
- Gerçek çatı modelinde 532 yüzün kaynak normalleriyle uyumu ve BMS yüz indekslerinin değişmeden geri kaydı doğrulandı.

# 2.4.1 — 10 Ekim 2026

- UE Rotator parametreleri isimleriyle verilir; yatay dönüşün pitch eksenine uygulanıp binaları yatırması düzeltildi.
- Her nesnenin pitch, roll ve yaw sonucu kaydetmeden önce kaynak açıyla kontrol edilir. Hatalı veya geçersiz dönüş aktarımı durdurur.
- Güneş ve ilk görünüm kamerasının dönüş parametreleri düzeltildi.
- Gerçek açık UE 5.8.3 sahnesinde 577 yerleşim kontrol edildi; 301 eğilmiş nesne düzeltildi, konumları korundu.

# 2.4.0 — 10 Ekim 2026

- Panelden ayrı Jangan Unreal projesi oluşturma eklendi.
- 16 NVM harita parçası, tekrar kullanılan BSR modelleri ve kaynak nesne yerleşimleri otomatik aktarılır.
- FBX+PNG çıktıları UE'de Static Mesh ve materyallere dönüştürülür; saydam yaprak dokuları maske olarak bağlanır.
- Ağaç iskeletleri statik çevre için mevcut pozlarıyla sabitlenir. Geçersiz UV değerleri kayda alınarak düzeltilir.
- Aktarım geçici Blender sahnesinde çalışır; mevcut nesneler, materyaller ve panel ayarları korunur.
- Kurulu Unreal editörü otomatik bulunur. İşlem sonucu, eksik varlıklar ve nesne sayıları raporlanır; dolu proje klasörü korunur.
- 75 birim testi, gerçek PK2 → Blender → UE 5.8.3 aktarımı ve izole ZIP kurulumu doğrulandı.

# 2.3.3 — 10 Ekim 2026

- PK2 listesindeki desteklenen dosya adları doğrudan içe aktarılabilir.
- NVM için Data ve Map klasörlerinin kullanımı düzeltildi; harita dokuları ve nesne bağımlılıkları birlikte çıkarılır.
- DOF blokları ve ek nesnelerin bağlı model, materyal ve dokuları yüklenir.
- NVM zemininin eksik UV koordinatları düzeltildi.
- Geçersiz dosya, yanlış uzantı ve boş aktarım sonucu hata olarak bildirilir. Eksik bağlı dosyalar ve ayrıntılı hata kayıtları Blender Text Editor'dan okunabilir.
- İçe aktarma çağrılarının Blender 5.2 görünüm ve nesne modu uyumluluğu düzeltildi.
- Mesh, iskelet, animasyon ve FBX + PNG aktarımı gerçek oyun dosyalarıyla test edildi.
- Eklentinin kurulum paketi ve manifest doğrulaması düzeltildi.
