import asyncio, time, random
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_questions, get_pyq_questions, create_test_session, get_test_session,
    update_test_session, clear_test_session, save_completed_test,
    update_subject_stat, get_user
)
from modules.question_gen import generate_pyq_batch, generate_ai_question
from modules.quiz_apis    import fetch_external_questions
from config import EXAMS

MARKS_SCHEME = {
    "SSC":     {"correct": 2,    "wrong": -0.5},
    "UPSC":    {"correct": 2,    "wrong": -0.66},
    "JEE":     {"correct": 4,    "wrong": -1},
    "RAILWAY": {"correct": 1,    "wrong": -0.25},
}

TEST_PRESETS = {
    "SSC_FULL":     {"exam":"SSC",     "total":100, "sections":{"Quant":25,"English":25,"Reasoning":25,"GK":25}},
    "SSC_MINI":     {"exam":"SSC",     "total":25,  "sections":{"Quant":7,"English":6,"Reasoning":6,"GK":6}},
    "UPSC_FULL":    {"exam":"UPSC",    "total":100, "sections":{"History":15,"Polity":15,"Geography":15,"Economy":15,"Science":15,"Current Affairs":25}},
    "JEE_FULL":     {"exam":"JEE",     "total":90,  "sections":{"Physics":30,"Chemistry":30,"Maths":30}},
    "RAILWAY_FULL": {"exam":"RAILWAY", "total":100, "sections":{"Quant":30,"Reasoning":30,"GK":25,"General Science":15}},
}

# ── PROGRESS ANIMATION ───────────────────────────────────────
LOADING_FRAMES = ["⬜⬜⬜⬜⬜","🟦⬜⬜⬜⬜","🟦🟦⬜⬜⬜","🟦🟦🟦⬜⬜","🟦🟦🟦🟦⬜","🟦🟦🟦🟦🟦"]

async def animated_progress(msg, label: str, total_steps: int):
    """Show animated loading with ETA"""
    start = time.time()
    for i, frame in enumerate(LOADING_FRAMES):
        pct     = int((i / len(LOADING_FRAMES)) * 100)
        elapsed = time.time() - start
        eta     = int((elapsed / max(i, 1)) * (len(LOADING_FRAMES) - i)) if i > 0 else "..."
        eta_str = f"{eta}s" if isinstance(eta, int) else eta
        try:
            await msg.edit(
                f"⚙️ **{label}**\n\n"
                f"{frame} `{pct}%`\n"
                f"⏱ ETA: `{eta_str}`\n\n"
                f"_Please wait..._"
            )
        except Exception:
            pass
        await asyncio.sleep(0.4)


def _bar(pct: float, w: int = 12) -> str:
    filled = int((pct / 100) * w)
    return "█" * filled + "░" * (w - filled)


def _mini_bar(pct: float, w: int = 8) -> str:
    filled = int((pct / 100) * w)
    return "▓" * filled + "░" * (w - filled)


# ── QUESTION FETCHING ─────────────────────────────────────────
async def _fetch_section(exam, subject, count, difficulty, prefer_pyq, lang):
    questions = []
    if prefer_pyq:
        questions.extend(await get_pyq_questions(exam, subject, count))
    if len(questions) < count:
        needed = count - len(questions)
        db_qs  = await get_questions(exam, subject, difficulty=difficulty, count=needed)
        seen   = {str(q.get("_id","")) for q in questions}
        for q in db_qs:
            if str(q.get("_id","")) not in seen:
                questions.append(q)
    if len(questions) < count:
        needed  = count - len(questions)
        ext_qs  = await fetch_external_questions(subject, needed, difficulty.lower())
        questions.extend(ext_qs)
    if len(questions) < count:
        needed = count - len(questions)
        # Generate in smaller batches to avoid JSON truncation
        batch_size = 5
        while needed > 0:
            batch = min(batch_size, needed)
            ai_qs = await generate_pyq_batch(exam, subject, count=batch, difficulty=difficulty)
            questions.extend(ai_qs)
            needed -= len(ai_qs)
            if not ai_qs:
                break
    return questions[:count]


async def build_test(preset_key, exam, subject=None, section=None,
                     difficulty="Medium", custom_count=10,
                     prefer_pyq=True, lang="en"):
    if subject:
        qs = await _fetch_section(exam, subject, custom_count, difficulty, prefer_pyq, lang)
        if section:
            filtered = [q for q in qs if q.get("section","").lower() == section.lower()]
            if len(filtered) < custom_count:
                extra = await generate_pyq_batch(exam, subject, section, custom_count - len(filtered), difficulty)
                filtered.extend(extra)
            qs = filtered
        return qs[:custom_count]

    preset = TEST_PRESETS.get(preset_key)
    if not preset:
        return await _fetch_section(exam, None, custom_count, difficulty, prefer_pyq, lang)

    all_qs = []
    for subj, cnt in preset["sections"].items():
        qs = await _fetch_section(exam, subj, cnt, difficulty, prefer_pyq, lang)
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

    if await get_test_session(uid):
        await message.reply(
            "⚠️ **Test already running!**\n"
            "Use /stoptest to end it first."
        )
        return

    # ── Animated Loading ──────────────────────────────────────
    msg = await message.reply(
        f"🔄 **Preparing your {exam} test, {name}...**\n\n"
        f"⬜⬜⬜⬜⬜ `0%`\n⏱ ETA: `calculating...`"
    )

    load_task = asyncio.create_task(
        animated_progress(msg, f"Building {exam} Test", 6)
    )

    questions = await build_test(
        preset_key or "SSC_MINI", exam, subject, section,
        difficulty, custom_count, prefer_pyq, lang
    )
    load_task.cancel()

    if not questions:
        await msg.edit("❌ Questions unavailable. Try again later.")
        return

    marks    = MARKS_SCHEME.get(exam, {"correct": 2, "wrong": -0.5})
    pyq_cnt  = sum(1 for q in questions if q.get("is_pyq"))
    total    = len(questions)
    est_mins = (total * 60) // 60  # ~1 min per question estimate

    await create_test_session(uid, {
        "exam": exam, "subject": subject,
        "questions": questions, "current_idx": 0,
        "total": total, "answers": {},
        "start_time": time.time(),
        "marks_correct": marks["correct"],
        "marks_wrong":   marks["wrong"],
        "difficulty": difficulty, "lang": lang,
        "status": "running",
    })

    diff_emoji = {"Easy":"🟢","Medium":"🟡","Hard":"🔴"}.get(difficulty,"🏆")

    await msg.edit(
        f"╔══════════════════════╗\n"
        f"║   🎯 **{exam} MOCK TEST**   ║\n"
        f"╚══════════════════════╝\n\n"
        f"👤 Student: **{name}**\n"
        f"📋 Exam: **{exam}**\n"
        f"❓ Questions: **{total}**\n"
        f"📊 Difficulty: {diff_emoji} **{difficulty}**\n"
        f"📅 PYQ Questions: **{pyq_cnt}/{total}**\n"
        f"✅ Correct: **+{marks['correct']}** | ❌ Wrong: **{marks['wrong']}**\n"
        f"⏱ Est. Time: **~{est_mins} min**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Starting in **3 seconds...**\n"
        f"💡 _Tap the correct option button!_"
    )
    await asyncio.sleep(3)
    await send_next_question(client, message.chat.id, uid)


# ── SEND QUESTION ─────────────────────────────────────────────
async def send_next_question(client: Client, chat_id: int, uid: int):
    session = await get_test_session(uid)
    if not session or session["status"] != "running":
        return

    idx       = session["current_idx"]
    questions = session["questions"]
    lang      = session.get("lang", "en")

    if idx >= len(questions):
        await finish_test(client, chat_id, uid)
        return

    q     = questions[idx]
    total = session["total"]
    subj  = q.get("subject", "General")
    sec   = q.get("section", "")
    diff  = q.get("difficulty", "Medium")
    src   = q.get("exam_source", "")
    yr    = q.get("exam_year", "")

    diff_emoji = {"Easy":"🟢","Medium":"🟡","Hard":"🔴","PYQ":"🏆"}.get(diff,"🟡")

    # Progress bar
    progress_pct = int((idx / total) * 100)
    prog_bar     = _bar(progress_pct)
    remaining_q  = total - idx

    # Source badge
    if q.get("is_pyq") and src:
        source_badge = f"📅 `{src}" + (f" ({yr})" if yr else "") + "`"
    else:
        source_badge = f"🤖 `AI Generated • {subj}`"

    # Build question message
    header = (
        f"┌─────────────────────────┐\n"
        f"│ {source_badge}\n"
        f"└─────────────────────────┘\n\n"
        f"**Q{idx+1}** of **{total}** | {subj}"
        + (f" › {sec}" if sec else "")
        + f" {diff_emoji}\n"
        f"`{prog_bar}` {progress_pct}%\n"
        f"⏳ **{remaining_q}** questions left\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**{q['question']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

    options = q.get("options", [])
    opt_emojis = ["🅰️","🅱️","🆎","🆑"]
    buttons = []
    for i, opt in enumerate(options):
        letter = chr(65 + i)
        # Clean option text (remove "A. " prefix if present)
        opt_text = opt
        if len(opt) > 2 and opt[1] in ".)" and opt[0].isalpha():
            opt_text = opt[2:].strip()
        buttons.append([InlineKeyboardButton(
            f"{opt_emojis[i] if i < 4 else letter} {opt_text[:55]}",
            callback_data=f"ans_{uid}_{idx}_{letter}"
        )])

    # Skip button
    buttons.append([InlineKeyboardButton("⏭ Skip Question", callback_data=f"ans_{uid}_{idx}_SKIP")])

    await client.send_message(
        chat_id,
        header,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ── PROCESS BUTTON ANSWER ─────────────────────────────────────
async def process_button_answer(client, uid: int, chat_id: int,
                                 q_idx: int, user_ans: str):
    session = await get_test_session(uid)
    if not session or session["status"] != "running":
        return

    questions   = session["questions"]
    lang        = session.get("lang", "en")
    if q_idx >= len(questions):
        return

    q           = questions[q_idx]
    correct_ans = str(q.get("answer", "")).strip().upper()[:1]
    is_correct  = user_ans == correct_ans
    is_skipped  = user_ans == "SKIP"

    answers = session.get("answers", {})
    answers[str(q_idx)] = "SKIPPED" if is_skipped else user_ans
    next_idx = q_idx + 1

    await update_subject_stat(uid, q.get("subject","General"), is_correct and not is_skipped)
    await update_test_session(uid, {"answers": answers, "current_idx": next_idx})

    # ── Feedback message ──────────────────────────────────────
    total       = session["total"]
    remaining   = total - next_idx
    src         = q.get("exam_source","")
    yr          = q.get("exam_year","")
    explanation = q.get("explanation","")[:180]
    short_m     = q.get("short_method","")

    if is_skipped:
        fb = (
            f"⏭ **Skipped** — Q{q_idx+1}\n"
            f"✅ Correct Answer: **{correct_ans}**\n"
            f"💬 _{explanation}_"
        )
    elif is_correct:
        fb = (
            f"✅ **CORRECT!** +{session.get('marks_correct',2)} marks\n\n"
            f"Q{q_idx+1}: {q['question'][:60]}...\n"
            + (f"\n⚡ **Short Method:** _{short_m[:150]}_" if short_m else "")
        )
    else:
        options = q.get("options", [])
        correct_text = ""
        for opt in options:
            if opt.strip().upper().startswith(correct_ans):
                correct_text = opt[2:].strip() if len(opt)>2 else opt
                break
        fb = (
            f"❌ **WRONG!** {session.get('marks_wrong',-0.5)} marks\n\n"
            f"Your answer: **{user_ans}** | Correct: **{correct_ans}**\n"
            + (f"✅ _{correct_text[:80]}_\n" if correct_text else "")
            + (f"\n💬 _{explanation}_" if explanation else "")
            + (f"\n⚡ **Trick:** _{short_m[:120]}_" if short_m else "")
            + (f"\n📅 _{src}" + (f" ({yr})" if yr else "") + "_" if src else "")
        )

    # Progress footer
    if remaining > 0:
        progress_pct = int((next_idx / total) * 100)
        fb += f"\n\n`{_mini_bar(progress_pct)}` **{progress_pct}%** | {remaining} left"
    
    await client.send_message(chat_id, fb)

    if next_idx >= total:
        await asyncio.sleep(1)
        await finish_test(client, chat_id, uid)
    else:
        await asyncio.sleep(0.8)
        await send_next_question(client, chat_id, uid)


# ── FINISH + FULL ANALYSIS ────────────────────────────────────
async def finish_test(client, chat_id: int, uid: int):
    session = await get_test_session(uid)
    if not session:
        return

    user      = await get_user(uid)
    name      = user["name"] if user else "Student"
    questions = session["questions"]
    answers   = session.get("answers", {})
    exam      = session.get("exam", "SSC")
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
        subj        = q.get("subject", "General")
        is_pyq      = q.get("is_pyq", False)

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
                "explanation": q.get("explanation","")[:160],
                "short_method":q.get("short_method",""),
                "exam_source": q.get("exam_source",""),
                "exam_year":   q.get("exam_year",""),
            })

    total_qs   = len(questions)
    raw_score  = (correct * mc) + (wrong * mw)
    max_score  = total_qs * mc
    percentage = round((raw_score / max_score) * 100, 1) if max_score > 0 else 0
    accuracy   = round((correct / (correct + wrong)) * 100, 1) if (correct + wrong) > 0 else 0

    await save_completed_test(uid, {
        "exam": exam, "total": total_qs, "correct": correct,
        "wrong": wrong, "skipped": skipped,
        "score": raw_score, "max_score": max_score,
        "percentage": percentage, "accuracy": accuracy,
        "subject_breakdown": subject_breakdown, "time_taken": elapsed,
    })
    await clear_test_session(uid)

    mins, secs = divmod(elapsed, 60)
    grade      = _grade(percentage)
    rank_info  = _rank_estimate(exam, percentage)
    grade_bar  = _bar(percentage)

    # ── Main Report ───────────────────────────────────────────
    report = (
        f"╔══════════════════════════╗\n"
        f"║  🏁 **TEST COMPLETE!**       ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 **{name}** | 📋 {exam}\n\n"
        f"**SCORECARD**\n"
        f"`{grade_bar}` **{percentage}%**\n\n"
        f"┌────────────────────────┐\n"
        f"│ ✅ Correct:  **{correct:>3}**  (+{correct*mc:.0f} pts)\n"
        f"│ ❌ Wrong:    **{wrong:>3}**  ({wrong*mw:.1f} pts)\n"
        f"│ ⏭ Skipped:  **{skipped:>3}**\n"
        f"│ ━━━━━━━━━━━━━━━━━━━\n"
        f"│ 📈 Score:  **{raw_score:.1f}** / {max_score:.0f}\n"
        f"│ 🎯 Accuracy: **{accuracy}%**\n"
        f"│ ⏱ Time: **{mins}m {secs}s**\n"
        f"│ 🏆 Grade: **{grade}**\n"
        f"└────────────────────────┘\n"
    )

    if pyq_total > 0:
        pyq_pct = round((pyq_correct / pyq_total) * 100)
        report += f"\n📅 **PYQ Accuracy:** {pyq_correct}/{pyq_total} `{_mini_bar(pyq_pct)}` {pyq_pct}%\n"

    report += f"\n{rank_info}\n\n"

    # Subject breakdown
    report += "**📚 SUBJECT ANALYSIS**\n"
    for subj, s in subject_breakdown.items():
        t2  = s["total"]
        c2  = s["correct"]
        w2  = s["wrong"]
        pct = round((c2 / t2) * 100) if t2 > 0 else 0
        st  = "✅" if pct >= 70 else ("⚠️" if pct >= 40 else "❌")
        report += f"{st} **{subj}**\n   `{_mini_bar(pct)}` {pct}% ({c2}✓ {w2}✗)\n"

    weak = [s for s, v in subject_breakdown.items()
            if v["total"] > 0 and (v["correct"] / v["total"]) < 0.5]
    if weak:
        report += f"\n⚠️ **Focus Areas:** {', '.join(weak)}\n"
        report += f"💡 `/practice {exam} {weak[0]}`\n"

    report += "\n📊 `/myprogress` — Full history"

    await client.send_message(chat_id, report)

    # ── Wrong Questions Detail ────────────────────────────────
    if wrong_questions:
        wtext = f"📝 **{name} — Mistakes Breakdown:**\n\n"
        for i, wq in enumerate(wrong_questions[:6], 1):
            src_line = ""
            if wq.get("exam_source"):
                src_line = f"\n   📅 _{wq['exam_source']}" + (f" ({wq['exam_year']})" if wq.get("exam_year") else "") + "_"
            sm = f"\n   ⚡ _{wq['short_method'][:100]}_" if wq.get("short_method") else ""
            wtext += (
                f"**{i}.** _{wq['q']}_\n"
                f"   ❌ You: `{wq['your_ans']}` ✅ Ans: `{wq['correct_ans']}`{src_line}\n"
                f"   💬 {wq['explanation'][:130]}{sm}\n\n"
            )
        if len(wrong_questions) > 6:
            wtext += f"_...and {len(wrong_questions)-6} more. Practice more to improve!_"
        await client.send_message(chat_id, wtext)


def _rank_estimate(exam: str, pct: float) -> str:
    bands = {
        "SSC":     [(90,"🥇 Top 1% — Rank: ~1–1,000"),
                    (80,"🥈 Top 5% — Rank: ~1K–5K"),
                    (70,"🥉 Top 15% — Safe Zone ✅"),
                    (60,"📊 Borderline — Near Cutoff"),
                    (50,"⚠️ Below Avg Cutoff"),
                    (0, "❌ Below Cutoff")],
        "UPSC":    [(70,"🥇 Excellent — IAS Territory"),
                    (60,"🥈 IPS/IFS Range"),
                    (50,"🥉 State Services"),
                    (40,"⚠️ Below UPSC Cutoff"),
                    (0, "❌ Needs Major Work")],
        "JEE":     [(85,"🥇 IIT Guaranteed"),
                    (70,"🥈 Top NIT Rank"),
                    (55,"🥉 NIT Possible"),
                    (40,"⚠️ Below NIT Cutoff"),
                    (0, "❌ Needs Improvement")],
        "RAILWAY": [(85,"🥇 Sure Selection 🎉"),
                    (75,"🥈 Very Good Chance"),
                    (65,"🥉 Document Verification Likely"),
                    (55,"⚠️ Borderline"),
                    (0, "❌ Below Cutoff")],
    }
    for threshold, msg in bands.get(exam, bands["SSC"]):
        if pct >= threshold:
            return f"┌ 🎯 **RANK ESTIMATE**\n└ {msg}"
    return "🎯 Keep practicing!"


def _grade(pct: float) -> str:
    if pct >= 90: return "A+ 🌟 Outstanding"
    if pct >= 80: return "A ⭐ Excellent"
    if pct >= 70: return "B+ 👍 Good"
    if pct >= 60: return "B 📚 Above Avg"
    if pct >= 50: return "C ⚠️ Average"
    return "D 💪 Keep Going"
