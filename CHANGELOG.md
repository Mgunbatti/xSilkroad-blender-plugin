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
