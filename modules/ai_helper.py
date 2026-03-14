import httpx, json, re
from config import GROQ_API_KEY, GEMINI_API_KEY, SAMBANOVA_API_KEY

GROQ_MODEL      = "llama-3.3-70b-versatile"
GEMINI_MODEL    = "gemini-1.5-flash"
SAMBANOVA_MODEL = "Meta-Llama-3.1-405B-Instruct"


async def _groq(prompt: str, system: str) -> str:
    if not GROQ_API_KEY: raise ValueError("No Groq key")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": GROQ_MODEL, "messages": msgs, "max_tokens": 4000})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def _gemini(prompt: str, system: str) -> str:
    if not GEMINI_API_KEY: raise ValueError("No Gemini key")
    full = f"{system}\n\n{prompt}" if system else prompt
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": full}]}],
                  "generationConfig": {"maxOutputTokens": 4000}})
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _sambanova(prompt: str, system: str) -> str:
    if not SAMBANOVA_API_KEY: raise ValueError("No SambaNova key")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {SAMBANOVA_API_KEY}"},
            json={"model": SAMBANOVA_MODEL, "messages": msgs, "max_tokens": 4000})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def ask_ai(prompt: str, system: str = "") -> str:
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


def _extract_json(text: str):
    """
    Robust JSON extractor — handles:
    - Markdown code fences
    - Truncated/incomplete JSON arrays
    - Extra text before/after JSON
    """
    # 1. Strip markdown fences
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()

    # 2. Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Find JSON array in text
    arr_start = text.find("[")
    if arr_start != -1:
        # Try progressively shorter substrings to find valid JSON
        chunk = text[arr_start:]
        # Try closing at last complete object
        last_brace = chunk.rfind("},")
        if last_brace != -1:
            candidate = chunk[:last_brace + 1] + "]"
            try:
                return json.loads(candidate)
            except Exception:
                pass
        # Try up to last }
        last_brace2 = chunk.rfind("}")
        if last_brace2 != -1:
            candidate = chunk[:last_brace2 + 1] + "]"
            try:
                return json.loads(candidate)
            except Exception:
                pass

    # 4. Find JSON object
    obj_start = text.find("{")
    if obj_start != -1:
        chunk = text[obj_start:]
        last_brace = chunk.rfind("}")
        if last_brace != -1:
            candidate = chunk[:last_brace + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass

    raise json.JSONDecodeError("Could not extract JSON", text, 0)


async def ask_ai_json(prompt: str, system: str = "") -> dict | list:
    sys_prompt = (system + "\n\nRespond ONLY with valid JSON. No markdown, no backticks, no preamble. No trailing commas.").strip()
    raw = await ask_ai(prompt, sys_prompt)
    return _extract_json(raw)
