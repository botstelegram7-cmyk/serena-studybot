import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_IDS, EXAMS, MAX_DAILY_DOUBTS

print("[bot.py] Loading...", flush=True)

app = Client(
    name      = "serena_studybot",
    api_id    = API_ID,
    api_hash  = API_HASH,
    bot_token = BOT_TOKEN,
    in_memory = True,
)

from database import (
    get_or_create_user, add_questions_bulk, count_questions,
    update_user, get_user, get_user_lang, get_db_stats,
    check_doubt_limit, get_all_users, get_image, set_image, get_all_images
)
from modules.mock_test    import start_mock_test, process_button_answer, clear_session, get_session
from modules.doubt_solver import solve_doubt
from modules.tracker      import get_progress_report, get_leaderboard_text
from modules.parser       import process_owner_upload

_upload_ctx: dict = {}
owner_filter = filters.user(OWNER_IDS)

print("[bot.py] Loaded ✅", flush=True)


# ═══════════════ EXAM IMAGES ══════════════════════════════════
EXAM_BANNERS = {
    "SSC":     "https://i.imgur.com/placeholder_ssc.jpg",    # Replace with real image URL
    "UPSC":    "https://i.imgur.com/placeholder_upsc.jpg",
    "JEE":     "https://i.imgur.com/placeholder_jee.jpg",
    "RAILWAY": "https://i.imgur.com/placeholder_rail.jpg",
}

# Exam theme emojis for colorful feel
EXAM_THEME = {
    "SSC":     {"emoji":"📋","color":"🟦","icon":"⚡"},
    "UPSC":    {"emoji":"🏛","color":"🟨","icon":"🎯"},
    "JEE":     {"emoji":"⚗️","color":"🟩","icon":"🔬"},
    "RAILWAY": {"emoji":"🚂","color":"🟥","icon":"🛤"},
}


# ═══════════════ KEYBOARDS ════════════════════════════════════
def start_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 SSC",      callback_data="exam_SSC"),
         InlineKeyboardButton("🏛 UPSC",     callback_data="exam_UPSC")],
        [InlineKeyboardButton("⚗️ JEE",      callback_data="exam_JEE"),
         InlineKeyboardButton("🚂 RAILWAY",  callback_data="exam_RAILWAY")],
        [InlineKeyboardButton("🌐 Language", callback_data="m_lang"),
         InlineKeyboardButton("📊 Progress", callback_data="m_prog")],
    ])

def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English",  callback_data="lang_en"),
         InlineKeyboardButton("🇮🇳 हिंदी",    callback_data="lang_hi"),
         InlineKeyboardButton("🇧🇩 বাংলা",   callback_data="lang_bn")],
    ])

def diff_kb(exam: str):
    t = EXAM_THEME.get(exam, {"color":"🟦"})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Easy",     callback_data=f"diff_{exam}_Easy"),
         InlineKeyboardButton("🟡 Medium",   callback_data=f"diff_{exam}_Medium")],
        [InlineKeyboardButton("🔴 Hard",     callback_data=f"diff_{exam}_Hard"),
         InlineKeyboardButton("💀 Extreme",  callback_data=f"diff_{exam}_Extreme")],
        [InlineKeyboardButton("🏆 Full Mock Test", callback_data=f"diff_{exam}_Medium_full")],
    ])

def main_kb(exam: str):
    t = EXAM_THEME.get(exam, {"emoji":"📋","icon":"⚡"})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📝 Full Mock Test",    callback_data=f"m_full_{exam}"),
         InlineKeyboardButton(f"⚡ Quick 10Q",         callback_data=f"m_quick_{exam}")],
        [InlineKeyboardButton(f"📚 Subject Practice",  callback_data=f"m_subj_{exam}"),
         InlineKeyboardButton(f"🗂 Topic Practice",    callback_data=f"m_topic_{exam}")],
        [InlineKeyboardButton(f"💀 Extreme Test",      callback_data=f"m_extreme_{exam}"),
         InlineKeyboardButton(f"📊 My Progress",       callback_data="m_prog")],
        [InlineKeyboardButton(f"🏆 Leaderboard",       callback_data=f"m_lead_{exam}"),
         InlineKeyboardButton(f"🌐 Language",          callback_data="m_lang")],
    ])

def subject_kb(exam: str):
    subjects = EXAMS.get(exam, [])
    em_map = {"Quant":"📐","English":"📝","Reasoning":"🧩","GK":"🌍",
              "Physics":"⚛️","Chemistry":"🧪","Maths":"📊",
              "History":"🏺","Polity":"⚖️","Geography":"🗺",
              "Economy":"💰","Science":"🔬","Current Affairs":"📰",
              "General Science":"🌿"}
    rows = []
    for i in range(0, len(subjects), 2):
        row = []
        for s in subjects[i:i+2]:
            em = em_map.get(s,"📚")
            row.append(InlineKeyboardButton(
                f"{em} {s}", callback_data=f"subj_{exam}_{s}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Back", callback_data=f"exam_{exam}")])
    return InlineKeyboardMarkup(rows)


def topic_kb(exam: str, subject: str):
    from modules.question_gen import SECTION_MAP
    topics = SECTION_MAP.get(subject, [])
    rows = []
    for i in range(0, len(topics), 2):
        row = []
        for t in topics[i:i+2]:
            row.append(InlineKeyboardButton(t[:25], callback_data=f"topic_{exam}_{subject}_{t}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Back", callback_data=f"m_subj_{exam}")])
    return InlineKeyboardMarkup(rows)


# ═══════════════ HELPERS ══════════════════════════════════════
async def _user(msg: Message):
    u = msg.from_user
    return await get_or_create_user(u.id, u.first_name, u.username or "")

async def _lang(uid: int) -> str:
    return await get_user_lang(uid)

async def _force_clear(uid: int):
    """Nuke all session data for user"""
    await clear_session(uid)


# ═══════════════ START ════════════════════════════════════════
@app.on_message(filters.command("start"))
async def cmd_start(_, msg: Message):
    u    = await _user(msg)
    name = msg.from_user.first_name

    caption = (
        f"╔══════════════════════════╗\n"
        f"║  🎓 **SERENA STUDY BOT**     ║\n"
        f"║  _Your Exam Companion_    ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👋 **Welcome, {name}!**\n"
        f"📅 _2025-26 Updated | Latest PYQ_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 **SSC** — CGL · CHSL · MTS · GD\n"
        f"🏛 **UPSC** — CSE · NDA · CDS · CAPF\n"
        f"⚗️ **JEE** — Mains · Advanced\n"
        f"🚂 **RAILWAY** — NTPC · Group D · ALP\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ **Features:**\n"
        f"📅 Real PYQ with Exam Tag + Year\n"
        f"💀 Extreme Difficulty Mode\n"
        f"🗂 Topic-wise Targeted Practice\n"
        f"✏️ AI Doubt → Rough Copy Style\n"
        f"📊 Testbook-style Analysis\n\n"
        f"👇 **Choose your exam:**"
    )

    # Try to send with image
    img_url = await get_image("START")
    try:
        if img_url:
            await msg.reply_photo(img_url, caption=caption, reply_markup=start_kb())
        else:
            await msg.reply(caption, reply_markup=start_kb())
    except Exception:
        await msg.reply(caption, reply_markup=start_kb())


@app.on_message(filters.command("help"))
async def cmd_help(_, msg: Message):
    await _user(msg)
    name = msg.from_user.first_name
    await msg.reply(
        f"📚 **{name} — All Commands**\n\n"
        "**🎯 TESTS**\n"
        "`/test SSC` — Choose difficulty & start\n"
        "`/quick SSC 10` — Quick 10Q test\n"
        "`/practice SSC Quant` — Subject practice\n"
        "`/topic SSC Quant Percentage` — Topic practice\n"
        "`/extreme SSC` — 💀 Extreme difficulty\n"
        "`/stoptest` — Force stop test\n\n"
        "**🤔 DOUBT SOLVER**\n"
        "`/ask <question>` — AI solves (rough copy style!)\n"
        "_(Seedha question type karo bhi chalega)_\n\n"
        "**📊 STATS**\n"
        "`/myprogress` — Full report\n"
        "`/leaderboard SSC` — Top scorers\n\n"
        "**⚙️ SETTINGS**\n"
        "`/setexam SSC UPSC` — Set exams\n"
        "`/language` — Change language\n"
    )


# ═══════════════ LANGUAGE ═════════════════════════════════════
@app.on_message(filters.command("language"))
async def cmd_language(_, msg: Message):
    await _user(msg)
    await msg.reply("🌐 **Choose your language:**", reply_markup=lang_kb())

@app.on_callback_query(filters.regex(r"^lang_(\w+)$"))
async def cb_lang(_, cq: CallbackQuery):
    lang = cq.matches[0].group(1)
    await update_user(cq.from_user.id, {"lang": lang})
    names = {"en":"🇬🇧 English","hi":"🇮🇳 हिंदी","bn":"🇧🇩 বাংলা"}
    await cq.message.edit_text(f"✅ Language: **{names.get(lang,lang)}**!\n\n/start to go home.")

@app.on_callback_query(filters.regex(r"^m_lang$"))
async def cb_menu_lang(_, cq: CallbackQuery):
    await cq.answer()
    await cq.message.reply("🌐 **Choose language:**", reply_markup=lang_kb())


# ═══════════════ EXAM SELECTION ═══════════════════════════════
@app.on_callback_query(filters.regex(r"^exam_(.+)$"))
async def cb_exam(_, cq: CallbackQuery):
    exam = cq.matches[0].group(1)
    uid  = cq.from_user.id
    name = cq.from_user.first_name
    t    = EXAM_THEME.get(exam, {"emoji":"📋","color":"🟦","icon":"⚡"})
    await update_user(uid, {"exams": [exam]})
    await cq.message.edit_text(
        f"{t['color']} **{t['emoji']} {exam} — Ready, {name}!**\n\n"
        f"What do you want to do? 👇",
        reply_markup=main_kb(exam)
    )


# ═══════════════ MENU CALLBACKS ═══════════════════════════════
@app.on_callback_query(filters.regex(r"^m_(.+)$"))
async def cb_menu(_, cq: CallbackQuery):
    data = cq.matches[0].group(1)
    uid  = cq.from_user.id
    lang = await _lang(uid)
    await cq.answer()

    if data == "prog":
        rpt = await get_progress_report(uid, lang)
        await cq.message.reply(rpt)
        return
    if data == "lang":
        await cq.message.reply("🌐 Choose language:", reply_markup=lang_kb())
        return

    parts = data.split("_", 1)
    if len(parts) < 2:
        return
    action, exam = parts[0], parts[1]

    if action == "full":
        await cq.message.reply(
            f"📊 **{exam} — Choose Difficulty:**\n"
            f"💡 _Extreme = Top 1% level questions_",
            reply_markup=diff_kb(exam)
        )
    elif action == "quick":
        u    = await get_user(uid)
        diff = u.get("preferred_difficulty","Medium") if u else "Medium"
        await _force_clear(uid)
        await start_mock_test(app, cq.message, exam, custom_count=10,
                               difficulty=diff, lang=lang)
    elif action == "subj":
        await cq.message.reply(
            f"📚 **{exam} — Subject Choose Karo:**",
            reply_markup=subject_kb(exam)
        )
    elif action == "topic":
        # Show subject list first, then topics
        await cq.message.reply(
            f"🗂 **{exam} — Topic Practice:**\nFirst choose subject 👇",
            reply_markup=subject_kb(exam)
        )
    elif action == "extreme":
        await _force_clear(uid)
        await cq.message.reply(
            f"💀 **{exam} EXTREME MODE**\n"
            f"_Only top 1% can crack these!_"
        )
        await start_mock_test(app, cq.message, exam, custom_count=10,
                               difficulty="Extreme", lang=lang)
    elif action == "lead":
        board = await get_leaderboard_text(exam)
        await cq.message.reply(board)


@app.on_callback_query(filters.regex(r"^diff_(\w+)_(\w+)(_full)?$"))
async def cb_diff(_, cq: CallbackQuery):
    exam   = cq.matches[0].group(1)
    diff   = cq.matches[0].group(2)
    full   = bool(cq.matches[0].group(3))
    uid    = cq.from_user.id
    lang   = await _lang(uid)
    await update_user(uid, {"preferred_difficulty": diff})
    await cq.answer()
    await _force_clear(uid)
    preset = {"SSC":"SSC_FULL","UPSC":"UPSC_FULL",
              "JEE":"JEE_FULL","RAILWAY":"RAILWAY_FULL"}.get(exam,"SSC_FULL")
    count  = None if full else 15
    await start_mock_test(app, cq.message, exam,
                          preset_key=preset if full else None,
                          custom_count=count or 15,
                          difficulty=diff, lang=lang)


@app.on_callback_query(filters.regex(r"^subj_(\w+)_(.+)$"))
async def cb_subj(_, cq: CallbackQuery):
    exam    = cq.matches[0].group(1)
    subject = cq.matches[0].group(2)
    uid     = cq.from_user.id
    lang    = await _lang(uid)
    await cq.answer()
    # Show topic options
    await cq.message.reply(
        f"🗂 **{exam} › {subject}**\n\nChoose a topic for focused practice:",
        reply_markup=topic_kb(exam, subject)
    )


@app.on_callback_query(filters.regex(r"^topic_(\w+)_(.+?)_(.+)$"))
async def cb_topic(_, cq: CallbackQuery):
    exam    = cq.matches[0].group(1)
    subject = cq.matches[0].group(2)
    topic   = cq.matches[0].group(3)
    uid     = cq.from_user.id
    lang    = await _lang(uid)
    u       = await get_user(uid)
    diff    = u.get("preferred_difficulty","Medium") if u else "Medium"
    await cq.answer()
    await _force_clear(uid)
    await cq.message.reply(
        f"🎯 Starting **{exam} › {subject} › {topic}**\n"
        f"Difficulty: **{diff}** | 10 Questions"
    )
    await start_mock_test(app, cq.message, exam, subject=subject,
                          section=topic, custom_count=10,
                          difficulty=diff, lang=lang)


# ═══════════════ TEST COMMANDS ════════════════════════════════
@app.on_message(filters.command("test"))
async def cmd_test(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = msg.command[1:]
    if not args:
        await msg.reply("📋 Choose your exam:", reply_markup=start_kb())
        return
    exam = args[0].upper()
    if exam not in EXAMS:
        await msg.reply(f"❌ Invalid. Choose: {', '.join(EXAMS.keys())}")
        return
    await msg.reply(f"📊 **{exam}** — Choose Difficulty:", reply_markup=diff_kb(exam))


@app.on_message(filters.command("quick"))
async def cmd_quick(_, msg: Message):
    u     = await _user(msg)
    lang  = u.get("lang","en")
    args  = msg.command[1:]
    exam  = args[0].upper() if args else "SSC"
    count = int(args[1]) if len(args)>1 and args[1].isdigit() else 10
    count = min(count, 30)
    if exam not in EXAMS: exam = "SSC"
    diff  = u.get("preferred_difficulty","Medium")
    await _force_clear(msg.from_user.id)
    await start_mock_test(app, msg, exam, custom_count=count, difficulty=diff, lang=lang)


@app.on_message(filters.command("practice"))
async def cmd_practice(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = msg.command[1:]
    if len(args) < 2:
        await msg.reply(
            "Usage: `/practice EXAM SUBJECT`\n\n"
            "Examples:\n`/practice SSC Quant`\n`/practice JEE Physics`"
        )
        return
    exam    = args[0].upper()
    subject = args[1].title()
    if exam not in EXAMS:
        await msg.reply(f"❌ Invalid: {exam}")
        return
    diff = u.get("preferred_difficulty","Medium")
    await _force_clear(msg.from_user.id)
    await start_mock_test(app, msg, exam, subject=subject,
                          custom_count=20, difficulty=diff, lang=lang)


@app.on_message(filters.command("topic"))
async def cmd_topic(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = msg.command[1:]
    if len(args) < 3:
        await msg.reply(
            "Usage: `/topic EXAM SUBJECT TOPIC`\n\n"
            "Examples:\n"
            "`/topic SSC Quant Percentage`\n"
            "`/topic JEE Physics Mechanics`\n"
            "`/topic UPSC Polity Parliament`"
        )
        return
    exam    = args[0].upper()
    subject = args[1].title()
    topic   = " ".join(args[2:]).title()
    diff    = u.get("preferred_difficulty","Medium")
    await _force_clear(msg.from_user.id)
    await msg.reply(f"🎯 Starting **{exam} › {subject} › {topic}** (10Q)")
    await start_mock_test(app, msg, exam, subject=subject,
                          section=topic, custom_count=10,
                          difficulty=diff, lang=lang)


@app.on_message(filters.command("extreme"))
async def cmd_extreme(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = msg.command[1:]
    exam = args[0].upper() if args else "SSC"
    if exam not in EXAMS: exam = "SSC"
    await _force_clear(msg.from_user.id)
    await msg.reply(
        f"💀 **{exam} EXTREME MODE**\n"
        f"_Top 1% level — Are you ready?_ 🔥"
    )
    await start_mock_test(app, msg, exam, custom_count=10,
                          difficulty="Extreme", lang=lang)


@app.on_message(filters.command("stoptest"))
async def cmd_stoptest(_, msg: Message):
    uid  = msg.from_user.id
    name = msg.from_user.first_name
    await _force_clear(uid)
    await msg.reply(
        f"🛑 **{name}, all sessions cleared!**\n\n"
        f"✅ Start fresh: /test SSC"
    )


# ═══════════════ ANSWER BUTTONS ═══════════════════════════════
@app.on_callback_query(filters.regex(r"^tans_(\d+)_(\d+)_([ABCD]|SKIP)$"))
async def cb_answer(_, cq: CallbackQuery):
    uid   = cq.from_user.id
    q_idx = int(cq.matches[0].group(2))
    ans   = cq.matches[0].group(3)
    await cq.answer()
    try:
        await cq.message.delete()
    except Exception:
        pass
    await process_button_answer(app, uid, cq.message.chat.id, q_idx, ans)


# ═══════════════ DOUBT SOLVER ═════════════════════════════════
@app.on_message(filters.command("ask"))
async def cmd_ask(_, msg: Message):
    u     = await _user(msg)
    doubt = " ".join(msg.command[1:]).strip()
    if not doubt:
        await msg.reply(
            "🤔 **How to ask doubt:**\n\n"
            "`/ask A train covers 360km in 4hrs, find speed`\n"
            "`/ask What is Article 370?`\n\n"
            "Ya seedha type karo — auto detect!"
        )
        return
    await _solve(msg, u, doubt)


async def _solve(msg: Message, user: dict, doubt: str):
    uid  = user["uid"]
    lang = user.get("lang","en")
    exam = (user.get("exams") or ["SSC"])[0]
    name = user["name"]
    ok, remaining = await check_doubt_limit(uid, MAX_DAILY_DOUBTS)
    if not ok:
        await msg.reply(f"⚠️ Daily limit reached ({MAX_DAILY_DOUBTS}/day). Come back tomorrow!")
        return
    m = await msg.reply("✏️ _Solving on rough copy..._")
    try:
        answer = await solve_doubt(doubt, exam, name, lang)
        await m.edit(answer + f"\n\n_{remaining} doubts left today_")
    except Exception as e:
        await m.edit(f"❌ Error: {str(e)[:100]}")


# ═══════════════ PROGRESS + LEADERBOARD ═══════════════════════
@app.on_message(filters.command("myprogress"))
async def cmd_progress(_, msg: Message):
    u = await _user(msg)
    rpt = await get_progress_report(msg.from_user.id, u.get("lang","en"))
    await msg.reply(rpt)

@app.on_message(filters.command("leaderboard"))
async def cmd_leaderboard(_, msg: Message):
    await _user(msg)
    args = msg.command[1:]
    exam = args[0].upper() if args else "SSC"
    if exam not in EXAMS: exam = "SSC"
    await msg.reply(await get_leaderboard_text(exam))

@app.on_message(filters.command("setexam"))
async def cmd_setexam(_, msg: Message):
    u    = await _user(msg)
    args = [a.upper() for a in msg.command[1:] if a.upper() in EXAMS]
    if not args:
        await msg.reply(f"Usage: `/setexam SSC UPSC`\nAvailable: {', '.join(EXAMS.keys())}")
        return
    await update_user(msg.from_user.id, {"exams": args})
    await msg.reply(f"✅ Exams set: **{', '.join(args)}**!")


# ═══════════════ OWNER COMMANDS ═══════════════════════════════
@app.on_message(filters.command("upload") & owner_filter)
async def cmd_upload(_, msg: Message):
    args = msg.command[1:]
    if len(args) < 2:
        await msg.reply(
            "📤 **Upload PYQ Sheet**\n\n"
            "Usage: `/upload EXAM SUBJECT [YEAR] [SOURCE]`\n\n"
            "Examples:\n"
            "`/upload SSC Quant 2024 SSC CGL 2024 Tier-I`\n"
            "`/upload UPSC Polity 2025 UPSC CSE 2025`\n"
            "`/upload RAILWAY GK 2025 RRB NTPC 2025`\n\n"
            "Then send PDF / Image / TXT!"
        )
        return
    exam    = args[0].upper()
    subject = args[1].title()
    year    = args[2] if len(args)>2 and args[2].isdigit() else "2025"
    source  = " ".join(args[3:] if len(args)>3 else args[2:]) or f"{exam} {subject} {year}"
    if exam not in EXAMS:
        await msg.reply(f"❌ Invalid exam. Use: {', '.join(EXAMS.keys())}")
        return
    _upload_ctx[msg.from_user.id] = {
        "exam": exam, "subject": subject,
        "source": source, "exam_year": year
    }
    await msg.reply(
        f"✅ **Upload Context:**\n"
        f"📋 {exam} | 📚 {subject}\n"
        f"📅 Year: {year} | 📂 {source}\n\n"
        f"Now send file! (PDF/Image/TXT)"
    )

@app.on_message(owner_filter & (filters.document | filters.photo))
async def owner_file(_, msg: Message):
    uid = msg.from_user.id
    if uid not in _upload_ctx: return
    ctx = _upload_ctx[uid]
    m   = await msg.reply(f"📥 Processing **{ctx['exam']} — {ctx['subject']}**...")
    try:
        file_bytes = bytes((await msg.download(in_memory=True)).getbuffer())
        if msg.photo: ftype = "image"
        elif msg.document:
            fname = msg.document.file_name or ""
            if   fname.lower().endswith(".pdf"): ftype = "pdf"
            elif fname.lower().endswith(".txt"): ftype = "txt"
            else:
                await m.edit("❌ Only PDF / TXT / Image supported.")
                return
        questions = await process_owner_upload(
            file_bytes, ftype, ctx["exam"], ctx["subject"],
            ctx["source"], ctx.get("exam_year"), "en"
        )
        if not questions:
            await m.edit("❌ No questions extracted. Use text-based PDF or clearer image.")
            return
        saved = await add_questions_bulk(questions)
        total = await count_questions(ctx["exam"], ctx["subject"])
        _upload_ctx.pop(uid, None)
        await m.edit(
            f"✅ **Uploaded!**\n"
            f"❓ Added: **{saved}** | Total: **{total}**"
        )
    except Exception as e:
        await m.edit(f"❌ Error: {str(e)[:200]}")

@app.on_message(filters.command("dbstats") & owner_filter)
async def cmd_dbstats(_, msg: Message):
    stats = await get_db_stats()
    text  = "📊 **Question Bank 2025-26**\n\n"
    total = 0
    for exam, s in stats.items():
        t = EXAM_THEME.get(exam, {"emoji":"📋"})
        text  += f"{t['emoji']} **{exam}**: {s['total']} ({s['pyq']} PYQ)\n"
        total += s['total']
    text += f"\n**TOTAL: {total}**"
    await msg.reply(text)


@app.on_message(filters.command("setimage") & owner_filter)
async def cmd_setimage(_, msg: Message):
    """
    Set image for start/exam screens.
    Usage: /setimage START <url>
    Or reply to a photo: /setimage SSC
    Keys: START, SSC, UPSC, JEE, RAILWAY
    """
    args = msg.command[1:]
    valid_keys = ["START","SSC","UPSC","JEE","RAILWAY"]

    # Reply to photo mode
    if msg.reply_to_message and msg.reply_to_message.photo:
        if not args:
            await msg.reply(
                "Usage: Reply to image + /setimage KEY\n"
                f"Keys: {', '.join(valid_keys)}"
            )
            return
        key = args[0].upper()
        if key not in valid_keys:
            await msg.reply(f"❌ Invalid key. Use: {', '.join(valid_keys)}")
            return
        # Download and get file_id
        photo = msg.reply_to_message.photo
        await set_image(key, photo.file_id)
        await msg.reply(f"✅ **{key}** image set via file_id!")
        return

    # URL mode
    if len(args) < 2:
        keys_str = ', '.join(valid_keys)
        await msg.reply(
            f"📸 **Set Bot Images**\n\n"
            f"**Method 1 — URL:**\n"
            f"`/setimage START https://i.imgur.com/xyz.jpg`\n"
            f"`/setimage SSC https://i.imgur.com/abc.jpg`\n\n"
            f"**Method 2 — Photo Reply:**\n"
            f"Reply to any photo with `/setimage SSC`\n\n"
            f"**Keys:** {keys_str}\n\n"
            f"**View current:** /images"
        )
        return

    key = args[0].upper()
    url = args[1]
    if key not in valid_keys:
        await msg.reply(f"❌ Invalid key. Use: {', '.join(valid_keys)}")
        return
    await set_image(key, url)
    await msg.reply(f"✅ **{key}** image set!\n\n`{url[:60]}`")


@app.on_message(filters.command("images") & owner_filter)
async def cmd_images(_, msg: Message):
    imgs = await get_all_images()
    if not imgs:
        await msg.reply("No images set yet.\nUse: /setimage START url")
        return
    out = ["**Bot Images:**"]
    for key, url in imgs.items():
        short = str(url)[:50]
        out.append(f"**{key}:** `{short}`")
    out.append("\nUpdate: /setimage KEY url")
    await msg.reply("\n".join(out))

@app.on_message(filters.command("delimage") & owner_filter)
async def cmd_delimage(_, msg: Message):
    args = msg.command[1:]
    if not args:
        await msg.reply("Usage: `/delimage SSC`")
        return
    from database import images_col
    key = args[0].upper()
    await images_col.delete_one({"key": key})
    await msg.reply(f"✅ **{key}** image removed!")

@app.on_message(filters.command("broadcast") & owner_filter)
async def cmd_broadcast(_, msg: Message):
    text = " ".join(msg.command[1:]).strip()
    if not text:
        await msg.reply("Usage: `/broadcast message`")
        return
    users = await get_all_users()
    sent  = 0
    for u in users:
        try:
            await app.send_message(u["uid"], f"📢 **Announcement:**\n\n{text}")
            sent += 1
        except Exception:
            pass
    await msg.reply(f"✅ Sent to {sent} users.")


# ═══════════════ SMART TEXT ═══════════════════════════════════
DOUBT_KW = [
    "kya hai","what is","how to","kaise","explain","kyun","why",
    "difference","define","formula","trick","shortcut","solve",
    "calculate","find","mean","called","batao","samjhao",
    "क्या है","कैसे","क्यों","?","find","evaluate"
]

SKIP_CMDS = [
    "start","help","test","quick","practice","topic","extreme","ask",
    "stoptest","myprogress","leaderboard","setexam","language",
    "upload","dbstats","broadcast","setimage","images","delimage"
]

@app.on_message(filters.text & filters.private & ~filters.command(SKIP_CMDS))
async def smart_text(_, msg: Message):
    u    = await _user(msg)
    text = msg.text.strip()
    if await get_session(msg.from_user.id):
        return
    is_doubt = any(kw in text.lower() for kw in DOUBT_KW) or "?" in text
    if is_doubt:
        await _solve(msg, u, text)
    else:
        await msg.reply(
            "🤔 **What do you need?**\n\n"
            "• Test: `/test SSC`\n"
            "• Quick: `/quick SSC 10`\n"
            "• Topic: `/topic SSC Quant Percentage`\n"
            "• Extreme: `/extreme JEE`\n"
            "• Doubt: `/ask your question`\n"
            "• Help: /help"
        )
