import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
try:
    from pyrogram.types import PollAnswer
except ImportError:
    PollAnswer = None  # Older pyrogram — handler still works
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_IDS, EXAMS, MAX_DAILY_DOUBTS, LANGUAGES
from database import (
    get_or_create_user, get_test_session, clear_test_session,
    add_questions_bulk, count_questions, update_user, get_user,
    get_user_lang, get_db_stats, check_doubt_limit, get_all_users
)
from modules.mock_test    import start_mock_test, process_poll_answer, process_button_answer, TEST_PRESETS
from modules.doubt_solver import solve_doubt
from modules.tracker      import get_progress_report, get_leaderboard_text
from modules.parser       import process_owner_upload

app = Client("serena_studybot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Owner upload context: {uid: {exam, subject, source, exam_year, lang}}
_upload_ctx: dict = {}

owner_filter = filters.user(OWNER_IDS)


# ═══════════════════ KEYBOARDS ════════════════════════════════
def exam_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 SSC",     callback_data="exam_SSC"),
         InlineKeyboardButton("🏛 UPSC",    callback_data="exam_UPSC")],
        [InlineKeyboardButton("⚗️ JEE",     callback_data="exam_JEE"),
         InlineKeyboardButton("🚂 RAILWAY", callback_data="exam_RAILWAY")],
    ])


def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English",  callback_data="lang_en"),
         InlineKeyboardButton("🇮🇳 हिंदी",    callback_data="lang_hi"),
         InlineKeyboardButton("🇧🇩 বাংলা",   callback_data="lang_bn")],
    ])


def diff_kb(exam: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Easy",    callback_data=f"diff_{exam}_Easy"),
         InlineKeyboardButton("🟡 Medium",  callback_data=f"diff_{exam}_Medium"),
         InlineKeyboardButton("🔴 Hard",    callback_data=f"diff_{exam}_Hard"),
         InlineKeyboardButton("🏆 PYQ Mix", callback_data=f"diff_{exam}_Medium_pyq")],
    ])


def main_kb(exam: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Full Mock Test",   callback_data=f"m_full_{exam}"),
         InlineKeyboardButton("⚡ Quick 10Q",        callback_data=f"m_quick_{exam}")],
        [InlineKeyboardButton("📚 Subject Practice", callback_data=f"m_subj_{exam}"),
         InlineKeyboardButton("📊 My Progress",      callback_data="m_prog")],
        [InlineKeyboardButton("🏆 Leaderboard",      callback_data=f"m_lead_{exam}"),
         InlineKeyboardButton("🌐 Language",         callback_data="m_lang")],
    ])


# ═══════════════════ HELPERS ══════════════════════════════════
async def _user(msg: Message):
    u = msg.from_user
    return await get_or_create_user(u.id, u.first_name, u.username or "")


async def _lang(uid: int) -> str:
    return await get_user_lang(uid)


# ═══════════════════ START ════════════════════════════════════
@app.on_message(filters.command("start"))
async def cmd_start(_, msg: Message):
    u    = await _user(msg)
    name = msg.from_user.first_name
    lang = u.get("lang","en")
    greetings = {
        "en": f"🎓 **Welcome, {name}!**\nYour personal exam coach for SSC | UPSC | JEE | RAILWAY\n\nChoose your exam 👇",
        "hi": f"🎓 **स्वागत है, {name}!**\nSSC | UPSC | JEE | RAILWAY के लिए आपका कोच\n\nपरीक्षा चुनें 👇",
        "bn": f"🎓 **স্বাগতম, {name}!**\nSSC | UPSC | JEE | RAILWAY-এর জন্য আপনার কোচ\n\nপরীক্ষা বেছে নিন 👇",
    }
    await msg.reply(greetings.get(lang, greetings["en"]), reply_markup=exam_kb())


@app.on_message(filters.command("help"))
async def cmd_help(_, msg: Message):
    await _user(msg)
    name = msg.from_user.first_name
    await msg.reply(
        f"📚 **{name} — Commands:**\n\n"
        "**🎯 TESTS**\n"
        "`/test SSC` — Full SSC Mock (100Q)\n"
        "`/test UPSC` — Full UPSC Prelims (100Q)\n"
        "`/test JEE` — Full JEE Mains (90Q)\n"
        "`/test RAILWAY` — Full Railway Test (100Q)\n"
        "`/quick SSC 10` — Quick 10 questions\n"
        "`/stoptest` — End current test\n\n"
        "**📚 PRACTICE**\n"
        "`/practice SSC Quant` — Subject practice\n"
        "`/practice JEE Physics Mechanics` — Section\n\n"
        "**🤔 DOUBTS**\n"
        "`/ask <your question>` — AI doubt solver\n"
        "_(Seedha question type karo bhi chalega!)_\n\n"
        "**📊 STATS**\n"
        "`/myprogress` — Your full report\n"
        "`/leaderboard SSC` — Top scorers\n\n"
        "**⚙️ SETTINGS**\n"
        "`/setexam SSC UPSC` — Set your exams\n"
        "`/language` — Change language\n"
    )


# ═══════════════════ LANGUAGE ══════════════════════════════
@app.on_message(filters.command("language"))
async def cmd_language(_, msg: Message):
    await _user(msg)
    await msg.reply("🌐 **Choose your language:**", reply_markup=lang_kb())


@app.on_callback_query(filters.regex(r"^lang_(\w+)$"))
async def cb_lang(_, cq: CallbackQuery):
    lang = cq.matches[0].group(1)
    uid  = cq.from_user.id
    await update_user(uid, {"lang": lang})
    names = {"en":"🇬🇧 English","hi":"🇮🇳 हिंदी","bn":"🇧🇩 বাংলা"}
    await cq.message.edit_text(
        f"✅ Language set to **{names.get(lang,lang)}**!\n\nUse /start to begin.",
        reply_markup=None
    )


@app.on_callback_query(filters.regex(r"^m_lang$"))
async def cb_menu_lang(_, cq: CallbackQuery):
    await cq.answer()
    await cq.message.reply("🌐 **Choose language:**", reply_markup=lang_kb())


# ═══════════════════ EXAM SELECTION ═══════════════════════════
@app.on_callback_query(filters.regex(r"^exam_(.+)$"))
async def cb_exam(_, cq: CallbackQuery):
    exam = cq.matches[0].group(1)
    uid  = cq.from_user.id
    name = cq.from_user.first_name
    lang = await _lang(uid)
    await update_user(uid, {"exams": [exam]})
    labels = {
        "en": f"✅ **{name}, exam set: {exam}!**\n\nWhat do you want to do? 👇",
        "hi": f"✅ **{name}, परीक्षा सेट: {exam}!**\n\nक्या करना है? 👇",
        "bn": f"✅ **{name}, পরীক্ষা সেট: {exam}!**\n\nকি করতে চান? 👇",
    }
    await cq.message.edit_text(labels.get(lang, labels["en"]),
                                reply_markup=main_kb(exam))


# ═══════════════════ MENU CALLBACKS ═══════════════════════════
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
        preset = {"SSC":"SSC_FULL","UPSC":"UPSC_FULL","JEE":"JEE_FULL","RAILWAY":"RAILWAY_FULL"}.get(exam,"SSC_FULL")
        await cq.message.reply(f"📊 Difficulty choose karo for **{exam}**:", reply_markup=diff_kb(exam))

    elif action == "quick":
        user = await get_user(uid)
        diff = user.get("preferred_difficulty","Medium") if user else "Medium"
        await start_mock_test(app, cq.message, exam, custom_count=10,
                               difficulty=diff, lang=lang)

    elif action == "subj":
        subjects = EXAMS.get(exam, [])
        btns = [[InlineKeyboardButton(s, callback_data=f"subj_{exam}_{s}")] for s in subjects]
        await cq.message.reply(f"📚 **{exam} — Subject choose karo:**",
                                reply_markup=InlineKeyboardMarkup(btns))

    elif action == "lead":
        board = await get_leaderboard_text(exam)
        await cq.message.reply(board)


@app.on_callback_query(filters.regex(r"^diff_(.+)_(\w+?)(_pyq)?$"))
async def cb_diff(_, cq: CallbackQuery):
    exam   = cq.matches[0].group(1)
    diff   = cq.matches[0].group(2)
    pyq    = bool(cq.matches[0].group(3))
    uid    = cq.from_user.id
    lang   = await _lang(uid)
    await update_user(uid, {"preferred_difficulty": diff})
    await cq.answer()
    preset = {"SSC":"SSC_FULL","UPSC":"UPSC_FULL","JEE":"JEE_FULL","RAILWAY":"RAILWAY_FULL"}.get(exam,"SSC_FULL")
    await start_mock_test(app, cq.message, exam, preset_key=preset,
                           difficulty=diff, prefer_pyq=pyq, lang=lang)


@app.on_callback_query(filters.regex(r"^subj_(.+)_(.+)$"))
async def cb_subj(_, cq: CallbackQuery):
    exam    = cq.matches[0].group(1)
    subject = cq.matches[0].group(2)
    uid     = cq.from_user.id
    lang    = await _lang(uid)
    await cq.answer()
    user = await get_user(uid)
    diff = user.get("preferred_difficulty","Medium") if user else "Medium"
    await start_mock_test(app, cq.message, exam, subject=subject,
                           custom_count=20, difficulty=diff, lang=lang)


# ═══════════════════ TEST COMMANDS ════════════════════════════
@app.on_message(filters.command("test"))
async def cmd_test(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    name = msg.from_user.first_name
    args = msg.command[1:]
    if not args:
        await msg.reply(f"📋 **{name}, choose exam:**", reply_markup=exam_kb())
        return
    exam = args[0].upper()
    if exam not in EXAMS:
        await msg.reply(f"❌ Invalid. Choose: {', '.join(EXAMS.keys())}")
        return
    await msg.reply(f"📊 Difficulty for **{exam}**:", reply_markup=diff_kb(exam))


@app.on_message(filters.command("quick"))
async def cmd_quick(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = msg.command[1:]
    exam  = args[0].upper() if args else "SSC"
    count = int(args[1]) if len(args)>1 and args[1].isdigit() else 10
    count = min(count, 30)
    if exam not in EXAMS: exam = "SSC"
    diff = u.get("preferred_difficulty","Medium")
    await start_mock_test(app, msg, exam, custom_count=count, difficulty=diff, lang=lang)


@app.on_message(filters.command("practice"))
async def cmd_practice(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = msg.command[1:]
    name = msg.from_user.first_name
    if len(args) < 2:
        await msg.reply(
            f"Usage: `/practice EXAM SUBJECT [SECTION]`\n\n"
            "Examples:\n"
            "`/practice SSC Quant`\n"
            "`/practice SSC Quant Percentage`\n"
            "`/practice JEE Physics Mechanics`\n"
            "`/practice UPSC Polity Parliament`"
        )
        return
    exam    = args[0].upper()
    subject = args[1].title()
    section = " ".join(args[2:]).title() if len(args)>2 else None
    if exam not in EXAMS:
        await msg.reply(f"❌ Invalid exam: {exam}")
        return
    diff = u.get("preferred_difficulty","Medium")
    label = f"{exam} — {subject}" + (f" › {section}" if section else "")
    await msg.reply(f"📚 Starting **{label}** for {name}...")
    await start_mock_test(app, msg, exam, subject=subject, section=section,
                           custom_count=20, difficulty=diff, lang=lang)


@app.on_message(filters.command("stoptest"))
async def cmd_stoptest(_, msg: Message):
    uid  = msg.from_user.id
    lang = await _lang(uid)
    name = msg.from_user.first_name
    sess = await get_test_session(uid)
    if not sess:
        labels = {"en":f"❌ {name}, no active test.","hi":f"❌ {name}, कोई टेस्ट नहीं।","bn":f"❌ {name}, কোনো পরীক্ষা নেই।"}
        await msg.reply(labels.get(lang, labels["en"]))
        return
    await clear_test_session(uid)
    labels = {"en":f"🛑 **{name}, test stopped.**\nNew test: /test SSC",
              "hi":f"🛑 **{name}, टेस्ट बंद।**\nनया: /test SSC",
              "bn":f"🛑 **{name}, পরীক্ষা বন্ধ।**\nনতুন: /test SSC"}
    await msg.reply(labels.get(lang, labels["en"]))


# ═══════════════════ POLL + BUTTON ANSWERS ════════════════════
@app.on_poll_answer()
async def on_poll_answer(_, pa):
    await process_poll_answer(app, pa.user.id, pa.poll_id, pa.option_ids)


@app.on_callback_query(filters.regex(r"^ans_(\d+)_(\d+)_([ABCD])$"))
async def cb_answer(_, cq: CallbackQuery):
    uid   = int(cq.matches[0].group(1))
    q_idx = int(cq.matches[0].group(2))
    ans   = cq.matches[0].group(3)
    if uid != cq.from_user.id:
        await cq.answer("Not your question!", show_alert=True)
        return
    await cq.answer()
    await cq.message.delete()
    await process_button_answer(app, uid, cq.message.chat.id, q_idx, ans)


# ═══════════════════ DOUBT SOLVER ═════════════════════════════
@app.on_message(filters.command("ask"))
async def cmd_ask(_, msg: Message):
    u     = await _user(msg)
    doubt = " ".join(msg.command[1:]).strip()
    if not doubt:
        labels = {
            "en": "Usage: `/ask <your question>`\nExample: `/ask How to solve percentage questions fast?`",
            "hi": "उपयोग: `/ask <आपका प्रश्न>`\nउदाहरण: `/ask प्रतिशत कैसे हल करें?`",
            "bn": "ব্যবহার: `/ask <আপনার প্রশ্ন>`\nউদাহরণ: `/ask শতকরা কিভাবে সমাধান করব?`",
        }
        await msg.reply(labels.get(u.get("lang","en"), labels["en"]))
        return
    await _solve(msg, u, doubt)


async def _solve(msg: Message, user: dict, doubt: str):
    uid  = user["uid"]
    lang = user.get("lang","en")
    exam = (user.get("exams") or ["SSC"])[0]
    name = user["name"]
    ok, remaining = await check_doubt_limit(uid, MAX_DAILY_DOUBTS)
    if not ok:
        limit_msg = {
            "en": f"⚠️ Daily doubt limit reached ({MAX_DAILY_DOUBTS}/day). Come back tomorrow!",
            "hi": f"⚠️ आज की सीमा पूरी हो गई ({MAX_DAILY_DOUBTS}/दिन)। कल फिर आएं!",
            "bn": f"⚠️ আজকের সীমা শেষ ({MAX_DAILY_DOUBTS}/দিন)। কাল আবার আসুন!",
        }
        await msg.reply(limit_msg.get(lang, limit_msg["en"]))
        return
    m = await msg.reply("🧠 Solving...")
    try:
        answer = await solve_doubt(doubt, exam, name, lang)
        rem = f"\n\n_({remaining} doubts left today)_"
        await m.edit(answer + rem)
    except Exception as e:
        await m.edit(f"❌ Error: {str(e)[:100]}")


# ═══════════════════ PROGRESS + LEADERBOARD ═══════════════════
@app.on_message(filters.command("myprogress"))
async def cmd_progress(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    rpt  = await get_progress_report(msg.from_user.id, lang)
    await msg.reply(rpt)


@app.on_message(filters.command("leaderboard"))
async def cmd_leaderboard(_, msg: Message):
    await _user(msg)
    args = msg.command[1:]
    exam = args[0].upper() if args else "SSC"
    if exam not in EXAMS: exam = "SSC"
    board = await get_leaderboard_text(exam)
    await msg.reply(board)


@app.on_message(filters.command("setexam"))
async def cmd_setexam(_, msg: Message):
    u    = await _user(msg)
    lang = u.get("lang","en")
    args = [a.upper() for a in msg.command[1:] if a.upper() in EXAMS]
    if not args:
        await msg.reply(f"Usage: `/setexam SSC UPSC`\nAvailable: {', '.join(EXAMS.keys())}")
        return
    await update_user(msg.from_user.id, {"exams": args})
    await msg.reply(f"✅ Exams set: **{', '.join(args)}**!")


# ═══════════════════ OWNER: UPLOAD ════════════════════════════
@app.on_message(filters.command("upload") & owner_filter)
async def cmd_upload(_, msg: Message):
    """Owner sets upload context, then sends file"""
    args = msg.command[1:]
    if len(args) < 2:
        await msg.reply(
            "📤 **Upload PYQ Sheet**\n\n"
            "Usage: `/upload EXAM SUBJECT [YEAR] [SOURCE NAME]`\n\n"
            "Examples:\n"
            "`/upload SSC Quant 2023 SSC CGL 2023 Paper 1`\n"
            "`/upload UPSC Polity 2022 UPSC Prelims 2022`\n"
            "`/upload JEE Physics 2024 JEE Mains Jan 2024`\n"
            "`/upload RAILWAY GK 2024 RRB NTPC 2024`\n\n"
            "Phir PDF / Image / TXT bhejo!"
        )
        return
    exam    = args[0].upper()
    subject = args[1].title()
    year    = args[2] if len(args)>2 and args[2].isdigit() else None
    source  = " ".join(args[3:] if year else args[2:]) or f"{exam} {subject} Paper"
    if exam not in EXAMS:
        await msg.reply(f"❌ Invalid exam. Use: {', '.join(EXAMS.keys())}")
        return
    _upload_ctx[msg.from_user.id] = {
        "exam": exam, "subject": subject,
        "source": source, "exam_year": year, "lang": "en"
    }
    await msg.reply(
        f"✅ **Upload context set:**\n"
        f"📋 Exam: **{exam}**\n"
        f"📚 Subject: **{subject}**\n"
        f"📅 Year: **{year or 'Unknown'}**\n"
        f"📂 Source: **{source}**\n\n"
        f"Ab PDF / Image / TXT bhejo!"
    )


@app.on_message(owner_filter & (filters.document | filters.photo))
async def owner_file(_, msg: Message):
    uid = msg.from_user.id
    if uid not in _upload_ctx:
        return
    ctx = _upload_ctx[uid]
    m   = await msg.reply(f"📥 Processing **{ctx['exam']} — {ctx['subject']}**...")
    try:
        file_bytes = bytes((await msg.download(in_memory=True)).getbuffer())
        if msg.photo:
            ftype = "image"
        elif msg.document:
            fname = msg.document.file_name or ""
            if   fname.lower().endswith(".pdf"): ftype = "pdf"
            elif fname.lower().endswith(".txt"): ftype = "txt"
            else:
                await m.edit("❌ Only PDF / TXT / Image supported.")
                return

        questions = await process_owner_upload(
            file_bytes, ftype,
            ctx["exam"], ctx["subject"],
            ctx["source"], ctx.get("exam_year"), ctx.get("lang","en")
        )
        if not questions:
            await m.edit(
                "❌ No questions extracted.\n\n"
                "Tips:\n• Clearer image\n• Text-based PDF works best\n"
                "• Must be MCQ format with A/B/C/D options"
            )
            return

        saved = await add_questions_bulk(questions)
        _upload_ctx.pop(uid, None)
        total_now = await count_questions(ctx["exam"], ctx["subject"])
        pyq_count = await count_questions(ctx["exam"], ctx["subject"], is_pyq=True)

        await m.edit(
            f"✅ **Upload Successful!**\n\n"
            f"📋 Exam: **{ctx['exam']}**\n"
            f"📚 Subject: **{ctx['subject']}**\n"
            f"📅 Source: **{ctx['source']}**\n"
            f"❓ Questions Added: **{saved}**\n\n"
            f"📦 Total in DB: **{total_now}** (PYQ: **{pyq_count}**)"
        )
    except Exception as e:
        await m.edit(f"❌ Error: {str(e)[:200]}")


@app.on_message(filters.command("dbstats") & owner_filter)
async def cmd_dbstats(_, msg: Message):
    stats = await get_db_stats()
    text  = "📊 **Question Bank**\n\n"
    total_all = 0
    for exam, s in stats.items():
        text += f"**{exam}**: {s['total']} total ({s['pyq']} PYQ)\n"
        total_all += s['total']
    text += f"\n**TOTAL: {total_all}**"
    await msg.reply(text)


@app.on_message(filters.command("broadcast") & owner_filter)
async def cmd_broadcast(_, msg: Message):
    text = " ".join(msg.command[1:]).strip()
    if not text:
        await msg.reply("Usage: `/broadcast Your message`")
        return
    all_users = await get_all_users()
    sent = 0
    for u in all_users:
        try:
            await app.send_message(u["uid"], f"📢 **Announcement:**\n\n{text}")
            sent += 1
        except Exception:
            pass
    await msg.reply(f"✅ Sent to {sent} users.")


@app.on_message(filters.command("addowner") & owner_filter)
async def cmd_addowner(_, msg: Message):
    """Runtime owner add (doesn't persist restart — add to .env for permanent)"""
    args = msg.command[1:]
    if not args or not args[0].isdigit():
        await msg.reply("Usage: `/addowner <user_id>`")
        return
    new_id = int(args[0])
    if new_id not in OWNER_IDS:
        OWNER_IDS.append(new_id)
    await msg.reply(f"✅ Added owner: `{new_id}`\nCurrent owners: {OWNER_IDS}")


# ═══════════════════ SMART TEXT ═══════════════════════════════
DOUBT_KW = ["kya hai","what is","how to","kaise","explain","kyun","why",
            "difference","define","formula","trick","shortcut","solve",
            "calculate","find","mean","called","example","batao","samjhao",
            "क्या है","कैसे","समझाइए","क्यों","কি","কিভাবে","?"]


@app.on_message(
    filters.text & filters.private
    & ~filters.command(["start","help","test","quick","practice","ask","stoptest",
                        "myprogress","leaderboard","setexam","language","upload",
                        "dbstats","broadcast","addowner"])
)
async def smart_text(_, msg: Message):
    u    = await _user(msg)
    text = msg.text.strip()

    # In test? ignore
    if await get_test_session(msg.from_user.id):
        return

    is_doubt = any(kw in text.lower() for kw in DOUBT_KW) or "?" in text
    if is_doubt:
        await _solve(msg, u, text)
    else:
        lang = u.get("lang","en")
        hints = {
            "en": "🤔 What do you need?\n\n• Doubt? `/ask your question`\n• Test? `/test SSC`\n• Practice? `/practice SSC Quant`\n• Help? /help",
            "hi": "🤔 क्या चाहिए?\n\n• डाउट? `/ask आपका प्रश्न`\n• टेस्ट? `/test SSC`\n• प्रैक्टिस? `/practice SSC Quant`",
            "bn": "🤔 কি দরকার?\n\n• ডাউট? `/ask আপনার প্রশ্ন`\n• পরীক্ষা? `/test SSC`\n• প্র্যাক্টিস? `/practice SSC Quant`",
        }
        await msg.reply(hints.get(lang, hints["en"]))
