"""
ai/tr_content.py
Turkish orthopedic Instagram content and current-topic suggestions.
"""

import logging
import os
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

DISCLAIMER = "Bilgilendirme amaçlıdır. Tanı ve tedavi için hekiminize başvurunuz."

CURATED_TOPICS = [
    {
        "title": "Robotik diz protezi gerçekten daha mı iyi?",
        "angle": "Standart diz protezi ile robotik cerrahi arasındaki farkları hasta diliyle anlat.",
        "source": "Kürasyon",
    },
    {
        "title": "Kalça protezinde hızlı iyileşme: doğru hasta, doğru plan",
        "angle": "Ameliyat sonrası erken mobilizasyon ve rehabilitasyonun önemini vurgula.",
        "source": "Kürasyon",
    },
    {
        "title": "Spor yaralanmalarında PRP, kök hücre ve gerçekçi beklentiler",
        "angle": "Abartılı vaatlerden kaçınarak biyolojik tedavilerin sınırlarını anlat.",
        "source": "Kürasyon",
    },
    {
        "title": "Skolyoz takibinde yapay zekâ ve fotoğraf analizi",
        "angle": "Röntgen yerine geçmediğini ama takipte yardımcı olabileceğini açıkla.",
        "source": "Kürasyon",
    },
    {
        "title": "Osteoporotik kırıklar: basit düşme neden ciddi olabilir?",
        "angle": "Kalça, omurga ve el bileği kırıklarında kemik sağlığı değerlendirmesini anlat.",
        "source": "Kürasyon",
    },
    {
        "title": "Ayak başparmak ağrısı: halluks valgus mu, halluks rijidus mu?",
        "angle": "Hastaların sık karıştırdığı iki tabloyu sade şekilde ayır.",
        "source": "Kürasyon",
    },
]


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
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key.startswith("sk-"):
        try:
            return _openai_chat([
                {"role": "system", "content": "Ortopedi uzmanı için Türkçe Instagram hook cümlesi yaz. Tek cümle, 8-14 kelime, merak uyandırıcı ama clickbait değil. Tıbbi iddia abartısı yapma. Sadece cümleyi döndür."},
                {"role": "user", "content": f"Konu: {topic}"},
            ], temperature=0.7, max_tokens=80).strip('"').strip("'")
        except Exception as exc:
            logger.warning("Turkish hook OpenAI failed: %s", exc)
    return "Doğru tedavi, doğru tanıyla başlar."


def generate_turkish_caption(topic: str, hook: str, tone: str = "professional") -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key.startswith("sk-"):
        try:
            return _openai_chat([
                {"role": "system", "content": f"""
Sen Doç. Dr. Özgür Karakoyun için Türkçe medikal Instagram açıklaması yazan editörsün.
Kurallar:
- Türkçe yaz.
- Hasta dostu, bilimsel, sakin ve güven veren ton kullan.
- Tedavi garantisi, kesin sonuç, mucize, abartılı vaat kullanma.
- 120-180 kelime.
- İlk satır hook cümlesi olsun ve aynen kullanılsın.
- Kısa paragraflar kullan.
- Son satır aynen şu olsun: {DISCLAIMER}
- Markdown başlığı kullanma.
"""},
                {"role": "user", "content": f"Konu: {topic}\nHook: {hook}\nTon: {tone}\nAçıklamayı yaz."},
            ], temperature=0.55, max_tokens=650)
        except Exception as exc:
            logger.warning("Turkish caption OpenAI failed: %s", exc)
    return f"{hook}\n\n{topic} hakkında doğru bilgi, doğru değerlendirme ve kişiye özel tedavi planı önemlidir. Ortopedi ve travmatolojide her hastanın yaşı, aktivite düzeyi, muayene bulguları ve görüntüleme sonuçları birlikte değerlendirilmelidir.\n\nEn doğru yaklaşım, şikâyetin nedenini belirlemek ve tedaviyi buna göre planlamaktır.\n\n{DISCLAIMER}"


def generate_turkish_hashtags(topic: str) -> list[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key.startswith("sk-"):
        try:
            text = _openai_chat([
                {"role": "system", "content": "Türkçe ortopedi Instagram gönderisi için 8 hashtag üret. Her satır # ile başlasın. Türkçe ve aranabilir etiketler kullan. Açıklama yazma."},
                {"role": "user", "content": f"Konu: {topic}"},
            ], temperature=0.4, max_tokens=160)
            tags = [line.strip() for line in text.splitlines() if line.strip().startswith("#")]
            base = ["#Ortopedi", "#Travmatoloji", "#ÖzgürKarakoyun"]
            return list(dict.fromkeys(tags + base))[:10]
        except Exception as exc:
            logger.warning("Turkish hashtags OpenAI failed: %s", exc)
    return ["#Ortopedi", "#Travmatoloji", "#KemikSağlığı", "#EklemSağlığı", "#DizAğrısı", "#KalçaAğrısı", "#ÖzgürKarakoyun"]


def _pubmed_recent_titles() -> list[dict]:
    """Fetch recent PubMed titles to seed current topic suggestions."""
    query = '(orthopedic OR orthopaedic OR traumatology OR arthroplasty OR fracture OR scoliosis) AND (2025:3000[pdat])'
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            esearch = client.get(f"{base}/esearch.fcgi", params={
                "db": "pubmed", "term": query, "retmode": "json", "retmax": "8", "sort": "pub date"
            })
            esearch.raise_for_status()
            ids = esearch.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []
            efetch = client.get(f"{base}/efetch.fcgi", params={
                "db": "pubmed", "id": ",".join(ids), "retmode": "xml"
            })
            efetch.raise_for_status()
        root = ET.fromstring(efetch.text)
        results = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID", default="")
            title = "".join(article.find(".//ArticleTitle").itertext()).strip() if article.find(".//ArticleTitle") is not None else ""
            if title:
                results.append({
                    "title": title,
                    "angle": "Güncel literatürden hasta eğitimi için sadeleştirilmiş içerik konusu.",
                    "source": f"PubMed PMID {pmid}" if pmid else "PubMed",
                })
        return results[:8]
    except Exception as exc:
        logger.warning("PubMed topic fetch failed: %s", exc)
        return []


def suggest_current_topics() -> list[dict]:
    fetched = _pubmed_recent_titles()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if fetched and api_key.startswith("sk-"):
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
            logger.warning("OpenAI topic summarization failed: %s", exc)
    return (fetched[:3] + CURATED_TOPICS)[:6]
