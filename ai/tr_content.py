"""
ai/tr_content.py
Türkçe ortopedi Instagram içeriği: hook, caption, hashtag, carousel metni ve güncel konu önerileri.
"""

from __future__ import annotations

import json
import logging
import os
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

DISCLAIMER = "Bilgilendirme amaçlıdır. Daha fazla bilgi için doktorunuza başvurun."
SURGICAL_DISCLAIMER = "Her cerrahi veya girişimsel işlemde sonuçlar kişiden kişiye değişiklik gösterebilir. İşlem öncesinde hekiminizden detaylı görüş almanız önerilir."

CURATED_TOPICS = [
    {"title": "Robotik diz protezi gerçekten daha mı iyi?", "angle": "Avantaj, sınır ve hasta seçimini dengeli anlat.", "source": "Kürasyon"},
    {"title": "Kalça protezi sonrası güvenli iyileşme süreci", "angle": "Erken mobilizasyon, egzersiz ve kontrol randevularını açıkla.", "source": "Kürasyon"},
    {"title": "Menisküs yırtığı her zaman ameliyat gerektirir mi?", "angle": "Belirti, MR bulgusu ve tedavi kararını hasta diliyle anlat.", "source": "Kürasyon"},
    {"title": "Skolyoz takibinde yapay zekâ ve fotoğraf analizi", "angle": "Yardımcı takip aracı olarak doğru beklentiyi kur.", "source": "Kürasyon"},
    {"title": "Osteoporotik kırıklar: basit düşme neden ciddi olabilir?", "angle": "Kalça, omurga ve el bileği kırıklarından kemik sağlığına geçiş yap.", "source": "Kürasyon"},
    {"title": "Ayak başparmak ağrısı: halluks valgus mu, halluks rijidus mu?", "angle": "Hastaların sık karıştırdığı iki tabloyu ayır.", "source": "Kürasyon"},
    {"title": "Diz protezi sonrası şişlik ne zaman önemlidir?", "angle": "Normal iyileşme ile uyarıcı bulgular arasındaki farkı anlat.", "source": "Kürasyon"},
    {"title": "Omuz ağrısında sıkışma sendromu ve rotator manşet yırtığı", "angle": "Gece ağrısı, güçsüzlük ve tedavi seçeneklerini sadeleştir.", "source": "Kürasyon"},
]


def _has_key() -> bool:
    return os.environ.get("OPENAI_API_KEY", "").strip().startswith("sk-")


def _openai_chat(messages, temperature=0.5, max_tokens=700):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def generate_turkish_hook(topic: str) -> str:
    if _has_key():
        try:
            return _openai_chat([
                {"role": "system", "content": "Ortopedi uzmanı için Türkçe Instagram hook cümlesi yaz. Tek cümle, 7-13 kelime, anlaşılır, güven veren, clickbait olmayan, tıbbi iddia abartısı içermeyen bir ifade olsun. Sadece cümleyi döndür."},
                {"role": "user", "content": f"Konu: {topic}"},
            ], temperature=0.65, max_tokens=80).strip('"').strip("'")
        except Exception as exc:
            logger.warning("Hook generation failed: %s", exc)
    return "Doğru tanı, doğru tedavi planının ilk adımıdır."


def generate_turkish_caption(topic: str, hook: str, tone: str = "professional") -> str:
    surgical = any(k in topic.lower() for k in ["protez", "ameliyat", "cerrahi", "implant", "revizyon"])
    final_disclaimer = DISCLAIMER + ("\n" + SURGICAL_DISCLAIMER if surgical else "")
    if _has_key():
        try:
            return _openai_chat([
                {"role": "system", "content": f"""
Sen Doç. Dr. Özgür Karakoyun için Türkçe medikal Instagram açıklaması yazan editörsün.
Kurallar:
- Türkçe yaz.
- Hasta dostu, bilimsel, sakin ve güven veren ton kullan.
- Tedavi garantisi, kesin sonuç, mucize ve abartılı vaat kullanma.
- 110-170 kelime yaz.
- İlk satır hook cümlesi olsun ve aynen kullanılsın.
- Kısa paragraflar kullan.
- Son satır(lar) aynen şu uyarı olsun: {final_disclaimer}
- Markdown başlığı kullanma.
"""},
                {"role": "user", "content": f"Konu: {topic}\nHook: {hook}\nTon: {tone}\nAçıklamayı yaz."},
            ], temperature=0.55, max_tokens=700)
        except Exception as exc:
            logger.warning("Caption generation failed: %s", exc)
    return f"{hook}\n\n{topic} hakkında doğru bilgi, muayene bulguları ve görüntüleme sonuçları birlikte değerlendirilmelidir. Her hastanın yaşı, aktivite düzeyi, şikâyet süresi ve beklentisi farklı olduğu için tedavi planı kişiye özel yapılmalıdır.\n\nŞikâyetleriniz devam ediyorsa veya günlük yaşamınızı etkiliyorsa ortopedi ve travmatoloji uzmanına başvurmanız uygun olur.\n\n{final_disclaimer}"


def generate_turkish_hashtags(topic: str) -> list[str]:
    if _has_key():
        try:
            text = _openai_chat([
                {"role": "system", "content": "Türkçe ortopedi Instagram gönderisi için 8 hashtag üret. Her satır # ile başlasın. Türkçe, aranabilir ve konu ile ilgili etiketler kullan. Açıklama yazma."},
                {"role": "user", "content": f"Konu: {topic}"},
            ], temperature=0.35, max_tokens=160)
            tags = [line.strip() for line in text.splitlines() if line.strip().startswith("#")]
            base = ["#Ortopedi", "#Travmatoloji", "#ÖzgürKarakoyun"]
            return list(dict.fromkeys(tags + base))[:10]
        except Exception as exc:
            logger.warning("Hashtag generation failed: %s", exc)
    return ["#Ortopedi", "#Travmatoloji", "#KemikSağlığı", "#EklemSağlığı", "#DizAğrısı", "#KalçaAğrısı", "#ÖzgürKarakoyun"]


def generate_carousel_slides(topic: str, hook: str, count: int = 5) -> list[dict]:
    count = max(3, min(int(count or 5), 7))
    if _has_key():
        try:
            text = _openai_chat([
                {"role": "system", "content": f"""
Türkçe Instagram carousel metni üret. Yanıtı sadece geçerli JSON olarak döndür.
Format: {{"slides":[{{"title":"...","body":"..."}}]}}
Kurallar:
- Tam olarak {count} slayt üret.
- Slayt 1 dikkat çekici kapak olsun.
- Her başlık en fazla 8 kelime.
- Her body en fazla 18 kelime.
- Hasta dostu, güven veren, abartısız medikal dil kullan.
- Son slaytta doktora başvurma/kişiye özel değerlendirme mesajı olsun.
"""},
                {"role": "user", "content": f"Konu: {topic}\nHook: {hook}"},
            ], temperature=0.5, max_tokens=850)
            data = json.loads(text)
            slides = data.get("slides", [])
            if isinstance(slides, list) and len(slides) >= 3:
                return slides[:count]
        except Exception as exc:
            logger.warning("Carousel text generation failed: %s", exc)
    return [
        {"title": topic[:54], "body": hook},
        {"title": "Neden önemlidir?", "body": "Şikâyetin nedeni doğru anlaşılmadan tedavi planı netleşmez."},
        {"title": "Hangi bulgular değerlendirilir?", "body": "Muayene, görüntüleme ve günlük yaşam etkisi birlikte ele alınır."},
        {"title": "Tedavi kişiye özeldir", "body": "Yaş, aktivite düzeyi ve beklentiler tedavi seçimini etkiler."},
        {"title": "Ne zaman başvurmalı?", "body": "Ağrı veya hareket kısıtlılığı sürüyorsa uzman görüşü alınmalıdır."},
    ][:count]


def _pubmed_recent_titles() -> list[dict]:
    query = '(orthopedic OR orthopaedic OR traumatology OR arthroplasty OR fracture OR scoliosis OR sports medicine) AND (2025:3000[pdat])'
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            esearch = client.get(f"{base}/esearch.fcgi", params={"db": "pubmed", "term": query, "retmode": "json", "retmax": "8", "sort": "pub date"})
            esearch.raise_for_status()
            ids = esearch.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []
            efetch = client.get(f"{base}/efetch.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
            efetch.raise_for_status()
        root = ET.fromstring(efetch.text)
        results = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID", default="")
            title_node = article.find(".//ArticleTitle")
            title = "".join(title_node.itertext()).strip() if title_node is not None else ""
            if title:
                results.append({"title": title, "angle": "Güncel literatürden hasta eğitimi için sadeleştirilebilir.", "source": f"PubMed PMID {pmid}" if pmid else "PubMed"})
        return results[:8]
    except Exception as exc:
        logger.warning("PubMed topic fetch failed: %s", exc)
        return []


def suggest_current_topics() -> list[dict]:
    fetched = _pubmed_recent_titles()
    if fetched and _has_key():
        try:
            joined = "\n".join([f"- {x['title']} ({x['source']})" for x in fetched])
            text = _openai_chat([
                {"role": "system", "content": "PubMed başlıklarından Türkçe Instagram konu önerileri çıkar. 6 öneri ver. Her öneriyi şu formatta yaz: Başlık | Açı | Kaynak. Hasta eğitimi için anlaşılır, güncel, ortopedi/travmatoloji odaklı olsun."},
                {"role": "user", "content": joined},
            ], temperature=0.45, max_tokens=800)
            topics = []
            for line in text.splitlines():
                line = line.strip("-• ").strip()
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    topics.append({"title": parts[0], "angle": parts[1], "source": parts[2] if len(parts) > 2 else "PubMed"})
            if topics:
                return topics[:6]
        except Exception as exc:
            logger.warning("Topic summarization failed: %s", exc)
    return (fetched[:3] + CURATED_TOPICS)[:8]
