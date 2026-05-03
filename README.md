# Türkçe AI Instagram Agent

Doç. Dr. Özgür Karakoyun için Türkçe ortopedi ve travmatoloji Instagram içerik sistemi.

## Bu sürümdeki akış

1. Kullanıcı resim yüklemez.
2. Kullanıcı bir konu yazar veya güncel konu önerilerinden seçer.
3. Sistem Türkçe hook, açıklama ve hashtag üretir.
4. GPT Image modeli konuya göre medikal arka plan görseli üretir.
5. Sistem okunabilir başlık, hook ve alt iletişim bölümünü görselin üzerine kendisi basar.
6. Sadece iki çıktı oluşturulur:
   - Gönderi: `1080x1350`
   - Story: `1080x1920`

## Alt bilgi

Her gönderi ve story altında otomatik olarak şu bilgiler yer alır:

- Doç. Dr. Özgür Karakoyun
- www.ozgurkarakoyun.com
- Tel: 0545 919 54 13

## Railway environment variables

```bash
OPENAI_API_KEY=sk-...
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=medium
OPENAI_IMAGE_SIZE=1024x1536
OPENAI_TEXT_MODEL=gpt-4o-mini
```

Not: `gpt-image-2` kullanımı için OpenAI platformunda Organization Verification gerekebilir. Doğrulama yoksa uygulama hata vermeden basit fallback görsel üretir.

## Endpointler

### `GET /`
Web arayüzünü açar.

### `GET /suggest-topics`
İnternet/PubMed üzerinden güncel ortopedi-travmatoloji başlıklarını almaya çalışır. Erişim başarısız olursa yerel kürasyon listesini döndürür.

### `POST /create-post`
Form alanları:

```text
topic: Türkçe konu
tone: professional | educational | friendly
```

Dönen çıktı:

```json
{
  "outputs": {
    "post": "/output/post_xxxxxxxx.jpg",
    "story": "/output/story_xxxxxxxx.jpg"
  }
}
```

## Lokal çalıştırma

```bash
pip install -r requirements.txt
python main.py
```

Tarayıcıda:

```text
http://localhost:8000
```
