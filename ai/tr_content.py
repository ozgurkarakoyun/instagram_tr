"""
ai/tr_content.py
Çok dilli ortopedi Instagram içeriği: hook, caption, hashtag, carousel metni ve güncel konu önerileri.
Desteklenen diller: Türkçe, İngilizce, Arapça.
"""

from __future__ import annotations

import json
import logging
import os
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

LANGUAGES = {
    "tr": {
        "name": "Türkçe",
        "prompt_name": "Turkish",
        "specialty": "Ortopedi ve Travmatoloji",
        "subline": "Güvenilir hasta bilgilendirme içeriği",
        "disclaimer": "Bilgilendirme amaçlıdır. Daha fazla bilgi için doktorunuza başvurun.",
        "surgical_disclaimer": "Her cerrahi veya girişimsel işlemde sonuçlar kişiden kişiye değişiklik gösterebilir. İşlem öncesinde hekiminizden detaylı görüş almanız önerilir.",
        "fallback_hook": "Doğru tanı, doğru tedavi planının ilk adımıdır.",
        "fallback_hashtags": ["#Ortopedi", "#Travmatoloji", "#KemikSağlığı", "#EklemSağlığı", "#DizAğrısı", "#KalçaAğrısı", "#ÖzgürKarakoyun"],
    },
    "en": {
        "name": "English",
        "prompt_name": "English",
        "specialty": "Orthopedics and Traumatology",
        "subline": "Reliable patient education content",
        "disclaimer": "For informational purposes only. Please consult your doctor for more information.",
        "surgical_disclaimer": "Outcomes may vary between patients for every surgical or interventional procedure. A detailed consultation with your physician is recommended before treatment.",
        "fallback_hook": "The right diagnosis is the first step toward the right treatment.",
        "fallback_hashtags": ["#Orthopedics", "#Traumatology", "#BoneHealth", "#JointHealth", "#KneePain", "#HipPain", "#OzgurKarakoyun"],
    },
    "ar": {
        "name": "العربية",
        "prompt_name": "Arabic",
        "specialty": "جراحة العظام والكسور",
        "subline": "محتوى موثوق لتثقيف المرضى",
        "disclaimer": "هذه المعلومات لأغراض التوعية فقط. للمزيد من المعلومات يُرجى استشارة طبيبك.",
        "surgical_disclaimer": "قد تختلف نتائج أي إجراء جراحي أو تداخلي من مريض لآخر. يُنصح بالحصول على استشارة مفصلة من طبيبك قبل الإجراء.",
        "fallback_hook": "التشخيص الصحيح هو الخطوة الأولى للعلاج الصحيح.",
        "fallback_hashtags": ["#جراحة_العظام", "#الكسور", "#صحة_العظام", "#صحة_المفاصل", "#ألم_الركبة", "#ألم_الورك", "#اوزغور_كاراكويون"],
    },
}

DISCLAIMER = LANGUAGES["tr"]["disclaimer"]
SURGICAL_DISCLAIMER = LANGUAGES["tr"]["surgical_disclaimer"]

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

CURATED_TOPICS_EN = [
    {"title": "Is robotic knee replacement really better?", "angle": "Explain benefits, limits, and patient selection in balanced language.", "source": "Curated"},
    {"title": "Safe recovery after hip replacement", "angle": "Explain early mobilization, exercises, and follow-up visits.", "source": "Curated"},
    {"title": "Does every meniscus tear require surgery?", "angle": "Clarify symptoms, MRI findings, and treatment decisions.", "source": "Curated"},
    {"title": "AI-assisted scoliosis monitoring", "angle": "Set realistic expectations for AI as a follow-up aid.", "source": "Curated"},
    {"title": "Osteoporotic fractures: why minor falls can be serious", "angle": "Connect hip, spine, and wrist fractures with bone health.", "source": "Curated"},
    {"title": "Big toe pain: hallux valgus or hallux rigidus?", "angle": "Differentiate two conditions patients often confuse.", "source": "Curated"},
]

CURATED_TOPICS_AR = [
    {"title": "هل جراحة تبديل الركبة بالروبوت أفضل فعلاً؟", "angle": "اشرح الفوائد والحدود واختيار المريض بلغة متوازنة.", "source": "تنسيق"},
    {"title": "التعافي الآمن بعد تبديل مفصل الورك", "angle": "اشرح الحركة المبكرة والتمارين ومواعيد المتابعة.", "source": "تنسيق"},
    {"title": "هل يحتاج كل تمزق في الغضروف الهلالي إلى عملية؟", "angle": "وضح الأعراض ونتائج الرنين وقرار العلاج.", "source": "تنسيق"},
    {"title": "متابعة الجنف باستخدام الذكاء الاصطناعي", "angle": "قدّم الذكاء الاصطناعي كأداة مساعدة للمتابعة.", "source": "تنسيق"},
    {"title": "كسور هشاشة العظام: لماذا قد تكون السقطة البسيطة خطيرة؟", "angle": "اربط كسور الورك والعمود والمعصم بصحة العظام.", "source": "تنسيق"},
    {"title": "ألم إبهام القدم: انحراف أم تيبس؟", "angle": "ميّز بين حالتين يخلط بينهما المرضى كثيراً.", "source": "تنسيق"},
]


def normalize_language(language: str | None) -> str:
    lang = (language or "tr").strip().lower()
    return lang if lang in LANGUAGES else "tr"


def language_config(language: str | None) -> dict:
    return LANGUAGES[normalize_language(language)]


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


def _is_surgical(topic: str) -> bool:
    t = (topic or "").lower()
    return any(k in t for k in [
        "protez", "ameliyat", "cerrahi", "implant", "revizyon",
        "surgery", "replacement", "arthroplasty", "implant", "revision",
        "جراحة", "عملية", "مفصل", "زرع", "استبدال"
    ])


def generate_hook(topic: str, language: str = "tr") -> str:
    lang = normalize_language(language)
    cfg = language_config(lang)
    if _has_key():
        try:
            return _openai_chat([
                {"role": "system", "content": f"Write one Instagram hook sentence in {cfg['prompt_name']} for an orthopedic specialist. 7-13 words if possible, clear, calm, trustworthy, no clickbait, no exaggerated medical claims. Return only the sentence."},
                {"role": "user", "content": f"Topic: {topic}"},
            ], temperature=0.65, max_tokens=90).strip('"').strip("'")
        except Exception as exc:
            logger.warning("Hook generation failed: %s", exc)
    return cfg["fallback_hook"]


def generate_caption(topic: str, hook: str, tone: str = "professional", language: str = "tr") -> str:
    lang = normalize_language(language)
    cfg = language_config(lang)
    final_disclaimer = cfg["disclaimer"] + ("\n" + cfg["surgical_disclaimer"] if _is_surgical(topic) else "")
    if _has_key():
        try:
            return _openai_chat([
                {"role": "system", "content": f"""
You are a medical Instagram editor for Assoc. Prof. Dr. Özgür Karakoyun.
Rules:
- Write in {cfg['prompt_name']}.
- Patient-friendly, scientific, calm, trustworthy tone.
- No treatment guarantee, miracle claims, exaggerated promises, or fear-based language.
- 110-170 words.
- First line must be the hook sentence exactly as provided.
- Use short paragraphs.
- End with this disclaimer exactly:
{final_disclaimer}
- Do not use markdown headings.
"""},
                {"role": "user", "content": f"Topic: {topic}\nHook: {hook}\nTone: {tone}\nWrite the caption."},
            ], temperature=0.55, max_tokens=800)
        except Exception as exc:
            logger.warning("Caption generation failed: %s", exc)

    if lang == "en":
        return f"{hook}\n\nAccurate information about {topic} should be interpreted together with examination findings and imaging results. Since each patient's age, activity level, symptom duration and expectations are different, treatment planning should be individualized.\n\nIf your symptoms continue or affect daily life, an orthopedic and traumatology consultation is recommended.\n\n{final_disclaimer}"
    if lang == "ar":
        return f"{hook}\n\nيجب تقييم موضوع {topic} مع نتائج الفحص والصور الطبية عند الحاجة. تختلف الخطة العلاجية حسب العمر ومستوى النشاط ومدة الأعراض وتوقعات كل مريض.\n\nإذا استمرت الأعراض أو أثرت في الحياة اليومية، فمن الأفضل مراجعة طبيب مختص بجراحة العظام والكسور.\n\n{final_disclaimer}"
    return f"{hook}\n\n{topic} hakkında doğru bilgi, muayene bulguları ve görüntüleme sonuçları birlikte değerlendirilmelidir. Her hastanın yaşı, aktivite düzeyi, şikâyet süresi ve beklentisi farklı olduğu için tedavi planı kişiye özel yapılmalıdır.\n\nŞikâyetleriniz devam ediyorsa veya günlük yaşamınızı etkiliyorsa ortopedi ve travmatoloji uzmanına başvurmanız uygun olur.\n\n{final_disclaimer}"


def generate_hashtags(topic: str, language: str = "tr") -> list[str]:
    lang = normalize_language(language)
    cfg = language_config(lang)
    if _has_key():
        try:
            text = _openai_chat([
                {"role": "system", "content": f"Generate 8 Instagram hashtags in {cfg['prompt_name']} for an orthopedic post. Each line must start with #. Use searchable, topic-relevant tags. No explanation."},
                {"role": "user", "content": f"Topic: {topic}"},
            ], temperature=0.35, max_tokens=180)
            tags = [line.strip() for line in text.splitlines() if line.strip().startswith("#")]
            base = cfg["fallback_hashtags"][-2:]
            return list(dict.fromkeys(tags + base))[:10]
        except Exception as exc:
            logger.warning("Hashtag generation failed: %s", exc)
    return cfg["fallback_hashtags"]


def generate_carousel_slides(topic: str, hook: str, count: int = 5, language: str = "tr") -> list[dict]:
    count = max(3, min(int(count or 5), 7))
    lang = normalize_language(language)
    cfg = language_config(lang)
    if _has_key():
        try:
            text = _openai_chat([
                {"role": "system", "content": f"""
Create Instagram carousel copy in {cfg['prompt_name']}. Return only valid JSON.
Format: {{"slides":[{{"title":"...","body":"..."}}]}}
Rules:
- Produce exactly {count} slides.
- Slide 1 must be an attention-grabbing cover.
- Each title max 8 words.
- Each body max 18 words.
- Patient-friendly, trustworthy, medically balanced.
- Last slide should recommend individualized medical evaluation / consulting a physician.
"""},
                {"role": "user", "content": f"Topic: {topic}\nHook: {hook}"},
            ], temperature=0.5, max_tokens=900)
            data = json.loads(text)
            slides = data.get("slides", [])
            if isinstance(slides, list) and len(slides) >= 3:
                return slides[:count]
        except Exception as exc:
            logger.warning("Carousel text generation failed: %s", exc)

    if lang == "en":
        fallback = [
            {"title": topic[:54], "body": hook},
            {"title": "Why does it matter?", "body": "Treatment planning starts with understanding the real cause of symptoms."},
            {"title": "What is evaluated?", "body": "Examination, imaging and daily-life impact are considered together."},
            {"title": "Treatment is individual", "body": "Age, activity level and expectations can change the best option."},
            {"title": "When to seek help?", "body": "Persistent pain or limited movement should be assessed by a specialist."},
        ]
    elif lang == "ar":
        fallback = [
            {"title": topic[:54], "body": hook},
            {"title": "لماذا هذا مهم؟", "body": "تحديد سبب الأعراض هو الخطوة الأولى لوضع خطة علاج مناسبة."},
            {"title": "ما الذي يتم تقييمه؟", "body": "يتم تقييم الفحص والصور وتأثير المشكلة على الحياة اليومية معاً."},
            {"title": "العلاج يختلف حسب المريض", "body": "العمر والنشاط والتوقعات تؤثر في اختيار العلاج الأنسب."},
            {"title": "متى تراجع الطبيب؟", "body": "إذا استمر الألم أو محدودية الحركة، يُنصح بمراجعة المختص."},
        ]
    else:
        fallback = [
            {"title": topic[:54], "body": hook},
            {"title": "Neden önemlidir?", "body": "Şikâyetin nedeni doğru anlaşılmadan tedavi planı netleşmez."},
            {"title": "Hangi bulgular değerlendirilir?", "body": "Muayene, görüntüleme ve günlük yaşam etkisi birlikte ele alınır."},
            {"title": "Tedavi kişiye özeldir", "body": "Yaş, aktivite düzeyi ve beklentiler tedavi seçimini etkiler."},
            {"title": "Ne zaman başvurmalı?", "body": "Ağrı veya hareket kısıtlılığı sürüyorsa uzman görüşü alınmalıdır."},
        ]
    return fallback[:count]


# Geriye dönük uyumluluk için eski fonksiyon adları
def generate_turkish_hook(topic: str) -> str:
    return generate_hook(topic, "tr")


def generate_turkish_caption(topic: str, hook: str, tone: str = "professional") -> str:
    return generate_caption(topic, hook, tone, "tr")


def generate_turkish_hashtags(topic: str) -> list[str]:
    return generate_hashtags(topic, "tr")


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
                results.append({"title": title, "angle": "Can be simplified for current patient education.", "source": f"PubMed PMID {pmid}" if pmid else "PubMed"})
        return results[:8]
    except Exception as exc:
        logger.warning("PubMed topic fetch failed: %s", exc)
        return []


def suggest_current_topics(language: str = "tr") -> list[dict]:
    lang = normalize_language(language)
    if lang == "en":
        curated = CURATED_TOPICS_EN
    elif lang == "ar":
        curated = CURATED_TOPICS_AR
    else:
        curated = CURATED_TOPICS

    fetched = _pubmed_recent_titles()
    if fetched and _has_key():
        try:
            cfg = language_config(lang)
            joined = "\n".join([f"- {x['title']} ({x['source']})" for x in fetched])
            text = _openai_chat([
                {"role": "system", "content": f"Extract 6 Instagram topic suggestions in {cfg['prompt_name']} from PubMed titles. Format each line as: Title | Angle | Source. Make them understandable, current, orthopedics/traumatology-focused."},
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
    return (fetched[:3] + curated)[:8]
