import os
from dotenv import load_dotenv
load_dotenv()

# ── TELEGRAM ──────────────────────────────────────────────────
API_ID        = int(os.getenv("API_ID", 0))
API_HASH      = os.getenv("API_HASH", "")
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")

# ── OWNERS (Both IDs) ─────────────────────────────────────────
OWNER_IDS     = [1598576202, 6518065496]   # Hardcoded + env support
_env_owners   = os.getenv("OWNER_IDS", "")
if _env_owners:
    for _oid in _env_owners.split(","):
        try:
            _id = int(_oid.strip())
            if _id not in OWNER_IDS:
                OWNER_IDS.append(_id)
        except ValueError:
            pass

# ── MONGODB ───────────────────────────────────────────────────
MONGO_URI     = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME       = os.getenv("DB_NAME", "studybot")

# ── AI PROVIDERS (Free Tier) ──────────────────────────────────
# 👉 https://console.groq.com          → FREE 14400 req/day
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
# 👉 https://aistudio.google.com       → FREE 1500 req/day
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
# 👉 https://cloud.sambanova.ai        → FREE
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")

# ── OPTIONAL QUIZ APIS ────────────────────────────────────────
# 👉 https://quizapi.io                → FREE 100 req/day
QUIZ_API_KEY      = os.getenv("QUIZ_API_KEY", "")
# 👉 https://opentdb.com               → FREE unlimited
OPENTDB_ENABLED   = os.getenv("OPENTDB_ENABLED", "true").lower() == "true"
# 👉 https://the-trivia-api.com        → FREE
TRIVIA_API_ENABLED = os.getenv("TRIVIA_API_ENABLED", "true").lower() == "true"

# ── SERVER ────────────────────────────────────────────────────
PORT              = int(os.getenv("PORT", 8080))

# ── BOT CONFIG ────────────────────────────────────────────────
MAX_DAILY_DOUBTS  = int(os.getenv("MAX_DAILY_DOUBTS", 30))
POLL_TIMER        = int(os.getenv("POLL_TIMER", 60))   # seconds per question
BOT_NAME          = "SerenaStudy"

# ── SUPPORTED LANGUAGES ───────────────────────────────────────
LANGUAGES = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "bn": "🇧🇩 Bengali",
}
DEFAULT_LANG = "en"

# ── EXAMS & SUBJECTS ─────────────────────────────────────────
EXAMS = {
    "SSC":     ["Quant", "English", "Reasoning", "GK"],
    "UPSC":    ["History", "Polity", "Geography", "Economy", "Science", "Current Affairs"],
    "JEE":     ["Physics", "Chemistry", "Maths"],
    "RAILWAY": ["Quant", "Reasoning", "GK", "General Science"],
}

# ── DIFFICULTY LEVELS ─────────────────────────────────────────
DIFFICULTIES = ["Easy", "Medium", "Hard", "PYQ"]  # PYQ = real exam level
