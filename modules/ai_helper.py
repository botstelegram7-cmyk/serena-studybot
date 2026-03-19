import httpx, json, asyncio, time, re
from config import GROQ_API_KEY, GEMINI_API_KEY, SAMBANOVA_API_KEY

GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
SNOVA_MODEL  = "Meta-Llama-3.3-70B-Instruct"

# ── GLOBAL RATE LIMITER ───────────────────────────────────────
_cooldown: dict = {}   # provider → unix time when it's free again

def _is_cooling(provider: str) -> bool:
    return time.time() < _cooldown.get(provider, 0)

def _set_cooldown(provider: str, seconds: float):
    _cooldown[provider] = time.time() + seconds
    print(f"[AI] {provider} cooldown {seconds:.0f}s", flush=True)


async def _groq(prompt: str, system: str) -> str:
    if not GROQ_API_KEY: raise ValueError("No Groq key")
    if _is_cooling("groq"): raise Exception("Groq cooling down")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": GROQ_MODEL, "messages": msgs, "max_tokens": 2000}
        )
        if r.status_code == 429:
            retry_after = float(r.headers.get("retry-after", 30))
            _set_cooldown("groq", retry_after)
            raise Exception(f"Groq 429 — cooling {retry_after}s")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def _gemini(prompt: str, system: str) -> str:
    if not GEMINI_API_KEY: raise ValueError("No Gemini key")
    if _is_cooling("gemini"): raise Exception("Gemini cooling down")
    full = f"{system}\n\n{prompt}" if system else prompt
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": full}]}],
                  "generationConfig": {"maxOutputTokens": 2000}}
        )
        if r.status_code == 429:
            _set_cooldown("gemini", 60)
            raise Exception("Gemini 429 — cooling 60s")
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _sambanova(prompt: str, system: str) -> str:
    if not SAMBANOVA_API_KEY: raise ValueError("No SambaNova key")
    if _is_cooling("sambanova"): raise Exception("SambaNova cooling down")
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(
            "https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {SAMBANOVA_API_KEY}"},
            json={"model": SNOVA_MODEL, "messages": msgs, "max_tokens": 2000}
        )
        if r.status_code in (429, 410):
            _set_cooldown("sambanova", 60)
            raise Exception(f"SambaNova {r.status_code}")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def ask_ai(prompt: str, system: str = "") -> str:
    """Try providers in order, skip ones that are cooling down"""
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
            result = await fn(prompt, system)
            # Success — clear any cooldown
            _cooldown.pop(name.lower(), None)
            return result
        except Exception as e:
            print(f"[AI] {name}: {str(e)[:80]}", flush=True)
            last_err = e
            continue

    raise Exception(f"All AI providers unavailable. Last: {last_err}")


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for sc, ec in [("[", "]"), ("{", "}")]:
        si = text.find(sc)
        if si == -1:
            continue
        chunk = text[si:]
        for ep in [chunk.rfind("},"), chunk.rfind("}")]:
            if ep > 0:
                try:
                    return json.loads(chunk[:ep+1] + ("]" if sc=="[" else ""))
                except Exception:
                    pass
    raise json.JSONDecodeError("Cannot extract JSON", text, 0)


async def ask_ai_json(prompt: str, system: str = "") -> dict | list:
    sp  = (system + "\n\nRespond ONLY with valid JSON. No markdown, no backticks.").strip()
    raw = await ask_ai(prompt, sp)
    return _extract_json(raw)
