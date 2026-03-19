from modules.ai_helper import ask_ai
import re

EXAM_CTX = {
    "SSC":     "SSC CGL/CHSL/MTS/CPO 2025-26",
    "UPSC":    "UPSC CSE 2025-26",
    "JEE":     "JEE Mains/Advanced 2025-26",
    "RAILWAY": "RRB NTPC/Group D 2025-26",
}

MATH_KW = [
    "percent","%","profit","loss","si","ci","interest","speed","distance",
    "time","ratio","proportion","average","mixture","number","lcm","hcf",
    "train","work","pipe","age","solve","calculate","find","value","equation",
    "algebra","triangle","area","volume","probability","discount","cost","price",
    "प्रतिशत","लाभ","हानि","गति","औसत","अनुपात","প্রতিশত","গতি",
    "=","×","÷","+","-","²","√","x","y"
]

def _is_math(text: str) -> bool:
    tl = text.lower()
    return any(kw in tl for kw in MATH_KW) or bool(re.search(r'\d+', text))


ROUGH_COPY_SYSTEM = """You are solving a competitive exam Quant/Maths question like a TOPPER writes on a ROUGH COPY during SSC/JEE/Railway exam.

STRICT RULES — NO EXCEPTIONS:
1. Start with ONE random short heading (e.g. "SSC Quant", "Quick Solve", "Speed Test")
2. Write ONLY numbers, symbols, steps — NO explanation words
3. NO LaTeX, NO $$, NO \\frac, NO aligned — BANNED
4. NO words like "Let", "Therefore", "Hence", "Profit", "Loss", "Solution"
5. Each calculation on NEW LINE
6. Use = sign naturally like pen on paper
7. Show intermediate steps like rough work
8. End with: — Technical Serena

EXACT STYLE TO FOLLOW:
SSC Quant Booster
0.75 × 2540
= 1905
+ 109
= 2014
1.15x + 0.75x = 2014
1.90x = 2014
x = 2014 ÷ 1.90
x = 1060 ✓

ANOTHER EXAMPLE:
Speed Solve
CP = 100
SP = 120 → 20% profit
New SP = 120 × 0.9 = 108
Profit = 108 - 100 = 8%

— Technical Serena

REMEMBER: Raw. Direct. Rough copy feel. No theory. No formatting."""


THEORY_SYSTEM = """You are a {exam} expert teacher. Student name: {name}.

Answer format (strict):
✅ [Direct answer in 1 line]

📌 [Core concept — max 3 lines, simple language]

🌍 [1 real example everyone knows]

🧠 [Memory trick if possible — 1 line]

📋 [{exam} 2025-26 Exam Angle: how this is asked now]

— Technical Serena

No long paragraphs. Simple. Direct. Exam-focused."""


async def solve_doubt(question: str, exam: str, name: str, lang: str = "en") -> str:
    exam_ctx = EXAM_CTX.get(exam, "competitive exam 2025-26")
    is_math  = _is_math(question)

    if is_math:
        system = ROUGH_COPY_SYSTEM
        prompt = question
    else:
        system = THEORY_SYSTEM.format(name=name, exam=exam_ctx)
        prompt = question

    try:
        response = await ask_ai(prompt, system)
        if is_math:
            # Format as code block for monospace (rough copy feel)
            return f"```\n{response}\n```"
        else:
            return f"🎓 **{name}:**\n\n{response}"
    except Exception as e:
        return f"❌ AI busy hai, retry karo. ({str(e)[:60]})"
