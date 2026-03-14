"""
Optional external Quiz API integrations.
These supplement the local DB and AI-generated questions.

APIs Used:
  1. Open Trivia DB  — https://opentdb.com          (FREE, no key needed)
  2. The Trivia API  — https://the-trivia-api.com   (FREE, no key needed)
  3. QuizAPI.io      — https://quizapi.io            (FREE 100/day, needs key)
"""
import httpx
from config import QUIZ_API_KEY, OPENTDB_ENABLED, TRIVIA_API_ENABLED


# ── CATEGORY MAPPINGS ─────────────────────────────────────────
# OpenTDB category IDs relevant to our exams
OPENTDB_CATEGORIES = {
    "GK":      9,   # General Knowledge
    "History": 23,  # History
    "Polity":  24,  # Politics
    "Science": 17,  # Science & Nature
    "Maths":   19,  # Mathematics
    "Geography": 22, # Geography
}

# Trivia API categories
TRIVIA_CATEGORIES = {
    "GK":       "general_knowledge",
    "History":  "history",
    "Science":  "science",
    "Maths":    "mathematics",
    "Geography": "geography",
}


async def fetch_opentdb(subject: str, count: int = 10, difficulty: str = "medium") -> list:
    """Fetch from Open Trivia Database — completely free, no key"""
    if not OPENTDB_ENABLED:
        return []
    cat_id = OPENTDB_CATEGORIES.get(subject)
    diff   = difficulty.lower() if difficulty.lower() in ["easy","medium","hard"] else "medium"
    params = {"amount": count, "type": "multiple", "difficulty": diff}
    if cat_id:
        params["category"] = cat_id
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://opentdb.com/api.php", params=params)
            data = r.json()
            if data.get("response_code") != 0:
                return []
            questions = []
            for item in data.get("results", []):
                # Build options list
                incorrect = item.get("incorrect_answers", [])
                correct   = item.get("correct_answer", "")
                all_opts  = incorrect + [correct]
                import random; random.shuffle(all_opts)
                answer_letter = chr(65 + all_opts.index(correct))  # A/B/C/D
                opts = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(all_opts)]
                questions.append({
                    "question":    item["question"],
                    "options":     opts,
                    "answer":      answer_letter,
                    "explanation": f"Correct answer: {correct}",
                    "short_method": None,
                    "subject":     subject,
                    "section":     subject,
                    "difficulty":  item.get("difficulty","medium").title(),
                    "source":      "Open Trivia DB",
                    "is_pyq":      False,
                    "exam_year":   None,
                    "exam_date":   None,
                })
            return questions
    except Exception as e:
        print(f"[OpenTDB] {e}")
        return []


async def fetch_trivia_api(subject: str, count: int = 10, difficulty: str = "medium") -> list:
    """Fetch from The Trivia API — free, no key"""
    if not TRIVIA_API_ENABLED:
        return []
    cat   = TRIVIA_CATEGORIES.get(subject, "general_knowledge")
    diff  = difficulty.lower() if difficulty.lower() in ["easy","medium","hard"] else "medium"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://the-trivia-api.com/v2/questions",
                params={"categories": cat, "limit": count, "difficulty": diff})
            items = r.json()
            questions = []
            for item in items:
                correct     = item.get("correctAnswer","")
                incorrects  = item.get("incorrectAnswers",[])
                all_opts    = incorrects + [correct]
                import random; random.shuffle(all_opts)
                answer_letter = chr(65 + all_opts.index(correct))
                opts = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(all_opts)]
                questions.append({
                    "question":    item.get("question",{}).get("text",""),
                    "options":     opts,
                    "answer":      answer_letter,
                    "explanation": f"Correct: {correct}",
                    "short_method": None,
                    "subject":     subject,
                    "section":     item.get("category", subject),
                    "difficulty":  diff.title(),
                    "source":      "The Trivia API",
                    "is_pyq":      False,
                    "exam_year":   None,
                    "exam_date":   None,
                })
            return questions
    except Exception as e:
        print(f"[TriviaAPI] {e}")
        return []


async def fetch_quizapi(subject: str, count: int = 10) -> list:
    """Fetch from QuizAPI.io — 100 req/day free"""
    if not QUIZ_API_KEY:
        return []
    tag_map = {
        "Science": "Linux",
        "GK":      "DevOps",
        "Maths":   "Docker",
    }
    tag = tag_map.get(subject, "Linux")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://quizapi.io/api/v1/questions",
                headers={"X-Api-Key": QUIZ_API_KEY},
                params={"limit": count, "tags": tag})
            items = r.json()
            questions = []
            for item in items:
                answers = item.get("answers", {})
                correct_ans = item.get("correct_answers", {})
                opts = []
                correct_letter = "A"
                for key in ["answer_a","answer_b","answer_c","answer_d"]:
                    val = answers.get(key)
                    if val:
                        letter = key.split("_")[1].upper()
                        opts.append(f"{letter}. {val}")
                        if correct_ans.get(f"{key}_correct") == "true":
                            correct_letter = letter
                if opts:
                    questions.append({
                        "question":    item.get("question",""),
                        "options":     opts,
                        "answer":      correct_letter,
                        "explanation": item.get("explanation","") or f"Correct: {correct_letter}",
                        "short_method": None,
                        "subject":     subject,
                        "section":     subject,
                        "difficulty":  "Medium",
                        "source":      "QuizAPI",
                        "is_pyq":      False,
                        "exam_year":   None,
                        "exam_date":   None,
                    })
            return questions
    except Exception as e:
        print(f"[QuizAPI] {e}")
        return []


async def fetch_external_questions(subject: str, count: int = 10,
                                    difficulty: str = "medium") -> list:
    """
    Master function — tries all external APIs and combines results.
    Falls back gracefully if any API is down.
    """
    results = []

    # Try OpenTDB
    if len(results) < count:
        qs = await fetch_opentdb(subject, min(count, 10), difficulty)
        results.extend(qs)

    # Try Trivia API
    if len(results) < count:
        qs = await fetch_trivia_api(subject, min(count - len(results), 10), difficulty)
        results.extend(qs)

    # Try QuizAPI
    if len(results) < count and QUIZ_API_KEY:
        qs = await fetch_quizapi(subject, min(count - len(results), 10))
        results.extend(qs)

    return results[:count]
