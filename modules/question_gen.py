import random
from modules.ai_helper import ask_ai_json

SECTION_MAP = {
    "Quant":          ["Percentage","Profit & Loss","SI & CI","Time & Work",
                       "Speed Distance Time","Ratio & Proportion","Number System",
                       "Algebra","Geometry","Trigonometry","DI","Average","Mixture"],
    "English":        ["Reading Comprehension","Error Spotting","Fill in Blanks",
                       "Sentence Improvement","Synonyms & Antonyms","Idioms & Phrases",
                       "Para Jumbles","Cloze Test","One Word Substitution"],
    "Reasoning":      ["Analogy","Series","Coding-Decoding","Blood Relations",
                       "Direction Sense","Ranking","Puzzles","Syllogism","Venn Diagram"],
    "GK":             ["History","Polity","Geography","Economy","Science & Tech",
                       "Sports","Awards","Current Affairs 2024-25","Static GK"],
    "Physics":        ["Mechanics","Optics","Thermodynamics","Electricity","Magnetism","Modern Physics"],
    "Chemistry":      ["Physical Chemistry","Organic Chemistry","Inorganic Chemistry","Chemical Bonding"],
    "Maths":          ["Algebra","Calculus","Coordinate Geometry","Trigonometry","Probability","Matrices"],
    "History":        ["Ancient India","Medieval India","Modern India","Freedom Struggle","Art & Culture"],
    "Polity":         ["Constitution","Fundamental Rights","Parliament","Judiciary","Federalism"],
    "Geography":      ["Physical Geography","Indian Geography","World Geography","Climate","Rivers"],
    "Economy":        ["Indian Economy","Budget 2024-25","Banking","Schemes & Policies 2024-25","Census 2024"],
    "Science":        ["Physics","Chemistry","Biology","Environment","Space 2024-25"],
    "Current Affairs":["National 2024-25","International 2024-25","Sports 2024-25","Awards 2024-25","Appointments 2024-25"],
    "General Science":["Physics","Chemistry","Biology","Computer","Environment"],
}

# Real PYQ instances — latest 2024-25 data
PYQ_EXAM_DATES = {
    "SSC": [
        ("SSC CGL 2024 Tier-I",        "2024"),
        ("SSC CGL 2024 Tier-II",        "2024"),
        ("SSC CHSL 2024 Tier-I",        "2024"),
        ("SSC CPO 2024",                "2024"),
        ("SSC GD Constable 2024",       "2024"),
        ("SSC MTS 2024",                "2024"),
        ("SSC Stenographer 2024",       "2024"),
        ("SSC CGL 2023 Tier-I",         "2023"),
        ("SSC CGL 2023 Tier-II",        "2023"),
        ("SSC CHSL 2023 Tier-I",        "2023"),
        ("SSC JE 2024",                 "2024"),
        ("SSC MTS 2023",                "2023"),
    ],
    "UPSC": [
        ("UPSC CSE Prelims 2024",       "2024"),
        ("UPSC CSE Prelims 2023",       "2023"),
        ("UPSC CAPF 2024",              "2024"),
        ("UPSC NDA II 2024",            "2024"),
        ("UPSC NDA I 2024",             "2024"),
        ("UPSC CDS II 2024",            "2024"),
        ("UPSC CDS I 2024",             "2024"),
        ("UPSC CSE Prelims 2022",       "2022"),
    ],
    "JEE": [
        ("JEE Mains Jan 2025 S1",       "2025"),
        ("JEE Mains Jan 2025 S2",       "2025"),
        ("JEE Mains Apr 2024 S1",       "2024"),
        ("JEE Mains Apr 2024 S2",       "2024"),
        ("JEE Mains Jan 2024 S1",       "2024"),
        ("JEE Advanced 2024",           "2024"),
        ("JEE Advanced 2023",           "2023"),
        ("JEE Mains 2023 S1",           "2023"),
    ],
    "RAILWAY": [
        ("RRB NTPC 2024 CBT-1",         "2024"),
        ("RRB Group D 2024 Phase-I",    "2024"),
        ("RRB Group D 2024 Phase-II",   "2024"),
        ("RRB ALP 2024 CBT-1",          "2024"),
        ("RRB JE 2024",                 "2024"),
        ("RRB NTPC 2023 CBT-2",         "2023"),
        ("RRB Group D 2023",            "2023"),
        ("RRB NTPC 2023 CBT-1",         "2023"),
    ],
}


async def generate_pyq_batch(exam: str, subject: str, section: str = None,
                              count: int = 5, difficulty: str = "Medium") -> list:
    """Generate PYQ-style questions — max 5 per call to avoid JSON truncation"""
    if not section:
        section = random.choice(SECTION_MAP.get(subject, [subject]))

    exam_instance, exam_year = random.choice(PYQ_EXAM_DATES.get(exam, [("Unknown Exam", "2024")]))

    style = {
        "SSC":     "SSC CGL/CHSL exam style — concise, 1-2 lines, tricky options",
        "UPSC":    "UPSC Prelims style — analytical, very close options, tests depth",
        "JEE":     "JEE Mains style — formula-based, numerical precision",
        "RAILWAY": "RRB NTPC style — straightforward, speed-focused",
    }.get(exam, "competitive exam")

    # Keep count small to avoid truncation
    batch = min(count, 5)

    prompt = f"""You are an expert Indian competitive exam question creator with knowledge up to 2025.
Generate exactly {batch} MCQ questions in the style of {exam_instance} ({exam_year}).

Subject: {subject} | Topic: {section} | Difficulty: {difficulty}
Style: {style}
Use latest 2024-2025 facts, schemes, appointments, current affairs where relevant.

Return ONLY a JSON array — no other text:
[
  {{
    "question": "concise question text (max 2 lines)",
    "options": ["A. opt1", "B. opt2", "C. opt3", "D. opt4"],
    "answer": "A",
    "explanation": "1-2 line explanation",
    "short_method": "shortcut trick or null",
    "subject": "{subject}",
    "section": "{section}",
    "exam": "{exam}",
    "exam_source": "{exam_instance}",
    "exam_year": "{exam_year}",
    "difficulty": "{difficulty}",
    "is_pyq": true,
    "source": "{exam_instance}"
  }}
]"""

    try:
        result = await ask_ai_json(prompt)
        if isinstance(result, list):
            return result[:batch]
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    return v[:batch]
    except Exception as e:
        print(f"[QGen] Batch failed: {e}")
    return []


async def translate_question(q: dict, target_lang: str) -> dict:
    if target_lang == "en":
        return q
    lang_name = {"hi": "Hindi", "bn": "Bengali"}.get(target_lang, "Hindi")
    prompt = f"""Translate this MCQ to {lang_name}. Keep A/B/C/D letters as is.
Q: {q['question']}
Options: {q['options']}
Explanation: {q.get('explanation','')}

Return JSON: {{"question":"...","options":["A. ...","B. ...","C. ...","D. ..."],"explanation":"..."}}"""
    try:
        t = await ask_ai_json(prompt)
        qc = q.copy()
        qc.update({"question": t.get("question", q["question"]),
                   "options":  t.get("options",  q["options"]),
                   "explanation": t.get("explanation", q.get("explanation","")),
                   "lang": target_lang})
        return qc
    except Exception:
        return q
