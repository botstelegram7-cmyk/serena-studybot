import httpx, json, asyncio, time, re
from config import GROQ_API_KEY, GEMINI_API_KEY, SAMBANOVA_API_KEY

# ── UPDATED MODELS ────────────────────────────────────────────
GROQ_MODEL      = "llama-3.3-70b-versatile"
GEMINI_MODEL    = "gemini-2.0-flash"          # Fixed: 1.5-flash is 404
SAMBANOVA_MODEL = "Meta-Llama-3.3-70B-Instruct"  # Fixed: 405B is 410 GONE

# ── RATE LIMITING ─────────────────────────────────────────────
_last_call: dict = {}   # provider → timestamp
_MIN_GAP = 1.5          # minimum seconds between calls per provider

async def _rate_limit(provider: str):
    """Ensure minimum gap between calls to same provider"""
    last = _last_call.get(provider, 0)
    gap  = time.time() - last
    if gap < _MIN_GAP:
        await asyncio.sleep(_MIN_GAP - gap)
    _last_call[provider] = time.time()


async def _groq(prompt: str, system: str) -> str:
    if not GROQ_API_KEY: raise ValueError("No Groq key")
    await _rate_limit("groq")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": GROQ_MODEL, "messages": msgs, "max_tokens": 2000}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def _gemini(prompt: str, system: str) -> str:
    if not GEMINI_API_KEY: raise ValueError("No Gemini key")
    await _rate_limit("gemini")
    full = f"{system}\n\n{prompt}" if system else prompt
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": full}]}],
                "generationConfig": {"maxOutputTokens": 2000}
            }
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _sambanova(prompt: str, system: str) -> str:
    if not SAMBANOVA_API_KEY: raise ValueError("No SambaNova key")
    await _rate_limit("sambanova")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(
            "https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {SAMBANOVA_API_KEY}"},
            json={"model": SAMBANOVA_MODEL, "messages": msgs, "max_tokens": 2000}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def ask_ai(prompt: str, system: str = "") -> str:
    """Groq → Gemini → SambaNova with rate limiting"""
    providers = [
        ("Groq",      _groq,      GROQ_API_KEY),
        ("Gemini",    _gemini,    GEMINI_API_KEY),
        ("SambaNova", _sambanova, SAMBANOVA_API_KEY),
    ]
    last_err = None
    for name, fn, key in providers:
        if not key:
            continue
        try:
            return await fn(prompt, system)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            print(f"[AI] {name} HTTP {status}: {e}", flush=True)
            if status == 429:
                # Rate limited — wait before trying next
                await asyncio.sleep(3)
            last_err = e
        except Exception as e:
            print(f"[AI] {name} failed: {e}", flush=True)
            last_err = e
    raise Exception(f"All AI providers failed. Last: {last_err}")


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting array
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        if start != -1:
            chunk = text[start:]
            # Try progressively shorter
            for end_pos in [chunk.rfind("},"), chunk.rfind("}")]:
                if end_pos > 0:
                    candidate = chunk[:end_pos+1] + ("]" if start_char=="[" else "")
                    try:
                        return json.loads(candidate)
                    except Exception:
                        pass
    raise json.JSONDecodeError("Cannot extract JSON", text, 0)


async def ask_ai_json(prompt: str, system: str = "") -> dict | list:
    sys_p = (system + "\n\nRespond ONLY with valid JSON. No markdown, no backticks.").strip()
    raw   = await ask_ai(prompt, sys_p)
    return _extract_json(raw)
