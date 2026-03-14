from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, date
from urllib.parse import quote_plus
from config import MONGO_URI, DB_NAME, DEFAULT_LANG


def _safe_mongo_uri(uri: str) -> str:
    """Auto-encode special chars in MongoDB URI password"""
    try:
        if "://" not in uri or "@" not in uri:
            return uri
        scheme, rest = uri.split("://", 1)
        credentials, host_part = rest.rsplit("@", 1)
        if ":" in credentials:
            user, password = credentials.split(":", 1)
            return f"{scheme}://{quote_plus(user)}:{quote_plus(password)}@{host_part}"
        return uri
    except Exception:
        return uri


client = AsyncIOMotorClient(_safe_mongo_uri(MONGO_URI))
db     = client[DB_NAME]

users_col     = db["users"]
questions_col = db["questions"]     # All questions incl PYQ
sessions_col  = db["test_sessions"]
tests_col     = db["completed_tests"]
daily_col     = db["daily_quiz"]
doubts_rl_col = db["doubts_rl"]


# ══════════════════════════════ USERS ════════════════════════
async def get_or_create_user(uid: int, name: str, username: str = ""):
    u = await users_col.find_one({"uid": uid})
    if not u:
        await users_col.insert_one({
            "uid": uid, "name": name, "username": username,
            "joined": datetime.utcnow(),
            "lang": DEFAULT_LANG,          # en / hi / bn
            "exams": [],
            "preferred_difficulty": "Medium",
            "total_tests": 0,
            "total_questions": 0,
            "correct": 0,
            "subject_stats": {},
            "last_active": datetime.utcnow(),
        })
    else:
        await users_col.update_one({"uid": uid}, {"$set": {"last_active": datetime.utcnow()}})
    return await users_col.find_one({"uid": uid})

async def get_user(uid: int):
    return await users_col.find_one({"uid": uid})

async def update_user(uid: int, data: dict):
    await users_col.update_one({"uid": uid}, {"$set": data})

async def get_all_users():
    return await users_col.find({}).to_list(100000)

async def get_user_lang(uid: int) -> str:
    u = await users_col.find_one({"uid": uid}, {"lang": 1})
    return u.get("lang", DEFAULT_LANG) if u else DEFAULT_LANG

async def update_subject_stat(uid: int, subject: str, correct: bool):
    u = await get_user(uid)
    if not u:
        return
    stats = u.get("subject_stats", {})
    if subject not in stats:
        stats[subject] = {"total": 0, "correct": 0}
    stats[subject]["total"] += 1
    if correct:
        stats[subject]["correct"] += 1
    await users_col.update_one(
        {"uid": uid},
        {"$set":  {"subject_stats": stats},
         "$inc":  {"total_questions": 1, "correct": 1 if correct else 0}}
    )


# ══════════════════════════════ QUESTIONS ════════════════════
async def add_question(data: dict) -> str:
    """
    Required fields: exam, subject, question, options, answer, explanation
    Optional:  section, difficulty, source, exam_year, exam_date, 
               is_pyq(bool), short_method, lang
    """
    data.setdefault("created_at", datetime.utcnow())
    data.setdefault("is_pyq", False)
    data.setdefault("lang", "en")
    data.setdefault("difficulty", "Medium")
    r = await questions_col.insert_one(data)
    return str(r.inserted_id)

async def add_questions_bulk(questions: list) -> int:
    if not questions:
        return 0
    for q in questions:
        q.setdefault("created_at", datetime.utcnow())
        q.setdefault("is_pyq", False)
        q.setdefault("lang", "en")
        q.setdefault("difficulty", "Medium")
    r = await questions_col.insert_many(questions)
    return len(r.inserted_ids)

async def get_questions(exam: str, subject: str = None, section: str = None,
                        difficulty: str = None, is_pyq: bool = None,
                        count: int = 10, lang: str = None) -> list:
    query = {"exam": exam}
    if subject:    query["subject"]    = subject
    if section:    query["section"]    = section
    if difficulty and difficulty != "Any": query["difficulty"] = difficulty
    if is_pyq is not None: query["is_pyq"] = is_pyq
    if lang:       query["lang"]       = lang
    pipeline = [{"$match": query}, {"$sample": {"size": count}}]
    return await questions_col.aggregate(pipeline).to_list(count)

async def get_pyq_questions(exam: str, subject: str = None, count: int = 10) -> list:
    return await get_questions(exam, subject, is_pyq=True, count=count)

async def count_questions(exam: str = None, subject: str = None, is_pyq: bool = None) -> int:
    query = {}
    if exam:    query["exam"]    = exam
    if subject: query["subject"] = subject
    if is_pyq is not None: query["is_pyq"] = is_pyq
    return await questions_col.count_documents(query)

async def get_db_stats() -> dict:
    stats = {}
    from config import EXAMS
    for exam in EXAMS:
        total = await count_questions(exam)
        pyq   = await count_questions(exam, is_pyq=True)
        stats[exam] = {"total": total, "pyq": pyq}
    return stats


# ══════════════════════════════ TEST SESSIONS ════════════════
async def create_test_session(uid: int, data: dict):
    await sessions_col.update_one(
        {"uid": uid},
        {"$set": {**data, "uid": uid, "created_at": datetime.utcnow()}},
        upsert=True
    )

async def get_test_session(uid: int):
    return await sessions_col.find_one({"uid": uid})

async def update_test_session(uid: int, data: dict):
    await sessions_col.update_one({"uid": uid}, {"$set": data})

async def clear_test_session(uid: int):
    await sessions_col.delete_one({"uid": uid})


# ══════════════════════════════ COMPLETED TESTS ══════════════
async def save_completed_test(uid: int, data: dict):
    data["uid"] = uid
    data["completed_at"] = datetime.utcnow()
    await tests_col.insert_one(data)
    await users_col.update_one({"uid": uid}, {"$inc": {"total_tests": 1}})

async def get_user_tests(uid: int, limit: int = 10):
    return await tests_col.find({"uid": uid}).sort("completed_at", -1).limit(limit).to_list(limit)

async def get_leaderboard(exam: str, limit: int = 10):
    pipeline = [
        {"$match": {"exam": exam}},
        {"$group": {"_id": "$uid", "best_score": {"$max": "$percentage"}, "attempts": {"$sum": 1}}},
        {"$sort": {"best_score": -1}},
        {"$limit": limit}
    ]
    return await tests_col.aggregate(pipeline).to_list(limit)


# ══════════════════════════════ RATE LIMIT ════════════════════
async def check_doubt_limit(uid: int, max_per_day: int) -> tuple:
    today = str(date.today())
    doc = await doubts_rl_col.find_one({"uid": uid, "date": today})
    if not doc:
        await doubts_rl_col.insert_one({"uid": uid, "date": today, "count": 1})
        return True, max_per_day - 1
    if doc["count"] >= max_per_day:
        return False, 0
    await doubts_rl_col.update_one({"uid": uid, "date": today}, {"$inc": {"count": 1}})
    return True, max_per_day - doc["count"] - 1
