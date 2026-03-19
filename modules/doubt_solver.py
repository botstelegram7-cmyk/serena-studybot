from modules.ai_helper import ask_ai
import re

EXAM_CTX = {
    "SSC":"SSC CGL/CHSL 2025-26","UPSC":"UPSC CSE 2025-26",
    "JEE":"JEE Mains/Advanced 2025-26","RAILWAY":"RRB NTPC/GD 2025-26",
}

MATH_KW = [
    "%","profit","loss","si","ci","speed","distance","time","ratio","average",
    "mixture","lcm","hcf","train","work","pipe","age","area","volume",
    "discount","cost","price","प्रतिशत","लाभ","=","×","÷","√","²","x","y",
    "find","calculate","solve","value","percent","number","algebra"
]

def _is_math(t): 
    tl = t.lower()
    return any(k in tl for k in MATH_KW) or bool(re.search(r'\d',t))

ROUGH_SYS = """Solve like a TOPPER writing on rough paper during SSC/JEE exam.

RULES (STRICT):
- Max 8-10 lines ONLY — short and direct
- ONLY numbers and symbols — zero explanation words
- NO LaTeX, NO $$, NO \\frac, NO "Let", NO "Therefore"
- Each step = new line
- Start: one 2-word heading
- End: — Technical Serena

EXAMPLE (copy this style):
Quick Solve
1.15x + 0.75x = 2014
1.90x = 2014
x = 1060

Another:
SP = 120% of 800 = 960
Discount = 10%
Final = 960 × 0.9 = 864
Profit = 864 - 800 = 64

— Technical Serena"""

THEORY_SYS = """You are {exam} expert. Student: {name}.

STRICT FORMAT:
✅ [Answer — 1 line]
📌 [Why — 2 lines max]
🧠 [Memory trick — 1 line]
📋 [2025-26 exam angle — 1 line]
— Technical Serena

Total: under 8 lines. No paragraphs."""

async def solve_doubt(question, exam, name, lang="en"):
    is_math = _is_math(question)
    if is_math:
        system = ROUGH_SYS
        prompt = f"Solve (max 10 lines rough copy style):\n{question}"
    else:
        system = THEORY_SYS.format(name=name, exam=EXAM_CTX.get(exam,"competitive exam"))
        prompt = question
    try:
        r = await ask_ai(prompt, system)
        if is_math:
            return f"```\n{r.strip()}\n```"
        return f"🎓 **{name}:**\n\n{r.strip()}"
    except Exception as e:
        return f"❌ Retry karo. ({str(e)[:50]})"
