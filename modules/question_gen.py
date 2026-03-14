import random
from modules.ai_helper import ask_ai_json
from config import EXAMS

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

SECTION_MAP = {
    "Quant":          ["Percentage","Profit & Loss","SI & CI","Time & Work",
                       "Speed Distance Time","Ratio & Proportion","Number System",
                       "Algebra","Geometry","Trigonometry","DI","Average","Mixture","Partnership"],
    "English":        ["Reading Comprehension","Error Spotting","Fill in Blanks",
                       "Sentence Improvement","Synonyms & Antonyms","Idioms & Phrases",
                       "Para Jumbles","Cloze Test","One Word Substitution"],
    "Reasoning":      ["Analogy","Series","Coding-Decoding","Blood Relations",
                       "Direction Sense","Ranking","Puzzles","Syllogism",
                       "Venn Diagram","Matrix","Mirror Image","Paper Folding"],
    "GK":             ["History","Polity","Geography","Economy","Science & Tech",
                       "Sports","Awards","Books & Authors","Current Affairs","Static GK"],
    "Physics":        ["Mechanics","Optics","Thermodynamics","Electricity",
                       "Magnetism","Modern Physics","Waves & Sound","Units & Measurements"],
    "Chemistry":      ["Physical Chemistry","Organic Chemistry","Inorganic Chemistry",
                       "Equilibrium","Electrochemistry","Chemical Bonding"],
    "Maths":          ["Algebra","Calculus","Coordinate Geometry","Trigonometry",
                       "Vectors","Statistics","Probability","Matrices","3D Geometry"],
    "History":        ["Ancient India","Medieval India","Modern India",
                       "World History","Freedom Struggle","Art & Culture"],
    "Polity":         ["Constitution","Fundamental Rights","DPSP","Parliament",
                       "Judiciary","Federalism","Local Government","Elections"],
    "Geography":      ["Physical Geography","Indian Geography","World Geography",
                       "Climate","Rivers & Lakes","Soils","Resources"],
    "Economy":        ["Basic Concepts","Indian Economy","Budget","Banking",
                       "International Trade","Schemes & Policies","Census"],
    "Science":        ["Physics","Chemistry","Biology","Computer Science","Environment"],
    "Current Affairs": ["National","International","Sports","Awards","Appointments"],
    "General Science": ["Physics","Chemistry","Biology","Computer","Environment"],
}

# Real PYQ exam instances with dates
PYQ_EXAM_DATES = {
    "SSC": [
        ("SSC CGL 2024 Tier-I", "2024"),
        ("SSC CGL 2023 Tier-I", "2023"),
        ("SSC CGL 2022 Tier-I", "2022"),
        ("SSC CHSL 2024", "2024"),
        ("SSC CHSL 2023", "2023"),
        ("SSC MTS 2023", "2023"),
        ("SSC MTS 2022", "2022"),
        ("SSC CPO 2023", "2023"),
        ("SSC GD 2024", "2024"),
        ("SSC GD 2023", "2023"),
        ("SSC JE 2023", "2023"),
        ("SSC Stenographer 2023", "2023"),
    ],
    "UPSC": [
        ("UPSC CSE Prelims 2024", "2024"),
        ("UPSC CSE Prelims 2023", "2023"),
        ("UPSC CSE Prelims 2022", "2022"),
        ("UPSC CSE Prelims 2021", "2021"),
        ("UPSC CSE Prelims 2020", "2020"),
        ("UPSC CAPF 2023", "2023"),
        ("UPSC NDA 2024", "2024"),
        ("UPSC CDS 2024", "2024"),
    ],
    "JEE": [
        ("JEE Mains Jan 2024 Shift 1", "2024"),
        ("JEE Mains Jan 2024 Shift 2", "2024"),
        ("JEE Mains Apr 2024", "2024"),
        ("JEE Mains 2023 Shift 1", "2023"),
        ("JEE Mains 2023 Shift 2", "2023"),
        ("JEE Advanced 2024", "2024"),
        ("JEE Advanced 2023", "2023"),
        ("JEE Mains 2022", "2022"),
    ],
    "RAILWAY": [
        ("RRB NTPC 2024 CBT-1", "2024"),
        ("RRB NTPC 2023 CBT-1", "2023"),
        ("RRB NTPC 2022 CBT-2", "2022"),
        ("RRB Group D 2024", "2024"),
        ("RRB Group D 2023", "2023"),
        ("RRB ALP 2024", "2024"),
        ("RRB JE 2023", "2023"),
        ("RRB NTPC 2021 CBT-2", "2021"),
    ],
}


async def generate_pyq_question(exam: str, subject: str, section: str = None,
                                 difficulty: str = "Medium") -> dict:
    """Generate a PYQ-style question with real exam metadata"""
    if not section:
        sections = SECTION_MAP.get(subject, [subject])
        section = random.choice(sections)

    exam_instance, exam_year = random.choice(PYQ_EXAM_DATES.get(exam, [("Unknown Exam", "2023")]))

    exam_style = {
        "SSC":     "SSC CGL/CHSL actual exam style — concise, tricky options, 1-2 lines",
        "UPSC":    "UPSC Prelims actual exam style — analytical, options very close, tests depth",
        "JEE":     "JEE Mains actual exam style — formula based, numerical, conceptual depth",
        "RAILWAY": "RRB NTPC/Group D actual style — straightforward, clear options",
    }.get(exam, "competitive exam")

    prompt = f"""Generate 1 realistic Previous Year Question (PYQ) style MCQ.

Exam: {exam} ({exam_instance})
Subject: {subject}
Topic: {section}
Difficulty: {difficulty}
Style: {exam_style}

This question should look and feel EXACTLY like a real question from {exam_instance}.
Make the options realistic and tricky (like actual exams).

Return JSON:
{{
  "question": "complete question exactly as it would appear in exam",
  "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
  "answer": "A",
  "explanation": "detailed step-by-step explanation",
  "short_method": "fastest shortcut/trick (especially for maths/reasoning)",
  "subject": "{subject}",
  "section": "{section}",
  "exam": "{exam}",
  "exam_source": "{exam_instance}",
  "exam_year": "{exam_year}",
  "difficulty": "{difficulty}",
  "is_pyq": true,
  "source": "{exam_instance}",
  "lang": "en"
}}"""
    return await ask_ai_json(prompt)


async def generate_pyq_batch(exam: str, subject: str, section: str = None,
                              count: int = 10, difficulty: str = "Medium") -> list:
    """Generate a batch of PYQ-style questions efficiently"""
    if not section:
        sections = SECTION_MAP.get(subject, [subject])
        section = random.choice(sections)

    exam_instance, exam_year = random.choice(PYQ_EXAM_DATES.get(exam, [("Unknown Exam", "2023")]))

    exam_style = {
        "SSC":     "SSC CGL/CHSL actual exam — concise, speed-focused, tricky options",
        "UPSC":    "UPSC Prelims actual exam — analytical, close options, tests concepts",
        "JEE":     "JEE Mains actual exam — formula/numerical, physics/chem/maths depth",
        "RAILWAY": "RRB NTPC/Group D actual exam — clear, straightforward options",
    }.get(exam, "competitive exam")

    prompt = f"""Generate exactly {count} realistic PYQ-style MCQ questions.

Exam: {exam} — Style: {exam_instance}
Subject: {subject}, Topic: {section}
Difficulty: {difficulty}
Style: {exam_style}

Each question must look like it came from a REAL {exam} exam paper.

Return a JSON ARRAY of {count} objects. Each object must have:
{{
  "question": "full question text",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "A/B/C/D",
  "explanation": "step-by-step solution",
  "short_method": "exam shortcut/trick or null",
  "subject": "{subject}",
  "section": "{section}",
  "exam": "{exam}",
  "exam_source": "{exam_instance}",
  "exam_year": "{exam_year}",
  "difficulty": "{difficulty}",
  "is_pyq": true,
  "source": "{exam_instance}",
  "lang": "en"
}}

Make all {count} questions unique, cover different aspects of {section}."""

    result = await ask_ai_json(prompt)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                return v
    return []


async def generate_ai_question(exam: str, subject: str, section: str = None,
                                difficulty: str = "Medium") -> dict:
    """Generate a fresh non-PYQ AI question"""
    if not section:
        section = random.choice(SECTION_MAP.get(subject, [subject]))

    prompt = f"""Generate 1 original MCQ for {exam} exam.
Subject: {subject}, Topic: {section}, Difficulty: {difficulty}

Return JSON:
{{
  "question": "question text",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "A/B/C/D",
  "explanation": "explanation",
  "short_method": "shortcut or null",
  "subject": "{subject}",
  "section": "{section}",
  "exam": "{exam}",
  "exam_source": "AI Generated",
  "exam_year": null,
  "difficulty": "{difficulty}",
  "is_pyq": false,
  "source": "AI Generated",
  "lang": "en"
}}"""
    return await ask_ai_json(prompt)


async def translate_question(q: dict, target_lang: str) -> dict:
    """Translate a question dict to Hindi or Bengali"""
    if target_lang == "en" or not target_lang:
        return q
    lang_name = {"hi": "Hindi", "bn": "Bengali"}.get(target_lang, "Hindi")
    prompt = f"""Translate this MCQ to {lang_name}. Keep exam terminology accurate.
Keep option letters (A/B/C/D) as is. Only translate the text.

Question: {q['question']}
Options: {q['options']}
Explanation: {q.get('explanation','')}

Return JSON:
{{
  "question": "translated question",
  "options": ["A. translated", "B. translated", "C. translated", "D. translated"],
  "explanation": "translated explanation",
  "short_method": "translated or null"
}}"""
    try:
        translated = await ask_ai_json(prompt)
        q_copy = q.copy()
        q_copy["question"]    = translated.get("question", q["question"])
        q_copy["options"]     = translated.get("options", q["options"])
        q_copy["explanation"] = translated.get("explanation", q.get("explanation",""))
        q_copy["short_method"]= translated.get("short_method", q.get("short_method"))
        q_copy["lang"]        = target_lang
        return q_copy
    except Exception as e:
        print(f"[Translate] Failed: {e}")
        return q  # Return original on failure
