import random
from modules.ai_helper import ask_ai_json

SECTION_MAP = {
    "Quant":    ["Percentage","Profit & Loss","SI & CI","Time & Work",
                 "Speed Distance Time","Ratio & Proportion","Number System",
                 "Algebra","Geometry","Trigonometry","DI","Average","Mixture"],
    "English":  ["Error Spotting","Fill in Blanks","Sentence Improvement",
                 "Synonyms & Antonyms","Idioms & Phrases","Para Jumbles",
                 "Cloze Test","One Word Substitution","Reading Comprehension"],
    "Reasoning":["Analogy","Series","Coding-Decoding","Blood Relations",
                 "Direction Sense","Puzzles","Syllogism","Venn Diagram",
                 "Mirror Image","Paper Folding","Matrix"],
    "GK":       ["Polity","History","Geography","Economy","Science & Tech",
                 "Sports 2025-26","Awards 2025-26","Current Affairs 2025-26",
                 "Budget 2025-26","Appointments 2025-26","Static GK"],
    "Physics":  ["Mechanics","Optics","Thermodynamics","Electricity",
                 "Magnetism","Modern Physics","Semiconductors"],
    "Chemistry":["Physical Chemistry","Organic Chemistry","Inorganic Chemistry",
                 "Chemical Bonding","Electrochemistry","Thermodynamics"],
    "Maths":    ["Algebra","Calculus","Coordinate Geometry","Trigonometry",
                 "Probability","Matrices","3D Geometry","Integration"],
    "History":  ["Ancient India","Medieval India","Modern India",
                 "Freedom Struggle","Art & Culture","World History"],
    "Polity":   ["Constitution","Fundamental Rights","DPSP","Parliament",
                 "Judiciary","Federalism","Local Government","Elections 2024-25"],
    "Geography":["Physical Geography","Indian Geography","World Geography",
                 "Climate Change 2025","Rivers & Lakes","Resources"],
    "Economy":  ["Indian Economy","Union Budget 2025-26","RBI Policy 2025",
                 "Banking 2025","Schemes 2025-26","International Trade"],
    "Science":  ["Physics","Chemistry","Biology","Space ISRO 2025",
                 "Environment 2025","Computer & AI"],
    "Current Affairs": ["National 2025-26","International 2025-26",
                        "Sports 2025-26","Awards 2025-26","Appointments 2025-26",
                        "Science & Tech 2025-26","Defence 2025-26"],
    "General Science": ["Physics","Chemistry","Biology","Computer","Environment"],
}

PYQ_EXAM_DATES = {
    "SSC": [
        ("SSC CGL 2025 Tier-I",        "2025"),
        ("SSC CGL 2025 Tier-II",        "2025"),
        ("SSC CHSL 2025 Tier-I",        "2025"),
        ("SSC CPO 2025",                "2025"),
        ("SSC GD 2025",                 "2025"),
        ("SSC MTS 2025",                "2025"),
        ("SSC CGL 2024 Tier-I",         "2024"),
        ("SSC CGL 2024 Tier-II",        "2024"),
        ("SSC CHSL 2024",               "2024"),
        ("SSC JE 2024",                 "2024"),
        ("SSC GD 2024",                 "2024"),
        ("SSC Stenographer 2024",       "2024"),
    ],
    "UPSC": [
        ("UPSC CSE Prelims 2025",       "2025"),
        ("UPSC CSE Prelims 2024",       "2024"),
        ("UPSC CAPF 2025",              "2025"),
        ("UPSC NDA I 2025",             "2025"),
        ("UPSC CDS I 2025",             "2025"),
        ("UPSC NDA II 2024",            "2024"),
        ("UPSC CDS II 2024",            "2024"),
        ("UPSC CSE Prelims 2023",       "2023"),
    ],
    "JEE": [
        ("JEE Mains Jan 2026 S1",       "2026"),
        ("JEE Mains Jan 2026 S2",       "2026"),
        ("JEE Mains Apr 2025 S1",       "2025"),
        ("JEE Mains Apr 2025 S2",       "2025"),
        ("JEE Mains Jan 2025 S1",       "2025"),
        ("JEE Advanced 2025",           "2025"),
        ("JEE Advanced 2024",           "2024"),
        ("JEE Mains Jan 2024",          "2024"),
    ],
    "RAILWAY": [
        ("RRB NTPC 2025 CBT-1",         "2025"),
        ("RRB Group D 2025 Phase-I",    "2025"),
        ("RRB ALP 2025 CBT-1",          "2025"),
        ("RRB JE 2025",                 "2025"),
        ("RRB NTPC 2024 CBT-2",         "2024"),
        ("RRB Group D 2024 Phase-II",   "2024"),
        ("RRB NTPC 2024 CBT-1",         "2024"),
        ("RRB Group D 2024",            "2024"),
    ],
}

# 2025-26 exam pattern notes
PATTERN_2026 = {
    "SSC": """2025-26 SSC Pattern Changes:
- CGL Tier-1: 60 min, 60 Q (no sectional cutoff removed)
- More Data Interpretation sets
- Current Affairs from last 6 months
- Quant: Higher difficulty, multi-step problems
- English: More vocab-based, idioms focus
- Ediquity pattern: application-based, not formula-rote""",

    "UPSC": """2025-26 UPSC Trend:
- CSAT more analytical reasoning
- Current Affairs: Budget 2025-26, Census 2024
- Environment & Climate prominent
- Technology: AI policy, Space (Chandrayaan-4 prep)
- Ediquity focus: conceptual depth over factual recall""",

    "JEE": """2025-26 JEE Pattern:
- NTA reformed paper: 75 Q, 3hrs
- More application-based, less formula plug-in
- Integer type questions increased
- Physics: Modern Physics weightage up
- Ediquity style: multi-concept integration""",

    "RAILWAY": """2025-26 Railway Trend:
- RRB NTPC new cycle: CBT-1 changed weightage
- GK: Schemes, appointments, sports 2024-25
- Reasoning: New puzzle types
- Maths: Speed & accuracy focus
- Ediquity: real-world application questions""",
}


async def generate_pyq_batch(exam: str, subject: str, section: str = None,
                              count: int = 5, difficulty: str = "Medium") -> list:
    if not section:
        section = random.choice(SECTION_MAP.get(subject, [subject]))

    exam_instance, exam_year = random.choice(
        PYQ_EXAM_DATES.get(exam, [("Unknown Exam 2025", "2025")])
    )

    diff_map = {
        "Easy":    "straightforward, direct formula application",
        "Medium":  "2-3 step problem, slight trick involved",
        "Hard":    "multi-step, concept combination, tricky options",
        "Extreme": "EXTREMELY HARD — 4+ steps, multiple concepts, options designed to trap toppers, only top 1% can solve",
    }
    diff_desc  = diff_map.get(difficulty, diff_map["Medium"])
    pattern_note = PATTERN_2026.get(exam, "")
    style = {
        "SSC":     "SSC 2025-26 exam style — speed + accuracy, real exam feel",
        "UPSC":    "UPSC 2025-26 Prelims style — analytical, very close options",
        "JEE":     "JEE 2025-26 Mains style — application-based, multi-concept",
        "RAILWAY": "RRB 2025-26 style — straightforward but tricky options",
    }.get(exam, "competitive exam 2025-26 style")

    batch = min(count, 5)

    prompt = f"""You are an expert Indian competitive exam question maker with complete knowledge up to March 2026.

Create exactly {batch} MCQ questions.
Exam: {exam} — Style: {exam_instance} ({exam_year})
Subject: {subject} | Topic: {section}
Difficulty: {difficulty} — {diff_desc}
Style guide: {style}

Current Exam Pattern 2025-26:
{pattern_note}

IMPORTANT RULES:
- Use LATEST 2025-26 data (Budget 2025-26, new appointments, recent events, new schemes)
- Follow Ediquity-style: application-based, not just memorization
- For Extreme difficulty: create questions that require 4+ steps, multiple formula combinations
- Options should be VERY close to trap students
- For Quant: use realistic numbers from actual exam papers
- For GK: use verified 2024-25 facts only

Return ONLY JSON array (no other text):
[{{
  "question": "complete question (max 2 lines for quant, 3 for theory)",
  "options": ["A. opt1", "B. opt2", "C. opt3", "D. opt4"],
  "answer": "A",
  "explanation": "1-2 line solution/reason",
  "short_method": "fastest shortcut for quant/reasoning or null",
  "subject": "{subject}",
  "section": "{section}",
  "exam": "{exam}",
  "exam_source": "{exam_instance}",
  "exam_year": "{exam_year}",
  "difficulty": "{difficulty}",
  "is_pyq": true,
  "source": "{exam_instance}"
}}]"""

    try:
        result = await ask_ai_json(prompt)
        if isinstance(result, list):
            return result[:batch]
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    return v[:batch]
    except Exception as e:
        print(f"[QGen] Failed: {e}")
    return []


async def translate_question(q: dict, target_lang: str) -> dict:
    if target_lang == "en":
        return q
    lang_name = {"hi": "Hindi", "bn": "Bengali"}.get(target_lang, "Hindi")
    prompt = f"""Translate MCQ to {lang_name}. Keep A/B/C/D as is.
Q: {q['question']}
Options: {q['options']}
Return JSON: {{"question":"...","options":["A....","B....","C....","D...."]}}"""
    try:
        t = await ask_ai_json(prompt)
        qc = q.copy()
        qc.update({"question": t.get("question", q["question"]),
                   "options": t.get("options", q["options"]),
                   "lang": target_lang})
        return qc
    except Exception:
        return q
