# Türkçe AI Instagram Klinik İçerik Sistemi

Doç. Dr. Özgür Karakoyun için ortopedi ve travmatoloji odaklı Instagram içerik üretim paneli.

## Özellikler

1. Konudan gönderi + story üretimi
2. Yüklenen görseli GPT Image ile gönderi/story tasarımına dönüştürme
3. Başlık ve hook metinlerini okunabilir şekilde görsel üzerine bindirme
4. Güncel ortopedi/travmatoloji konu önerileri sayfası
5. Caption + hashtag üretimi
6. 3-7 slaytlık carousel üretimi
7. Yüklenen görsellerde basit hasta bilgisi maskeleme
8. JSON tabanlı içerik arşivi

## Çıktılar

- Gönderi: `1080x1350`
- Story: `1080x1920`
- Carousel: `1080x1350`, 3-7 slayt

## Railway Environment Variables

```bash
OPENAI_API_KEY=sk-...
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=medium
OPENAI_IMAGE_SIZE=1024x1536
```

`gpt-image-2` için OpenAI Organization Verification gerekebilir. Doğrulama yoksa sistem fallback görselle çalışır; fakat gerçek GPT Image üretim/düzenleme aktif olmaz.

## Lokal çalıştırma

```bash
pip install -r requirements.txt
python main.py
```

Arayüz:

```text
http://localhost:8000
```

## API Endpointleri

```text
GET  /
GET  /health
GET  /suggest-topics
GET  /archive
GET  /archive/{job_id}
POST /create-content
POST /create-post   # eski endpoint uyumluluğu
```

`/create-content` form alanları:

```text
mode: topic | image
topic: string
tone: professional | educational | friendly
carousel_count: 3-7
mask_phi: true | false
upload: optional image file, only for image mode
```

## Hasta bilgisi uyarısı

Maskeleme özelliği kenar/bant alanlarını kapatır ve EXIF bilgisini temizler. OCR tabanlı kesin anonimleştirme değildir. Klinik paylaşım öncesi görselde hasta adı, protokol numarası, tarih, barkod, QR kod, yüz, telefon ve benzeri kişisel verilerin bulunmadığı kullanıcı tarafından kontrol edilmelidir.


## Railway Volume / Arşiv Ayarı

Kalıcı arşiv için Railway'de Volume oluşturup mount path olarak `/data` kullanın.

Environment Variables:

```bash
DATA_DIR=/data
OPENAI_API_KEY=sk-...
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=medium
OPENAI_IMAGE_SIZE=1024x1536
```

`ARCHIVE_DIR` adında secret/variable tanımlamayın. Arşiv otomatik olarak `DATA_DIR/archive/content_archive.json` dosyasına yazılır.


## Dil Seçenekleri

Bu sürümde içerik üretimi için üç dil seçeneği vardır:

- Türkçe
- English
- العربية

Dil seçimi şu alanlara uygulanır:

- Görsel üstü başlık ve hook
- Caption
- Hashtag
- Carousel slayt metinleri
- Alt banttaki uzmanlık/doktor etiketi

Arapça metin için `arabic-reshaper` ve `python-bidi` bağımlılıkları eklenmiştir.


## Video Story Özelliği

Bu sürümde `Görsel yükle` modunda video dosyası da yüklenebilir.

Desteklenen video formatları:

- MP4
- MOV
- M4V
- WebM
- AVI
- MKV

Kullanım:

1. `Görsel yükle` modunu seçin.
2. Video dosyasını yükleyin.
3. Dil ve konu alanını doldurun.
4. `Sadece Story` butonuna basın.

Kurallar:

- Video yalnızca Story için kullanılır.
- Video kırpılmaz.
- Aspect ratio korunur.
- Video, 1080x1920 story şablonu içindeki güvenli alana sığdırılır.
- Yatay videolar küçük görünür ama kırpılmaz.
- Dikey videolar çerçeve içine büyütülür/küçültülür ama crop uygulanmaz.


## Video Story Pillow/MoviePy Uyumluluk Notu

Pillow 10+ sürümlerinde `Image.ANTIALIAS` kaldırıldığı için MoviePy 1.0.3 video resize sırasında hata verebilir. 
Bu sürümde `media/video_story.py` içine uyumluluk yaması eklenmiştir:

```python
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
```

Bu nedenle video Story üretiminde `module "PIL.Image" has no attribute "ANTIALIAS"` hatası alınmamalıdır.


## Video Story MoviePy ImageClip Notu

MoviePy 1.0.3 `ImageClip()` fonksiyonunda PIL Image nesnesi yerine NumPy array bekleyebilir.
Bu sürümde Story arka planı şu şekilde dönüştürülür:

```python
bg_clip = ImageClip(np.array(bg_img)).set_duration(duration)
```

Bu, `"Image" object has no attribute "shape"` hatasını düzeltir.
