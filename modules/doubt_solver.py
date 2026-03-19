from modules.ai_helper import ask_ai
import re

EXAM_CTX = {
    "SSC":     "SSC CGL/CHSL 2025-26",
    "UPSC":    "UPSC CSE 2025-26",
    "JEE":     "JEE Mains/Advanced 2025-26",
    "RAILWAY": "RRB NTPC/Group D 2025-26",
}

# Only actual maths/quant patterns — NOT general questions
MATH_PATTERNS = [
    r'\d+\s*[%×÷\+\-\*\/]\s*\d+',   # number operator number
    r'\d+\s*(percent|%)',             # percentage
    r'(profit|loss|discount|sp|cp|mp)\s*(of|is|=|:)',  # commerce
    r'(speed|distance|time)\s*(of|is|=|:|\d)',         # SDT
    r'(find|calculate|evaluate|solve|what is the value)',  # solve commands
    r'(lcm|hcf|gcd)\s*of',
    r'(average|mean)\s*of',
    r'(area|volume|perimeter)\s*of',
    r'(\d+x|\dx)\s*[\+\-\=]',        # algebra like 2x + 5
    r'(si|ci|interest)\s*(=|is|on)',  # SI/CI
    r'train.*speed|speed.*train',
    r'pipe.*tank|tank.*pipe',
    r'work.*days|days.*work',
    r'ratio\s*\d+\s*:\s*\d+',
    r'\d+\s*(km|kg|liter|litre|rs|₹|meter|hour|min)',
]

GENERAL_PATTERNS = [
    r'how can i', r'how do i', r'what is', r'who is', r'why is',
    r'explain', r'tell me', r'kya hai', r'kaise', r'kyun',
    r'difference between', r'define', r'meaning of',
    r'crack ssc', r'crack upsc', r'crack jee', r'prepare',
    r'smart', r'topper', r'strategy', r'tips', r'trick',
    r'history of', r'article \d+', r'constitution',
    r'capital of', r'president', r'minister', r'scheme',
]


def _is_math(text: str) -> bool:
    tl = text.lower().strip()

    # If matches general pattern → definitely NOT math
    for pat in GENERAL_PATTERNS:
        if re.search(pat, tl):
            return False

    # Check math patterns
    for pat in MATH_PATTERNS:
        if re.search(pat, tl, re.IGNORECASE):
            return True

    # Has options like 1. 2. 3. 4. → likely a MCQ math question
    if re.search(r'^[1-4]\.\s*₹?\d', tl, re.MULTILINE):
        return True

    return False


ROUGH_SYS = """Solve this exam question like a TOPPER writing on rough paper.

STRICT RULES:
- Max 10 lines total
- ONLY numbers, variables, symbols
- NO words like "Let", "Therefore", "Hence", "Profit", "Solution", "Answer"
- NO LaTeX, NO $$, NO explanations
- Each calculation = new line
- Short 2-word heading first
- End with: — Technical Serena

STYLE:
Quick Solve
CP1 = 1.6CP2
SP1 = 1.25CP1
0.25CP1 - 0.1CP2 = 225
0.3CP2 = 225
CP2 = 750
CP1 = 1200
— Technical Serena"""


THEORY_SYS = """You are {exam} expert teacher. Student: {name}.

Answer in this EXACT format (strict):
✅ [Direct answer — 1 line]
📌 [Core concept — 2 lines max]
🧠 [Memory trick — 1 line]
📋 [2025-26 exam tip — 1 line]

Total under 6 lines. Simple. No paragraphs. No bullet lists."""


async def solve_doubt(question: str, exam: str, name: str, lang: str = "en") -> str:
    is_math = _is_math(question)

    if is_math:
        system = ROUGH_SYS
        prompt = f"Solve (rough copy, max 10 lines):\n{question}"
        try:
            r = await ask_ai(prompt, system)
            return f"```\n{r.strip()}\n```"
        except Exception as e:
            return f"❌ Retry karo. ({str(e)[:50]})"
    else:
        system = THEORY_SYS.format(
            name=name,
            exam=EXAM_CTX.get(exam, "competitive exam 2025-26")
        )
        try:
            r = await ask_ai(question, system)
            return f"🎓 **{name}:**\n\n{r.strip()}"
        except Exception as e:
            return f"❌ Retry karo. ({str(e)[:50]})"
