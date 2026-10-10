# SPDX-License-Identifier: GPL-3.0-or-later
"""English-first, Blender-language-independent localization for the editor.

Use English strings as stable message IDs. Users can select Turkish without
changing Blender's global language. Keep interpolation placeholders identical.
"""

TURKISH = {
    'Language': 'Dil',
    'Error: {error}': 'Hata: {error}',
    'PK2 Loading Status': 'PK2 Yükleme Durumu',
    'Scanning PK2...': 'PK2 taranıyor...',
    '{count} PK2 blocks scanned (total unknown)': '{count} PK2 bloğu tarandı (toplam bilinmiyor)',
    'Reading archive (engine has no block counter)': 'Arşiv okunuyor (motor blok sayacı sunmuyor)',
    'Cancel Scan': 'Taramayı İptal Et',
    'Loading complete': 'Yükleme tamamlandı',
    'Loading cancelled': 'Yükleme iptal edildi',
    'Could not open PK2': 'PK2 açılamadı',
    'Error or cancellation details below': 'Hata veya iptal ayrıntıları aşağıda',
    'Choose a PK2 to see loading progress': 'Yüklemeyi görmek için bir PK2 seç',
    '1. Open PK2 Archive': '1. PK2 Arşivini Aç',
    'PK2 engine ready': 'PK2 motoru hazır',
    'Install PK2 Engine': 'PK2 Motorunu Kur',
    'Open PK2...': 'PK2 Aç...',
    'Encryption key': 'Şifreleme anahtarı',
    '{count} PK2 archives available (main + linked)': '{count} PK2 arşivi hazır (ana + bağlı)',
    '2. Archive Contents': '2. Arşiv İçeriği',
    'Back': 'Geri',
    'Refresh': 'Yenile',
    'Search results (max 250)': 'Arama sonuçları (en fazla 250)',
    'Open Folder': 'Klasöre Gir',
    'Include animations': 'Animasyonları da çıkar',
    'Include map objects': 'Harita nesnelerini de çıkar',
    'Import Selected Model': 'Seçili Modeli Blender’a Aktar',
    '3. Edit / Save': '3. Düzenle / Kaydet',
    'Save .blend': '.blend Kaydet',
    'Export .fbx + PNG': '.fbx + PNG Aktar',
    'Source: {path}': 'Kaynak: {path}',
    'Save Selected Mesh to PK2': 'Seçili Mesh’i PK2’ye Kaydet',
    'PK2 write-back currently supports BMS meshes only.': 'PK2’ye geri kayıt şu anda yalnızca BMS mesh dosyaları içindir.',
    'Ready to open a PK2 archive': 'PK2 açmaya hazır',
    'No Blender window found. Run this tool in a 3D Viewport.': 'Blender penceresi bulunamadı. Aracı 3D Viewport içinden çalıştır.',
    'No 3D Viewport found. Open one and try again.': '3D Viewport bulunamadı. Bir 3D Viewport açıp yeniden dene.',
    'No 3D Viewport window region found.': '3D Viewport pencere bölgesi bulunamadı.',
    'Cannot switch to Object Mode. Select Object Mode and try again.': 'Object Mode’a geçilemedi. Object Mode’a geçip tekrar dene.',
    'PK2 engine is missing. Select Install PK2 Engine first.': 'PK2 motoru eksik. Önce PK2 Motorunu Kur seç.',
    'PK2 engine is missing. Click Install PK2 Engine first.': 'PK2 motoru eksik. Önce PK2 Motorunu Kur düğmesine bas.',
    '{archive} is scanning in the background; Blender remains responsive...': '{archive} arka planda taranıyor; Blender kullanılabilir...',
    '{archive}: {blocks} blocks scanned. Loading in the background...': '{archive}: {blocks} blok tarandı. Arka planda yükleniyor...',
    '{archive}: scanning in the background. This PK2 engine has no block counter...': '{archive}: arka planda taranıyor. PK2 motoru blok sayacı sunmuyor...',
    'Could not open PK2: {error}': 'PK2 açılamadı: {error}',
    'PK2 opened (some linked archives failed): {error}': 'PK2 açıldı (bazı bağlı arşivler okunamadı): {error}',
    'PK2 loading was cancelled': 'PK2 açılışı iptal edildi',
    'PK2 is loading in the background. Wait for the scan to finish.': 'PK2 arka planda yükleniyor. Taramanın tamamlanmasını bekle.',
    'PK2 is not ready. Use Open PK2.': 'PK2 hazır değil. PK2 Aç düğmesini kullan.',
    '{archive} | /{folder} | {count} items': '{archive} | /{folder} | {count} öğe',
    'Select a PK2 entry first.': 'Önce bir PK2 dosyası seç.',
    'PK2 engine is already installed': 'PK2 motoru zaten kurulu',
    'PK2API was installed but cannot be imported. Restart Blender.': 'PK2API kuruldu ancak içe alınamıyor. Blender’ı yeniden başlat.',
    'PK2 engine installed. Use Open PK2 to continue.': 'PK2 motoru kuruldu. Devam etmek için PK2 Aç seç.',
    'PK2 engine installed': 'PK2 motoru kuruldu',
    'This is a file. Use Import Selected Model instead.': 'Bu bir dosya. Seçili Modeli Blender’a Aktar düğmesini kullan.',
    '{count} search results shown (max 250)': '{count} arama sonucu gösteriliyor (en fazla 250)',
    'Select a BSR/BMS model first.': 'Önce bir BSR/BMS modeli seç.',
    '{extension} is not a supported 3D asset': '{extension} desteklenen bir 3D varlık değil',
    'Missing Silkroad importer for {extension}': '{extension} için içe aktarma operatörü bulunamadı',
    'Select a BSK/BSR armature before importing BAN.': 'BAN aktarmadan önce BSK/BSR iskeletini seç.',
    'Import did not finish: {result}': 'İçe aktarma tamamlanamadı: {result}',
    'Import created no objects. Check the BSR and its dependencies.': 'Nesne oluşturulmadı. BSR ve bağlı dosyaları kontrol et.',
    ' | {count} optional files missing': ' | {count} isteğe bağlı dosya eksik',
    'Imported into Blender: {path} | {count} objects{issues}': 'Blender’a aktarıldı: {path} | {count} nesne{issues}',
    'Imported into Blender: {path} | {count} objects': 'Blender’a aktarıldı: {path} | {count} nesne',
    'Imported into Blender: {path} | {count} objects | {missing} optional files missing': 'Blender’a aktarıldı: {path} | {count} nesne | {missing} opsiyonel dosya eksik',
    'Only a selected mesh can be saved back to PK2.': 'PK2’ye geri kayıt için bir Mesh seçmelisin.',
    'A UV map is required to save BMS.': 'BMS kaydı için UV Map gerekli.',
    'Triangulate all mesh faces (3 vertices) before saving BMS.': 'BMS için bütün yüzleri üçgenleştir (3 vertex).',
    'BMS supports at most 65535 vertices.': 'BMS en fazla 65535 vertex destekliyor.',
    'Apply mesh scale first: Ctrl+A > Scale.': 'Önce Mesh Scale uygula: Ctrl+A > Scale.',
    'BMS export operator is not registered.': 'BMS dışa aktarma operatörü kayıtlı değil.',
    'BMS export failed: {result}': 'BMS export başarısız: {result}',
    'BMS output file was not created. Check Blender console.': 'BMS çıktısı oluşturulmadı. Blender konsolunu kontrol et.',
    'The saved BMS file has an invalid signature.': 'Kaydedilen BMS dosyasının imzası geçersiz.',
    'I approve backing up and modifying the PK2 archive': 'PK2 arşivinin yedeklenmesini ve değiştirilmesini onaylıyorum',
    'WARNING: The original PK2 will be modified!': 'DİKKAT: Orijinal PK2 değiştirilecek!',
    'Mesh: {name}': 'Mesh: {name}',
    'PK2: {name}': 'PK2: {name}',
    'File: {path}': 'Dosya: {path}',
    'Full backup requires about twice the PK2 archive size in free space.': 'Tam yedek için yaklaşık PK2 boyutunun iki katı boş alan gerekli.',
    'Confirmation not given. PK2 was not modified.': 'Onay verilmedi. PK2 değiştirilmedi.',
    'Only a BMS entry originating from a PK2 can be saved.': 'Yalnızca PK2 kaynaklı bir BMS kaydedilebilir.',
    'Saved to PK2. Original backup: {backup}': 'PK2’ye kaydedildi. Orijinal yedek: {backup}',
    'BMS saved to PK2; full backup: {backup}': 'BMS PK2’ye yazıldı; tam yedek: {backup}',
    'Could not reopen PK2: {error}': 'PK2 tekrar açılamadı: {error}',
    'Could not pack textures: {error}': 'Texture’lar paketlenemedi: {error}',
    'Package PNG textures': 'PNG kaplamalarını paketle',
    'Export active animation': 'Aktif animasyonu aktar',
    'FBX exported: {name}, PNG: {converted}, missing: {missing}. Check TextureReport.txt.': 'FBX tamam: {name}, PNG: {converted}, eksik: {missing}. TextureReport.txt dosyasını kontrol et.',
    'Scan cancelled. Existing PK2 was not modified.': 'Tarama iptal edildi. Mevcut PK2 değiştirilmedi.',
    'FBX extension must be .fbx': 'FBX uzantısı .fbx olmalı',
    'Output folder does not exist: {path}': 'Çıktı klasörü bulunamadı: {path}',
    'Select at least one Mesh (Armature is recommended).': 'En az bir Mesh seçmelisin (Armature önerilir).',
    'Blender FBX export failed: {result}': 'Blender FBX export başarısız: {result}',
    'Blender did not generate an FBX output file': 'Blender FBX çıktı dosyası oluşturmadı',
    'PK2API is missing. Install the PK2 engine from the Blender panel.': 'PK2API eksik. Blender panelinden PK2 motorunu kur.',
}


def translate(message, language='EN', **params):
    """Format an English message in the selected locale, without evaluating code."""
    if language == 'TR':
        message = TURKISH.get(message, message)
    return message.format(**params) if params else message

TECHNICAL_ERRORS = {
    'PK2 path must be a string': 'PK2 yolu metin olmalı',
    'Invalid BMS data': 'Geçersiz BMS verisi',
    'Invalid BMS name length': 'Geçersiz BMS isim uzunluğu',
    'Invalid BMT material count': 'Geçersiz BMT materyal sayısı',
    'Enter at least 2 characters to search.': 'Arama için en az 2 karakter gir.',
    'PK2 write-back currently supports valid BMS meshes only': 'PK2 geri kaydı yalnızca geçerli BMS mesh dosyalarını destekler',
    'No permission to write PK2 archive': 'PK2 arşivine yazma izni yok',
    'The archive entry is not a valid BMS file': 'Arşivdeki dosya geçerli BMS değil',
    'Not enough disk space: approximately 2x PK2 size is required for staging and backup': 'Yetersiz disk alanı: geçici dosya ve yedek için yaklaşık 2 kat PK2 boyutu kadar boş alan gerekli',
    'PK2API add_file failed': 'PK2API add_file başarısız',
    'PK2 BMS verification failed after writing': 'Yazma sonrası PK2 BMS doğrulaması başarısız',
    'BSR file is incomplete or corrupted': 'BSR dosyası eksik veya bozuk',
    'Invalid reference length in BSR': 'BSR içindeki referans uzunluğu geçersiz',
    'Invalid material count in BSR': 'BSR içindeki materyal sayısı geçersiz',
    'Invalid mesh count in BSR': 'BSR içindeki mesh sayısı geçersiz',
    'Invalid animation count in BSR': 'BSR içindeki animasyon sayısı geçersiz',
}

TECHNICAL_PREFIXES = {
    'Absolute PK2 path is not allowed: ': 'Mutlak PK2 yolu kabul edilmez: ',
    'Invalid PK2 path: ': 'Geçersiz PK2 yolu: ',
    'PK2 archive not found: ': 'PK2 arşivi bulunamadı: ',
    'PK2 folder not found: ': 'PK2 klasörü bulunamadı: ',
    'This file type cannot be opened as a 3D model: ': 'Bu dosya türü 3D model olarak açılamaz: ',
    'Entry not found in PK2: ': 'PK2 içinde dosya bulunamadı: ',
    'Invalid relative PK2 path: ': 'Geçersiz göreli PK2 yolu: ',
    'Required model dependency was not found in PK2 archives: ': 'Bağlı model dosyası PK2 arşivlerinde bulunamadı: ',
    'Original BMS not found in PK2: ': 'Arşivde orijinal BMS bulunamadı: ',
    'Unsupported file extension: ': 'Desteklenmeyen dosya uzantısı: ',
    'File not found: ': 'Dosya bulunamadı: ',
    'Invalid BMS signature: ': 'Geçersiz BMS imzası: ',
    'Invalid BSR signature: ': 'Geçersiz BSR imzası: ',
    'Invalid BSK signature: ': 'Geçersiz BSK imzası: ',
    'Invalid BAN signature: ': 'Geçersiz BAN imzası: ',
    'Invalid DOF signature: ': 'Geçersiz DOF imzası: ',
    'Invalid NVM signature: ': 'Geçersiz NVM imzası: ',
    'FBX extension must be .fbx': 'FBX uzantısı .fbx olmalı',
    'Output folder does not exist: ': 'Çıktı klasörü bulunamadı: ',
    'Select at least one Mesh (Armature is recommended).': 'En az bir Mesh seçmelisin (Armature önerilir).',
    'Blender FBX export failed: ': 'Blender FBX export başarısız: ',
    'Blender did not generate an FBX output file': 'Blender FBX çıktısı oluşturmadı',
}


def translate_error(message, language='EN'):
    """Localize known helper/engine diagnostics without masking unknown errors."""
    if language != 'TR':
        return message
    if message in TECHNICAL_ERRORS:
        return TECHNICAL_ERRORS[message]
    if message in TECHNICAL_PREFIXES:
        return TECHNICAL_PREFIXES[message]
    for prefix, replacement in TECHNICAL_PREFIXES.items():
        if message.startswith(prefix):
            return replacement + message[len(prefix):]
    return TURKISH.get(message, message)
