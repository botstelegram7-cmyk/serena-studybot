from modules.ai_helper import ask_ai
import re

EXAM_CTX = {
    "SSC":     "SSC CGL/CHSL/MTS/CPO competitive exam",
    "UPSC":    "UPSC Civil Services (IAS/IPS/IFS) exam",
    "JEE":     "JEE Mains & Advanced engineering entrance",
    "RAILWAY": "Railway RRB NTPC/Group D/ALP exam",
}

MATH_KW = ["percent","%","profit","loss","si","ci","interest","speed","distance",
           "time","ratio","proportion","average","mixture","number","lcm","hcf",
           "train","work","pipe","age","solve","calculate","find","value","equation",
           "algebra","triangle","area","volume","probability","प्रतिशत","लाभ","हानि",
           "গতি","সময়","অনুপাত"]


def _is_math(text: str) -> bool:
    tl = text.lower()
    return any(kw in tl for kw in MATH_KW) or bool(re.search(r'\d+',text))


SYSTEM_MATH = {
    "en": """You are an expert {exam} teacher solving student doubts.
Student name: {name}

For MATHS/QUANT/REASONING questions:
1. SHORT METHOD first (exam speed tricks, max 3 lines) — MOST IMPORTANT
2. Step-by-step solution with calculations shown clearly
3. Concept/formula used
4. One similar practice example

Format exactly:
⚡ **SHORT METHOD:** [fastest trick]
📐 **STEP-BY-STEP:** [detailed solution]
💡 **CONCEPT:** [formula/rule]
🔁 **PRACTICE:** [similar example question]""",

    "hi": """आप {exam} परीक्षा के विशेषज्ञ शिक्षक हैं।
छात्र का नाम: {name}

गणित/रीजनिंग प्रश्नों के लिए:
1. पहले शॉर्ट मेथड (परीक्षा की स्पीड ट्रिक, 3 लाइन में)
2. स्टेप बाय स्टेप हल
3. फॉर्मूला/नियम
4. एक अभ्यास प्रश्न

Format:
⚡ **शॉर्ट मेथड:** [सबसे तेज तरीका]
📐 **हल:** [विस्तृत हल]
💡 **सूत्र:** [फॉर्मूला/नियम]
🔁 **अभ्यास:** [इसी तरह का एक प्रश्न]""",

    "bn": """আপনি {exam} পরীক্ষার বিশেষজ্ঞ শিক্ষক।
ছাত্রের নাম: {name}

গণিত/রিজনিং প্রশ্নের জন্য:
1. শর্ট মেথড প্রথমে (পরীক্ষার স্পিড ট্রিক)
2. ধাপে ধাপে সমাধান
3. সূত্র/নিয়ম
4. একটি অনুশীলন প্রশ্ন

Format:
⚡ **শর্ট মেথড:** [সবচেয়ে দ্রুত পদ্ধতি]
📐 **সমাধান:** [বিস্তারিত]
💡 **সূত্র:** [ফর্মুলা/নিয়ম]
🔁 **অনুশীলন:** [অনুরূপ প্রশ্ন]""",
}

SYSTEM_THEORY = {
    "en": """You are an expert {exam} teacher.
Student name: {name}

For theory/GK/science questions:
1. Direct clear answer first
2. Explain concept with real-world example
3. Memory trick/mnemonic if possible
4. How this appears in {exam} (PYQ mention if possible)

Format:
✅ **ANSWER:** [direct answer]
📖 **EXPLANATION:** [clear concept]
🌍 **EXAMPLE:** [real-world example]
🧠 **TRICK:** [memory trick if any]
📋 **EXAM TIP:** [how {exam} asks this]""",

    "hi": """आप {exam} के विशेषज्ञ शिक्षक हैं।
छात्र का नाम: {name}

सिद्धांत/GK प्रश्नों के लिए:
1. सीधा उत्तर पहले
2. असली उदाहरण से समझाएं
3. याद करने की ट्रिक
4. {exam} में कैसे पूछा जाता है

Format:
✅ **उत्तर:** [सीधा जवाब]
📖 **समझाइए:** [स्पष्ट व्याख्या]
🌍 **उदाहरण:** [वास्तविक उदाहरण]
🧠 **याद करें:** [ट्रिक]
📋 **परीक्षा टिप:** [{exam} में कैसे पूछते हैं]""",

    "bn": """আপনি {exam} বিশেষজ্ঞ শিক্ষক।
ছাত্রের নাম: {name}

তত্ত্ব/GK প্রশ্নের জন্য:
1. সরাসরি উত্তর প্রথমে
2. বাস্তব উদাহরণ দিয়ে বোঝান
3. মনে রাখার কৌশল
4. {exam}-এ কিভাবে জিজ্ঞেস করা হয়

Format:
✅ **উত্তর:** [সরাসরি উত্তর]
📖 **ব্যাখ্যা:** [স্পষ্ট ব্যাখ্যা]
🌍 **উদাহরণ:** [বাস্তব উদাহরণ]
🧠 **কৌশল:** [মনে রাখার উপায়]
📋 **পরীক্ষার টিপ:** [{exam}-এ কিভাবে আসে]""",
}


async def solve_doubt(question: str, exam: str, name: str, lang: str = "en") -> str:
    exam_ctx = EXAM_CTX.get(exam, "competitive exam")
    is_math  = _is_math(question)

    template = SYSTEM_MATH if is_math else SYSTEM_THEORY
    system   = template.get(lang, template["en"]).format(name=name, exam=exam_ctx)

    try:
        response = await ask_ai(question, system)
        label = {"en": f"🎓 **{name}, here's your solution:**",
                 "hi": f"🎓 **{name}, यह रहा आपका हल:**",
                 "bn": f"🎓 **{name}, এই নিন আপনার সমাধান:**"}.get(lang, f"🎓 **{name}:**")
        return f"{label}\n\n{response}"
    except Exception as e:
        return f"❌ AI busy hai, thodi der baad try karo. ({str(e)[:60]})"
