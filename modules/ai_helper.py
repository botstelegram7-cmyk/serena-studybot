import httpx, json
from config import GROQ_API_KEY, GEMINI_API_KEY, SAMBANOVA_API_KEY

GROQ_MODEL      = "llama-3.3-70b-versatile"
GEMINI_MODEL    = "gemini-1.5-flash"
SAMBANOVA_MODEL = "Meta-Llama-3.1-405B-Instruct"


async def _groq(prompt: str, system: str) -> str:
    if not GROQ_API_KEY: raise ValueError("No Groq key")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": GROQ_MODEL, "messages": msgs, "max_tokens": 2000})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def _gemini(prompt: str, system: str) -> str:
    if not GEMINI_API_KEY: raise ValueError("No Gemini key")
    full = f"{system}\n\n{prompt}" if system else prompt
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": full}]}]})
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _sambanova(prompt: str, system: str) -> str:
    if not SAMBANOVA_API_KEY: raise ValueError("No SambaNova key")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=50) as c:
        r = await c.post("https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {SAMBANOVA_API_KEY}"},
            json={"model": SAMBANOVA_MODEL, "messages": msgs, "max_tokens": 2000})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def ask_ai(prompt: str, system: str = "") -> str:
    """Groq → Gemini → SambaNova auto fallback"""
    for name, fn, key in [
        ("Groq",      _groq,      GROQ_API_KEY),
        ("Gemini",    _gemini,    GEMINI_API_KEY),
        ("SambaNova", _sambanova, SAMBANOVA_API_KEY),
    ]:
        if not key: continue
        try:
            return await fn(prompt, system)
        except Exception as e:
            print(f"[AI] {name} failed: {e}")
    raise Exception("All AI providers failed")


async def ask_ai_json(prompt: str, system: str = "") -> dict | list:
    sys_prompt = (system + "\n\nRespond ONLY with valid JSON. No markdown, no backticks, no preamble.").strip()
    raw = await ask_ai(prompt, sys_prompt)
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(clean)
