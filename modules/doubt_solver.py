from modules.ai_helper import ask_ai
import re

EXAM_CTX = {
    "SSC":     "SSC CGL/CHSL 2025-26",
    "UPSC":    "UPSC CSE 2025-26",
    "JEE":     "JEE Mains/Advanced 2025-26",
    "RAILWAY": "RRB NTPC/Group D 2025-26",
}

# Strict math patterns — ONLY actual calculation questions
MATH_PATTERNS = [
    r'^\d+[\+\-\*\/×÷]\d+',                    # starts with arithmetic
    r'(profit|loss)\s*(of|on|is|=)\s*\d+',     # profit/loss with numbers
    r'(sp|cp|mp)\s*(=|is|of)\s*\d+',           # SP/CP/MP
    r'speed\s*(is|=|of)\s*\d+',                # speed problems
    r'(si|ci)\s*(on|is|=)\s*\d+',              # SI/CI
    r'\d+\s*(km|kg|rs|₹|meter|litre|liter)\s*(per|in|at|for)', # units in context
    r'find\s+the\s+(value|speed|profit|loss|area|volume|price|cost)',
    r'(evaluate|calculate|compute|solve)\s+\d',
    r'\d+\s*[x-z]\s*[\+\-\=]',                 # algebra like 2x + 5
    r'(average|mean)\s+of\s+\d+',
    r'ratio\s+\d+\s*:\s*\d+',
    r'(lcm|hcf|gcd)\s+of\s+\d+',
    r'\d+\%\s+of\s+\d+',                       # X% of Y
    r'(area|perimeter|volume)\s+of\s+(circle|triangle|square|rectangle|cylinder)',
    r'\d+\s*(hours?|days?|minutes?)\s+(work|pipe|fill|empty)',  # work problems
    r'train\s+\d+\s*(km|meter)',                # train problems
]

# Things that are DEFINITELY not math
NOT_MATH = [
    r'remind\s+me',
    r'how\s+(can|do|to|should)',
    r'what\s+is\s+[a-z\s]+\?',
    r'who\s+(is|was|are)',
    r'why\s+(is|was|does|do)',
    r'explain\s+[a-z]',
    r'tell\s+me',
    r'kya\s+hai',
    r'kaise',
    r'kyun',
    r'difference\s+between',
    r'define\s+[a-z]',
    r'crack\s+(ssc|upsc|jee|railway)',
    r'(strategy|tips|tricks|plan)\s+for',
    r'capital\s+of',
    r'(president|prime minister|minister)',
    r'(history|geography|polity|economy)\s+of',
    r'article\s+\d+\s+(of|in)',
    r'(reminder|remind|schedule|alarm|timer)',
    r'good\s+(morning|night|evening)',
    r'hello|hi\s|hey\s',
    r'thank',
    r'help\s+me\s+with\s+[a-z]',
    r'smart|intelligent|genius',
    r'motivation|motivate',
    r'(set|give)\s+(me\s+)?(a\s+)?reminder',
    r'in\s+\d+\s+minutes?\s+(later|time)',  # "in 5 minutes later"
    r'after\s+\d+\s+minutes?',
]


def _is_math(text: str) -> bool:
    tl = text.lower().strip()

    # First check — if it's clearly NOT math, return False immediately
    for pat in NOT_MATH:
        if re.search(pat, tl):
            return False

    # Check actual math patterns
    for pat in MATH_PATTERNS:
        if re.search(pat, tl, re.IGNORECASE):
            return True

    # Has MCQ options 1. 2. 3. 4. with numbers/₹ → math MCQ
    if re.search(r'^[1-4]\.\s*(₹|Rs\.?|\d)', tl, re.MULTILINE):
        return True

    return False


ROUGH_SYS = """Solve this exam Maths/Quant question exactly like a topper writes on rough paper.

STRICT:
- Max 10 lines
- ONLY numbers, variables, symbols — zero English/Hindi words
- NO LaTeX, NO $$, NO explanations
- Each step = new line
- Short 2-word heading
- End: — Technical Serena

STYLE:
Quick Solve
CP = 1.6x
0.25(1.6x) - 0.1x = 225
0.3x = 225
x = 750
CP1 = 1200
— Technical Serena"""


GENERAL_SYS = """You are {exam} expert. Student name: {name}.

IMPORTANT: This is NOT a maths question. Give a helpful general answer.

Format:
✅ [Direct answer — 1 line]
📌 [Explanation — 2-3 lines]
🧠 [Tip/trick — 1 line]

Keep it short and helpful. Use Hinglish if needed."""


async def solve_doubt(question: str, exam: str, name: str, lang: str = "en") -> str:
    is_math = _is_math(question)

    if is_math:
        try:
            r = await ask_ai(f"Solve (rough copy, max 10 lines):\n{question}", ROUGH_SYS)
            return f"```\n{r.strip()}\n```"
        except Exception as e:
            return f"❌ Retry karo. ({str(e)[:50]})"
    else:
        system = GENERAL_SYS.format(
            name=name,
            exam=EXAM_CTX.get(exam, "competitive exam 2025-26")
        )
        try:
            r = await ask_ai(question, system)
            return f"🎓 **{name}:**\n\n{r.strip()}"
        except Exception as e:
            return f"❌ Retry karo. ({str(e)[:50]})"
