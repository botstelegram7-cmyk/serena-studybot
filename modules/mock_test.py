import asyncio, time, random
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_questions, get_pyq_questions, create_test_session, get_test_session,
    update_test_session, clear_test_session, save_completed_test,
    update_subject_stat, get_user, sessions_col
)
from modules.question_gen import generate_pyq_batch
from config import EXAMS

MARKS_SCHEME = {
    "SSC":     {"correct": 2,    "wrong": -0.5},
    "UPSC":    {"correct": 2,    "wrong": -0.66},
    "JEE":     {"correct": 4,    "wrong": -1},
    "RAILWAY": {"correct": 1,    "wrong": -0.25},
}

TEST_PRESETS = {
    "SSC_FULL":     {"exam":"SSC",     "total":100, "sections":{"Quant":25,"English":25,"Reasoning":25,"GK":25}},
    "UPSC_FULL":    {"exam":"UPSC",    "total":100, "sections":{"History":15,"Polity":20,"Geography":15,"Economy":15,"Science":10,"Current Affairs":25}},
    "JEE_FULL":     {"exam":"JEE",     "total":75,  "sections":{"Physics":25,"Chemistry":25,"Maths":25}},
    "RAILWAY_FULL": {"exam":"RAILWAY", "total":100, "sections":{"Quant":30,"Reasoning":30,"GK":25,"General Science":15}},
}


def _bar(pct: float, w: int = 12) -> str:
    f = int((pct/100)*w)
    return "█"*f + "░"*(w-f)

def _mini_bar(pct: float, w: int = 8) -> str:
    f = int((pct/100)*w)
    return "▓"*f + "░"*(w-f)


# ── FETCH QUESTIONS (PYQ ONLY) ───────────────────────────────
async def _fetch_section(exam: str, subject: str, count: int, difficulty: str) -> list:
    """Priority: DB PYQ → AI Generated PYQ (always tagged with exam+year)"""
    questions = []

    # 1. Try DB PYQ
    db_pyq = await get_pyq_questions(exam, subject, count)
    questions.extend(db_pyq)

    # 2. Fill with AI-generated PYQ (in batches of 5 to avoid truncation)
    attempts = 0
    while len(questions) < count and attempts < 4:
        needed = count - len(questions)
        batch  = min(needed, 5)
        ai_qs  = await generate_pyq_batch(exam, subject, count=batch, difficulty=difficulty)
        if ai_qs:
            questions.extend(ai_qs)
        else:
            attempts += 1
        await asyncio.sleep(0.3)  # Small delay between AI calls

    return questions[:count]


async def build_test(preset_key: str, exam: str, subject: str = None,
                     section: str = None, difficulty: str = "Medium",
                     custom_count: int = 10) -> list:
    if subject:
        qs = await _fetch_section(exam, subject, custom_count, difficulty)
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
        return await _fetch_section(exam, "GK", custom_count, difficulty)

    all_qs = []
    for subj, cnt in preset["sections"].items():
        qs = await _fetch_section(exam, subj, cnt, difficulty)
        all_qs.extend(qs)
    random.shuffle(all_qs)
    return all_qs


# ── START TEST ────────────────────────────────────────────────
async def start_mock_test(client: Client, message: Message,
                           exam: str, preset_key: str = None,
                           subject: str = None, section: str = None,
                           difficulty: str = "Medium",
                           custom_count: int = 10,
                           lang: str = "en"):
    uid  = message.from_user.id
    name = message.from_user.first_name

    # ALWAYS nuke existing sessions first — no blocking
    await sessions_col.delete_many({"uid": uid})

    marks   = MARKS_SCHEME.get(exam, {"correct": 2, "wrong": -0.5})
    diff_e  = {"Easy":"🟢","Medium":"🟡","Hard":"🔴"}.get(difficulty,"🟡")

    # Loading message
    msg = await message.reply(
        f"🔄 **Building your {exam} test...**\n\n"
        f"🟦⬜⬜⬜⬜ `20%` — Fetching PYQ questions...\n"
        f"⏱ Please wait ~15 seconds"
    )

    questions = await build_test(preset_key or "SSC_FULL", exam, subject,
                                  section, difficulty, custom_count)

    if not questions:
        await msg.edit("❌ Could not fetch questions. Try again in a moment.")
        return

    total    = len(questions)
    pyq_cnt  = sum(1 for q in questions if q.get("is_pyq", True))
    est_mins = max(1, (total * 90) // 60)

    # Save session — minimal data to avoid MongoDB size issues
    session_data = {
        "exam":          exam,
        "subject":       subject,
        "total":         total,
        "current_idx":   0,          # ← MUST initialize here
        "answers":       {},
        "start_time":    time.time(),
        "marks_correct": marks["correct"],
        "marks_wrong":   marks["wrong"],
        "difficulty":    difficulty,
        "lang":          lang,
        "status":        "running",
    }
    # Store questions separately to avoid size limit issues
    await create_test_session(uid, session_data)
    # Store questions in separate collection
    from database import db
    await db["test_questions"].delete_many({"uid": uid})
    await db["test_questions"].insert_one({"uid": uid, "questions": questions})

    await msg.edit(
        f"╔══════════════════════╗\n"
        f"║  🎯 **{exam} MOCK TEST**  ║\n"
        f"╚══════════════════════╝\n\n"
        f"👤 **{name}**\n"
        f"📋 Exam: **{exam}** | {diff_e} **{difficulty}**\n"
        f"❓ Questions: **{total}** | 📅 PYQ: **{pyq_cnt}**\n"
        f"✅ +{marks['correct']} Correct | ❌ {marks['wrong']} Wrong\n"
        f"⏱ Est. Time: **~{est_mins} min**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Starting in **3 seconds...**\n"
        f"💡 Tap correct option to answer!"
    )
    await asyncio.sleep(3)
    await send_next_question(client, message.chat.id, uid)


# ── GET SESSION + QUESTIONS ───────────────────────────────────
async def _get_session_and_questions(uid: int):
    from database import db
    session   = await get_test_session(uid)
    if not session:
        return None, None
    q_doc     = await db["test_questions"].find_one({"uid": uid})
    questions = q_doc["questions"] if q_doc else []
    return session, questions


# ── SEND QUESTION ─────────────────────────────────────────────
async def send_next_question(client: Client, chat_id: int, uid: int):
    session, questions = await _get_session_and_questions(uid)
    if not session or session["status"] != "running" or not questions:
        return

    idx   = session.get("current_idx", 0)
    total = session["total"]
    lang  = session.get("lang", "en")

    if idx >= total or idx >= len(questions):
        await finish_test(client, chat_id, uid)
        return

    q        = questions[idx]
    subj     = q.get("subject", "General")
    sec      = q.get("section", "")
    diff     = q.get("difficulty", "Medium")
    src      = q.get("exam_source", "")
    yr       = q.get("exam_year", "")
    diff_e   = {"Easy":"🟢","Medium":"🟡","Hard":"🔴"}.get(diff,"🏆")
    pct      = int((idx / total) * 100)
    left     = total - idx
    time_left = int((total - idx) * 90)  # ~90s per question estimate
    mins_l, secs_l = divmod(time_left, 60)

    # Source tag — always show exam name + year
    if src:
        source_tag = f"📅 `{src} ({yr})`" if yr else f"📅 `{src}`"
    else:
        source_tag = f"📅 `{session['exam']} PYQ 2024`"

    header = (
        f"{source_tag}\n"
        f"**Q{idx+1}/{total}** | {subj}" + (f" › {sec}" if sec else "") + f" {diff_e}\n"
        f"`{_bar(pct)}` {pct}% | ⏳ ~{mins_l}m {secs_l}s left\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**{q['question']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    opts    = q.get("options", [])
    em      = ["🅰️","🅱️","🆎","🆑"]
    buttons = []
    for i, opt in enumerate(opts[:4]):
        letter   = chr(65 + i)
        opt_text = opt[2:].strip() if (len(opt) > 2 and opt[1] in ".)") else opt
        buttons.append([InlineKeyboardButton(
            f"{em[i]} {opt_text[:55]}",
            callback_data=f"tans_{uid}_{idx}_{letter}"
        )])
    buttons.append([InlineKeyboardButton(
        "⏭ Skip", callback_data=f"tans_{uid}_{idx}_SKIP"
    )])

    await client.send_message(chat_id, header,
                               reply_markup=InlineKeyboardMarkup(buttons))


# ── PROCESS ANSWER ────────────────────────────────────────────
async def process_button_answer(client, uid: int, chat_id: int,
                                 q_idx: int, user_ans: str):
    session, questions = await _get_session_and_questions(uid)
    if not session or session["status"] != "running":
        await client.send_message(chat_id,
            "❌ No active test found. Start with /test SSC")
        return
    if not questions or q_idx >= len(questions):
        return

    q           = questions[q_idx]
    correct_ans = str(q.get("answer","")).strip().upper()[:1]
    is_skipped  = user_ans == "SKIP"
    is_correct  = (not is_skipped) and (user_ans == correct_ans)

    answers = session.get("answers", {})
    answers[str(q_idx)] = "SKIPPED" if is_skipped else user_ans
    next_idx = q_idx + 1

    await update_subject_stat(uid, q.get("subject","General"),
                               is_correct and not is_skipped)
    await update_test_session(uid, {"answers": answers, "current_idx": next_idx})

    # Feedback
    total      = session["total"]
    remaining  = total - next_idx
    mc         = session.get("marks_correct", 2)
    mw         = session.get("marks_wrong", -0.5)
    explanation= q.get("explanation","")[:180]
    short_m    = q.get("short_method","") or ""
    src        = q.get("exam_source","")
    yr         = q.get("exam_year","")

    if is_skipped:
        fb = (
            f"⏭ **Skipped** — Q{q_idx+1}\n"
            f"✅ Answer: **{correct_ans}**\n"
            + (f"💬 _{explanation}_" if explanation else "")
        )
    elif is_correct:
        fb = (
            f"✅ **CORRECT!** `+{mc} marks`\n\n"
            + (f"⚡ **Trick:** _{short_m[:150]}_\n" if short_m else "")
            + (f"📅 _{src}" + (f" ({yr})" if yr else "") + "_" if src else "")
        )
    else:
        opts = q.get("options",[])
        corr_text = next((o[2:].strip() for o in opts
                         if o.strip().upper().startswith(correct_ans)), "")
        fb = (
            f"❌ **WRONG!** `{mw} marks`\n\n"
            f"Your: **{user_ans}** → Correct: **{correct_ans}**"
            + (f"\n✅ _{corr_text[:80]}_" if corr_text else "")
            + (f"\n💬 _{explanation}_" if explanation else "")
            + (f"\n⚡ _{short_m[:120]}_" if short_m else "")
            + (f"\n📅 _{src}" + (f" ({yr})" if yr else "") + "_" if src else "")
        )

    pct_done = int((next_idx / total) * 100)
    if remaining > 0:
        fb += f"\n\n`{_mini_bar(pct_done)}` **{pct_done}%** done | **{remaining}** left"

    await client.send_message(chat_id, fb)

    if next_idx >= total:
        await asyncio.sleep(2)
        await finish_test(client, chat_id, uid)
    else:
        await asyncio.sleep(1.5)  # Anti-flood
        await send_next_question(client, chat_id, uid)


# ── FINISH + ANALYSIS ─────────────────────────────────────────
async def finish_test(client, chat_id: int, uid: int):
    session, questions = await _get_session_and_questions(uid)
    if not session or not questions:
        return

    user      = await get_user(uid)
    name      = user["name"] if user else "Student"
    answers   = session.get("answers", {})
    exam      = session.get("exam","SSC")
    mc        = session.get("marks_correct", 2)
    mw        = session.get("marks_wrong", -0.5)
    elapsed   = int(time.time() - session.get("start_time", time.time()))

    correct = wrong = skipped = 0
    subject_breakdown = {}
    wrong_questions   = []
    pyq_correct = pyq_total = 0

    for i, q in enumerate(questions):
        correct_ans = str(q.get("answer","")).strip().upper()[:1]
        user_ans    = answers.get(str(i), "SKIPPED")
        subj        = q.get("subject","General")
        is_pyq      = q.get("is_pyq", True)

        if subj not in subject_breakdown:
            subject_breakdown[subj] = {"total":0,"correct":0,"wrong":0}
        subject_breakdown[subj]["total"] += 1
        if is_pyq: pyq_total += 1

        if user_ans == "SKIPPED":
            skipped += 1
        elif user_ans == correct_ans:
            correct += 1
            subject_breakdown[subj]["correct"] += 1
            if is_pyq: pyq_correct += 1
        else:
            wrong += 1
            subject_breakdown[subj]["wrong"] += 1
            wrong_questions.append({
                "q":           q.get("question","")[:90],
                "your_ans":    user_ans,
                "correct_ans": correct_ans,
                "subject":     subj,
                "explanation": q.get("explanation","")[:150],
                "short_method":q.get("short_method",""),
                "exam_source": q.get("exam_source",""),
                "exam_year":   q.get("exam_year",""),
            })

    total_qs   = len(questions)
    raw_score  = (correct * mc) + (wrong * mw)
    max_score  = total_qs * mc
    percentage = round((raw_score / max_score)*100, 1) if max_score > 0 else 0
    accuracy   = round((correct / (correct+wrong))*100, 1) if (correct+wrong) > 0 else 0

    await save_completed_test(uid, {
        "exam":exam,"total":total_qs,"correct":correct,"wrong":wrong,
        "skipped":skipped,"score":raw_score,"max_score":max_score,
        "percentage":percentage,"accuracy":accuracy,
        "subject_breakdown":subject_breakdown,"time_taken":elapsed,
    })

    # Clean up
    await sessions_col.delete_many({"uid": uid})
    from database import db
    await db["test_questions"].delete_many({"uid": uid})

    mins, secs = divmod(elapsed, 60)
    grade      = _grade(percentage)
    rank_info  = _rank_estimate(exam, percentage)

    report = (
        f"╔══════════════════════════╗\n"
        f"║  🏁 **TEST COMPLETE!**       ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 **{name}** | 📋 {exam}\n"
        f"`{_bar(percentage)}` **{percentage}%**\n\n"
        f"┌──────────────────────────┐\n"
        f"│ ✅ Correct:  **{correct:>3}**  `+{correct*mc:.0f} pts`\n"
        f"│ ❌ Wrong:    **{wrong:>3}**  `{wrong*mw:.1f} pts`\n"
        f"│ ⏭ Skipped:  **{skipped:>3}**\n"
        f"│ ─────────────────────────\n"
        f"│ 📈 Score:    **{raw_score:.1f}** / {max_score:.0f}\n"
        f"│ 🎯 Accuracy: **{accuracy}%**\n"
        f"│ ⏱ Time:     **{mins}m {secs}s**\n"
        f"│ 🏆 Grade:    **{grade}**\n"
        f"└──────────────────────────┘\n"
    )

    if pyq_total > 0:
        pyq_pct = round((pyq_correct/pyq_total)*100)
        report += f"\n📅 **PYQ Accuracy:** {pyq_correct}/{pyq_total} `{_mini_bar(pyq_pct)}` {pyq_pct}%\n"

    report += f"\n{rank_info}\n\n**📚 SUBJECT ANALYSIS**\n"
    for subj, s in subject_breakdown.items():
        t2  = s["total"]
        c2  = s["correct"]
        pct = round((c2/t2)*100) if t2>0 else 0
        st  = "✅" if pct>=70 else ("⚠️" if pct>=40 else "❌")
        report += f"{st} **{subj}**: {c2}/{t2} `{_mini_bar(pct)}` {pct}%\n"

    weak = [s for s,v in subject_breakdown.items()
            if v["total"]>0 and (v["correct"]/v["total"])<0.5]
    if weak:
        report += f"\n⚠️ **Weak:** {', '.join(weak)} → `/practice {exam} {weak[0]}`"

    report += "\n\n📊 `/myprogress` | 🏆 `/leaderboard`"
    await client.send_message(chat_id, report)

    if wrong_questions:
        wt = f"📝 **{name} — Mistakes:**\n\n"
        for i, wq in enumerate(wrong_questions[:6], 1):
            src_line = (f"\n   📅 _{wq['exam_source']}"
                        + (f" ({wq['exam_year']})" if wq.get("exam_year") else "")
                        + "_") if wq.get("exam_source") else ""
            sm = f"\n   ⚡ _{wq['short_method'][:100]}_" if wq.get("short_method") else ""
            wt += (f"**{i}.** _{wq['q']}_\n"
                   f"   ❌ `{wq['your_ans']}` → ✅ `{wq['correct_ans']}`{src_line}\n"
                   f"   💬 {wq['explanation'][:130]}{sm}\n\n")
        if len(wrong_questions) > 6:
            wt += f"_...and {len(wrong_questions)-6} more_"
        await client.send_message(chat_id, wt)


def _rank_estimate(exam: str, pct: float) -> str:
    bands = {
        "SSC":     [(90,"🥇 Top 1% — ~1–1,000 rank"),(80,"🥈 Top 5% — ~1K–5K"),
                    (70,"🥉 Safe Zone ✅"),(60,"📊 Near Cutoff"),(0,"❌ Below Cutoff")],
        "UPSC":    [(70,"🥇 IAS Territory"),(60,"🥈 IPS/IFS Range"),
                    (50,"🥉 State Services"),(0,"❌ Below Cutoff")],
        "JEE":     [(85,"🥇 IIT Guaranteed"),(70,"🥈 Top NIT"),
                    (55,"🥉 NIT Possible"),(0,"❌ Needs Work")],
        "RAILWAY": [(85,"🥇 Sure Selection 🎉"),(75,"🥈 High Chance"),
                    (65,"🥉 DV Round Likely"),(0,"❌ Below Cutoff")],
    }
    for t, m in bands.get(exam, bands["SSC"]):
        if pct >= t:
            return f"┌ 🎯 **RANK ESTIMATE**\n└ {m}"
    return ""


def _grade(pct: float) -> str:
    if pct>=90: return "A+ 🌟 Outstanding"
    if pct>=80: return "A ⭐ Excellent"
    if pct>=70: return "B+ 👍 Good"
    if pct>=60: return "B 📚 Above Avg"
    if pct>=50: return "C ⚠️ Average"
    return "D 💪 Keep Going"
