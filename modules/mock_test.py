import asyncio, time, random
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_questions, get_pyq_questions, create_test_session, get_test_session,
    update_test_session, clear_test_session, save_completed_test,
    update_subject_stat, get_user, add_questions_bulk
)
from modules.question_gen import generate_pyq_batch, generate_ai_question, translate_question
from modules.quiz_apis    import fetch_external_questions
from config import POLL_TIMER, EXAMS

# ── MARKS SCHEME ─────────────────────────────────────────────
MARKS_SCHEME = {
    "SSC":     {"correct": 2,   "wrong": -0.5},
    "UPSC":    {"correct": 2,   "wrong": -0.66},
    "JEE":     {"correct": 4,   "wrong": -1},
    "RAILWAY": {"correct": 1,   "wrong": -0.25},
}

# ── TEST PRESETS ─────────────────────────────────────────────
TEST_PRESETS = {
    "SSC_FULL":      {"exam":"SSC",     "total":100,"time_min":60,
                      "sections":{"Quant":25,"English":25,"Reasoning":25,"GK":25}},
    "SSC_MINI":      {"exam":"SSC",     "total":25, "time_min":15,
                      "sections":{"Quant":7,"English":6,"Reasoning":6,"GK":6}},
    "UPSC_FULL":     {"exam":"UPSC",    "total":100,"time_min":120,
                      "sections":{"History":15,"Polity":15,"Geography":15,
                                  "Economy":15,"Science":15,"Current Affairs":25}},
    "JEE_FULL":      {"exam":"JEE",     "total":90, "time_min":180,
                      "sections":{"Physics":30,"Chemistry":30,"Maths":30}},
    "RAILWAY_FULL":  {"exam":"RAILWAY", "total":100,"time_min":90,
                      "sections":{"Quant":30,"Reasoning":30,"GK":25,"General Science":15}},
    "RAILWAY_MINI":  {"exam":"RAILWAY", "total":20, "time_min":20,
                      "sections":{"Quant":5,"Reasoning":5,"GK":5,"General Science":5}},
}

# ── MULTILANG STRINGS ─────────────────────────────────────────
MSG = {
    "en": {
        "test_ready":    "✅ **Test Ready!**",
        "starting":      "Starting in 3 seconds...",
        "q_label":       "Q{idx}/{total}",
        "correct":       "✅ Correct!",
        "wrong":         "❌ Wrong! Ans: {ans}",
        "short_method":  "⚡ Short Method:",
        "test_complete": "🎯 **TEST COMPLETE**",
        "preparing":     "⏳ Preparing test... please wait.",
        "already_active":"⚠️ A test is already active! Use /stoptest first.",
    },
    "hi": {
        "test_ready":    "✅ **टेस्ट तैयार है!**",
        "starting":      "3 सेकंड में शुरू हो रहा है...",
        "q_label":       "प्रश्न {idx}/{total}",
        "correct":       "✅ सही!",
        "wrong":         "❌ गलत! सही उत्तर: {ans}",
        "short_method":  "⚡ शॉर्ट मेथड:",
        "test_complete": "🎯 **टेस्ट पूर्ण**",
        "preparing":     "⏳ टेस्ट तैयार हो रहा है...",
        "already_active":"⚠️ एक टेस्ट पहले से चल रहा है! पहले /stoptest करें।",
    },
    "bn": {
        "test_ready":    "✅ **পরীক্ষা প্রস্তুত!**",
        "starting":      "৩ সেকেন্ডে শুরু হচ্ছে...",
        "q_label":       "প্রশ্ন {idx}/{total}",
        "correct":       "✅ সঠিক!",
        "wrong":         "❌ ভুল! সঠিক উত্তর: {ans}",
        "short_method":  "⚡ শর্ট মেথড:",
        "test_complete": "🎯 **পরীক্ষা সম্পন্ন**",
        "preparing":     "⏳ পরীক্ষা প্রস্তুত হচ্ছে...",
        "already_active":"⚠️ একটি পরীক্ষা ইতিমধ্যে চলছে! আগে /stoptest করুন।",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    s = MSG.get(lang, MSG["en"]).get(key, MSG["en"].get(key, key))
    return s.format(**kwargs) if kwargs else s


def _bar(pct: float, w: int = 10) -> str:
    f = int((pct / 100) * w)
    return "█" * f + "░" * (w - f)


# ── QUESTION FETCHING ─────────────────────────────────────────
async def _fetch_questions_for_section(exam: str, subject: str, count: int,
                                        difficulty: str, prefer_pyq: bool,
                                        lang: str) -> list:
    """
    Priority: DB PYQ → DB general → External API → AI Generated
    """
    questions = []

    # 1. Try DB PYQ first
    if prefer_pyq:
        db_pyq = await get_pyq_questions(exam, subject, count)
        questions.extend(db_pyq)

    # 2. Fill from DB general
    if len(questions) < count:
        needed  = count - len(questions)
        db_qs   = await get_questions(exam, subject, difficulty=difficulty,
                                       count=needed)
        existing_ids = {str(q.get("_id","")) for q in questions}
        for q in db_qs:
            if str(q.get("_id","")) not in existing_ids:
                questions.append(q)

    # 3. External APIs
    if len(questions) < count:
        needed  = count - len(questions)
        ext_qs  = await fetch_external_questions(subject, needed, difficulty.lower())
        questions.extend(ext_qs)

    # 4. AI Generate remainder
    if len(questions) < count:
        needed = count - len(questions)
        print(f"[Test] Generating {needed} AI PYQ questions for {exam}/{subject}")
        ai_qs  = await generate_pyq_batch(exam, subject, count=needed,
                                           difficulty=difficulty)
        questions.extend(ai_qs)

    # Translate if needed
    if lang != "en":
        translated = []
        for q in questions[:count]:
            translated.append(await translate_question(q, lang))
        return translated

    return questions[:count]


async def build_test(preset_key: str, exam: str, subject: str = None,
                      section: str = None, difficulty: str = "Medium",
                      custom_count: int = 10, prefer_pyq: bool = True,
                      lang: str = "en") -> list:
    """Build full question list for a test"""

    if subject:
        # Subject/section-wise practice
        qs = await _fetch_questions_for_section(
            exam, subject, custom_count, difficulty, prefer_pyq, lang
        )
        if section:
            filtered = [q for q in qs if q.get("section","").lower() == section.lower()]
            if len(filtered) < custom_count:
                extra = await generate_pyq_batch(exam, subject, section,
                                                  custom_count - len(filtered), difficulty)
                filtered.extend(extra)
            qs = filtered
        return qs[:custom_count]

    preset = TEST_PRESETS.get(preset_key)
    if not preset:
        # Custom quick test
        return await _fetch_questions_for_section(
            exam, None, custom_count, difficulty, prefer_pyq, lang
        )

    all_qs = []
    for subj, cnt in preset["sections"].items():
        qs = await _fetch_questions_for_section(
            exam, subj, cnt, difficulty, prefer_pyq, lang
        )
        all_qs.extend(qs)

    random.shuffle(all_qs)
    return all_qs


# ── START TEST ────────────────────────────────────────────────
async def start_mock_test(client: Client, message: Message,
                           exam: str, preset_key: str = None,
                           subject: str = None, section: str = None,
                           difficulty: str = "Medium",
                           custom_count: int = 10,
                           prefer_pyq: bool = True,
                           lang: str = "en"):
    uid  = message.from_user.id
    name = message.from_user.first_name

    existing = await get_test_session(uid)
    if existing:
        await message.reply(t(lang, "already_active"))
        return

    msg = await message.reply(t(lang, "preparing"))

    questions = await build_test(
        preset_key or "SSC_MINI", exam, subject, section,
        difficulty, custom_count, prefer_pyq, lang
    )

    if not questions:
        await msg.edit("❌ Questions not available. Please try again.")
        return

    marks = MARKS_SCHEME.get(exam, {"correct": 2, "wrong": -0.5})

    await create_test_session(uid, {
        "exam":        exam,
        "subject":     subject,
        "questions":   questions,
        "current_idx": 0,
        "total":       len(questions),
        "answers":     {},
        "start_time":  time.time(),
        "marks_correct": marks["correct"],
        "marks_wrong":   marks["wrong"],
        "difficulty":  difficulty,
        "lang":        lang,
        "status":      "running",
    })

    pyq_count = sum(1 for q in questions if q.get("is_pyq"))
    pyq_info  = f"📅 PYQ: **{pyq_count}/{len(questions)}** real exam questions\n" if pyq_count else ""

    await msg.edit(
        f"{t(lang, 'test_ready')}\n\n"
        f"📋 Exam: **{exam}**\n"
        f"❓ Questions: **{len(questions)}**\n"
        f"📊 Difficulty: **{difficulty}**\n"
        f"{pyq_info}"
        f"✅ +{marks['correct']} Correct  |  ❌ {marks['wrong']} Wrong\n\n"
        f"📌 Har question poll mein aayega!\n\n"
        f"{t(lang, 'starting')}"
    )
    await asyncio.sleep(3)
    await send_next_poll(client, message.chat.id, uid)


# ── SEND POLL ─────────────────────────────────────────────────
async def send_next_poll(client: Client, chat_id: int, uid: int):
    session = await get_test_session(uid)
    if not session or session["status"] != "running":
        return

    idx       = session["current_idx"]
    questions = session["questions"]
    lang      = session.get("lang", "en")

    if idx >= len(questions):
        await finish_test(client, chat_id, uid)
        return

    q      = questions[idx]
    total  = session["total"]
    subj   = q.get("subject", "General")
    sec    = q.get("section", "")
    diff   = q.get("difficulty", "Medium")
    src    = q.get("exam_source", "")
    yr     = q.get("exam_year", "")

    diff_emoji = {"Easy":"🟢","Medium":"🟡","Hard":"🔴","PYQ":"🏆"}.get(diff,"🟡")

    # Build header showing exam source + year
    if q.get("is_pyq") and src:
        source_line = f"📅 **{src}**" + (f" ({yr})" if yr else "")
    else:
        source_line = f"🤖 AI Generated • {subj}"

    q_header = (
        f"{source_line}\n"
        f"{t(lang,'q_label',idx=idx+1,total=total)} | {subj}"
        + (f" › {sec}" if sec else "")
        + f" {diff_emoji}\n\n"
    )

    question_text = q_header + q["question"]

    options = [str(opt)[:100] for opt in q.get("options", ["A","B","C","D"])]

    try:
        poll_msg = await client.send_poll(
            chat_id    = chat_id,
            question   = question_text[:255],
            options    = options,
            is_anonymous = False,
            open_period  = POLL_TIMER,
            explanation  = (
                f"✅ Answer: {q.get('answer','?')} | "
                f"{q.get('explanation','')}"
            )[:200],
        )
        poll_ids = session.get("poll_msg_ids", {})
        poll_ids[str(idx)] = poll_msg.id
        await update_test_session(uid, {
            "current_poll_id": poll_msg.id,
            "poll_msg_ids":    poll_ids,
        })
    except Exception as e:
        print(f"[Poll] Error: {e}")
        await _send_button_question(client, chat_id, uid, q, idx, total, lang)


async def _send_button_question(client, chat_id, uid, q, idx, total, lang):
    """Fallback: inline buttons if poll fails"""
    opts    = q.get("options", [])
    buttons = []
    for i, opt in enumerate(opts):
        letter = chr(65 + i)
        buttons.append([InlineKeyboardButton(
            opt[:60],
            callback_data=f"ans_{uid}_{idx}_{letter}"
        )])

    subj = q.get("subject","")
    diff = q.get("difficulty","Medium")
    src  = q.get("exam_source","")
    yr   = q.get("exam_year","")
    diff_emoji = {"Easy":"🟢","Medium":"🟡","Hard":"🔴"}.get(diff,"🟡")
    source_line = (f"📅 **{src}**" + (f" ({yr})" if yr else "")) if q.get("is_pyq") and src else f"🤖 AI • {subj}"

    text = (
        f"{source_line}\n"
        f"**{t(lang,'q_label',idx=idx+1,total=total)}** | {subj} {diff_emoji}\n\n"
        f"{q['question']}"
    )
    await client.send_message(chat_id, text,
                               reply_markup=InlineKeyboardMarkup(buttons))


# ── PROCESS ANSWERS ───────────────────────────────────────────
async def process_poll_answer(client, uid: int, poll_id: int, chosen_ids: list):
    session = await get_test_session(uid)
    if not session or session["status"] != "running":
        return

    idx       = session["current_idx"]
    questions = session["questions"]
    q         = questions[idx]
    lang      = session.get("lang","en")

    letter_map = {0:"A",1:"B",2:"C",3:"D"}
    user_ans   = letter_map.get(chosen_ids[0],"A") if chosen_ids else "SKIPPED"

    answers       = session.get("answers", {})
    answers[str(idx)] = user_ans
    next_idx      = idx + 1

    correct_ans   = str(q.get("answer","")).strip().upper()[:1]
    is_correct    = user_ans == correct_ans
    await update_subject_stat(uid, q.get("subject","General"), is_correct)
    await update_test_session(uid, {"answers": answers, "current_idx": next_idx})

    if next_idx >= session["total"]:
        await finish_test(client, uid, uid)
    else:
        await asyncio.sleep(1)
        await send_next_poll(client, uid, uid)


async def process_button_answer(client, uid: int, chat_id: int,
                                 q_idx: int, user_ans: str):
    session = await get_test_session(uid)
    if not session or session["status"] != "running":
        return

    questions   = session["questions"]
    lang        = session.get("lang","en")
    q           = questions[q_idx]
    correct_ans = str(q.get("answer","")).strip().upper()[:1]
    is_correct  = user_ans == correct_ans

    answers       = session.get("answers", {})
    answers[str(q_idx)] = user_ans
    next_idx      = q_idx + 1

    await update_subject_stat(uid, q.get("subject","General"), is_correct)
    await update_test_session(uid, {"answers": answers, "current_idx": next_idx})

    emoji   = "✅" if is_correct else "❌"
    sm      = q.get("short_method","") or ""
    fb_text = (
        f"{t(lang,'correct') if is_correct else t(lang,'wrong',ans=correct_ans)}\n"
        + (f"{t(lang,'short_method')} _{sm[:200]}_" if sm else "")
    )
    await client.send_message(chat_id, fb_text)

    if next_idx >= session["total"]:
        await finish_test(client, chat_id, uid)
    else:
        await asyncio.sleep(1)
        await send_next_poll(client, chat_id, uid)


# ── FINISH + ANALYSIS ─────────────────────────────────────────
async def finish_test(client, chat_id: int, uid: int):
    session = await get_test_session(uid)
    if not session:
        return

    user      = await get_user(uid)
    name      = user["name"] if user else "Student"
    lang      = session.get("lang","en")
    questions = session["questions"]
    answers   = session.get("answers",{})
    exam      = session.get("exam","SSC")
    mc        = session.get("marks_correct",2)
    mw        = session.get("marks_wrong",-0.5)
    elapsed   = int(time.time() - session.get("start_time", time.time()))

    # ── Score Calculation ─────────────────────────────────────
    correct = wrong = skipped = 0
    subject_breakdown  = {}
    wrong_questions    = []
    pyq_correct        = 0
    pyq_total          = 0

    for i, q in enumerate(questions):
        correct_ans = str(q.get("answer","")).strip().upper()[:1]
        user_ans    = answers.get(str(i),"SKIPPED")
        subj        = q.get("subject","General")
        is_pyq      = q.get("is_pyq", False)

        if subj not in subject_breakdown:
            subject_breakdown[subj] = {"total":0,"correct":0,"wrong":0,"pyq_total":0,"pyq_correct":0}
        subject_breakdown[subj]["total"] += 1
        if is_pyq:
            pyq_total += 1
            subject_breakdown[subj]["pyq_total"] += 1

        if user_ans == "SKIPPED":
            skipped += 1
        elif user_ans == correct_ans:
            correct += 1
            subject_breakdown[subj]["correct"] += 1
            if is_pyq:
                pyq_correct += 1
                subject_breakdown[subj]["pyq_correct"] += 1
        else:
            wrong += 1
            subject_breakdown[subj]["wrong"] += 1
            wrong_questions.append({
                "q":          q.get("question","")[:100],
                "your_ans":   user_ans,
                "correct_ans":correct_ans,
                "subject":    subj,
                "explanation":q.get("explanation","")[:200],
                "short_method":q.get("short_method",""),
                "exam_source":q.get("exam_source",""),
                "exam_year":  q.get("exam_year",""),
            })

    total_qs   = len(questions)
    raw_score  = (correct * mc) + (wrong * mw)
    max_score  = total_qs * mc
    percentage = round((raw_score / max_score)*100, 1) if max_score > 0 else 0
    accuracy   = round((correct / (correct+wrong))*100,1) if (correct+wrong)>0 else 0

    await save_completed_test(uid, {
        "exam": exam, "total": total_qs, "correct": correct,
        "wrong": wrong, "skipped": skipped,
        "score": raw_score, "max_score": max_score,
        "percentage": percentage, "accuracy": accuracy,
        "subject_breakdown": subject_breakdown,
        "time_taken": elapsed,
    })
    await clear_test_session(uid)

    # ── Format Main Analysis ──────────────────────────────────
    mins, secs = divmod(elapsed, 60)
    grade      = _grade(percentage)
    rank_info  = _rank_estimate(exam, percentage)

    report = (
        f"🎯 **{t(lang,'test_complete')} — {name}!**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **SCORECARD**\n"
        f"`{_bar(percentage)}` **{percentage}%**\n\n"
        f"✅ Correct:   **{correct}**  `(+{correct*mc:.1f})`\n"
        f"❌ Wrong:     **{wrong}**   `({wrong*mw:.1f})`\n"
        f"⏭ Skipped:   **{skipped}**\n"
        f"━━━━━━━━━━━━━\n"
        f"📈 Score:     **{raw_score:.1f} / {max_score:.1f}**\n"
        f"🎯 Accuracy:  **{accuracy}%**\n"
        f"⏱ Time:      **{mins}m {secs}s**\n"
        f"🏆 Grade:     **{grade}**\n"
    )

    if pyq_total > 0:
        pyq_acc = round((pyq_correct/pyq_total)*100)
        report += f"📅 PYQ Accuracy: **{pyq_acc}%** ({pyq_correct}/{pyq_total})\n"

    report += f"\n{rank_info}\n\n"

    # Subject breakdown
    report += "📚 **SUBJECT ANALYSIS**\n"
    for subj, s in subject_breakdown.items():
        t2  = s["total"]
        c2  = s["correct"]
        pct = round((c2/t2)*100) if t2 > 0 else 0
        st  = "✅" if pct>=70 else ("⚠️" if pct>=40 else "❌")
        report += f"{st} **{subj}**: {c2}/{t2} `{_bar(pct,8)}` {pct}%\n"

    # Weak areas
    weak = [s for s,v in subject_breakdown.items()
            if v["total"]>0 and (v["correct"]/v["total"])<0.5]
    if weak:
        report += f"\n⚠️ **Focus These:** {', '.join(weak)}\n"
        report += "💡 `/practice " + exam + " " + weak[0] + "` — targeted practice\n"

    report += "\n📋 `/solutions` — Galat questions explanation"

    await client.send_message(chat_id, report)

    # ── Wrong Questions Detail ────────────────────────────────
    if wrong_questions:
        wtext = f"❌ **{name} — Missed Questions:**\n\n"
        for i, wq in enumerate(wrong_questions[:6], 1):
            src_line = ""
            if wq.get("exam_source"):
                src_line = f"\n   📅 _{wq['exam_source']}" + (f" ({wq['exam_year']})" if wq.get('exam_year') else "") + "_"
            sm = f"\n   ⚡ _{wq['short_method'][:120]}_" if wq.get("short_method") else ""
            wtext += (
                f"**{i}.** {wq['q']}\n"
                f"   ❌ You: {wq['your_ans']}  ✅ Ans: {wq['correct_ans']}{src_line}\n"
                f"   💬 _{wq['explanation'][:150]}_{sm}\n\n"
            )
        if len(wrong_questions) > 6:
            wtext += f"_...and {len(wrong_questions)-6} more mistakes_"
        await client.send_message(chat_id, wtext)


def _rank_estimate(exam: str, pct: float) -> str:
    bands = {
        "SSC":     [(90,"🥇 Top 1% — Expected: 1–1,000 rank"),
                    (80,"🥈 Top 5% — Expected: 1K–5K rank"),
                    (70,"🥉 Top 15% — Safe zone"),
                    (60,"📊 Borderline — Near cutoff"),
                    (50,"⚠️ Below average cutoff"),
                    (0, "❌ Below cutoff — Needs work")],
        "UPSC":    [(70,"🥇 Excellent — IAS territory"),
                    (60,"🥈 IPS/IFS range"),
                    (50,"🥉 State services level"),
                    (40,"⚠️ Below UPSC cutoff"),
                    (0, "❌ Significant improvement needed")],
        "JEE":     [(85,"🥇 IIT guaranteed territory"),
                    (70,"🥈 Top NIT rank"),
                    (55,"🥉 NIT possible"),
                    (40,"⚠️ Below NIT cutoff"),
                    (0, "❌ Needs major improvement")],
        "RAILWAY": [(85,"🥇 Sure selection"),
                    (75,"🥈 Very good — High chance"),
                    (65,"🥉 Document verification likely"),
                    (55,"⚠️ Borderline"),
                    (0, "❌ Below cutoff")],
    }
    for threshold, msg in bands.get(exam, bands["SSC"]):
        if pct >= threshold:
            return f"🎯 **Rank Estimate:** {msg}"
    return "🎯 Keep practicing!"


def _grade(pct: float) -> str:
    if pct>=90: return "A+ 🌟"
    if pct>=80: return "A ⭐"
    if pct>=70: return "B+ 👍"
    if pct>=60: return "B 📚"
    if pct>=50: return "C ⚠️"
    return "D — Keep going! 💪"
