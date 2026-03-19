import asyncio, time, random
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_pyq_questions, get_questions, save_completed_test,
    update_subject_stat, get_user, db
)
from modules.question_gen import generate_pyq_batch
from modules.quiz_apis    import fetch_external_questions
from config import EXAMS

MARKS = {
    "SSC":     {"c": 2,   "w": -0.5},
    "UPSC":    {"c": 2,   "w": -0.66},
    "JEE":     {"c": 4,   "w": -1},
    "RAILWAY": {"c": 1,   "w": -0.25},
}

PRESETS = {
    "SSC_FULL":     {"sections": {"Quant":25,"English":25,"Reasoning":25,"GK":25}},
    "UPSC_FULL":    {"sections": {"History":15,"Polity":20,"Geography":15,"Economy":15,"Science":10,"Current Affairs":25}},
    "JEE_FULL":     {"sections": {"Physics":25,"Chemistry":25,"Maths":25}},
    "RAILWAY_FULL": {"sections": {"Quant":30,"Reasoning":30,"GK":25,"General Science":15}},
}

# ── SESSION (in-memory + MongoDB backup) ─────────────────────
# Primary: Python dict (fast, reliable within same process)
# Backup: MongoDB (for persistence)
_SESSIONS: dict = {}   # uid → session dict


async def _save_session(uid: int, data: dict):
    data["uid"] = uid
    data["created_at"] = time.time()
    # Save to memory first (instant)
    _SESSIONS[uid] = data
    # Also save to MongoDB as backup
    try:
        col = db["sessions_v3"]
        await col.delete_many({"uid": uid})
        # Don't store full questions in MongoDB to avoid size issues
        mongo_data = {k: v for k, v in data.items() if k != "questions"}
        mongo_data["uid"] = uid
        await col.insert_one(mongo_data)
    except Exception as e:
        print(f"[Session] MongoDB backup failed (ok, using memory): {e}", flush=True)


async def _get_session(uid: int) -> dict | None:
    # Check memory first
    if uid in _SESSIONS:
        return _SESSIONS[uid]
    # Fallback to MongoDB (won't have questions, but session info)
    try:
        col = db["sessions_v3"]
        doc = await col.find_one({"uid": uid})
        return doc
    except Exception:
        return None


async def _update_session(uid: int, updates: dict):
    if uid in _SESSIONS:
        _SESSIONS[uid].update(updates)
    # Update MongoDB too
    try:
        col = db["sessions_v3"]
        await col.update_one({"uid": uid}, {"$set": updates})
    except Exception as e:
        print(f"[Session] MongoDB update failed: {e}", flush=True)


async def _clear_session(uid: int):
    _SESSIONS.pop(uid, None)
    try:
        await db["sessions_v3"].delete_many({"uid": uid})
    except Exception:
        pass


def _bar(p, w=12):  return "█"*int(p/100*w) + "░"*(w-int(p/100*w))
def _mbar(p, w=8):  return "▓"*int(p/100*w) + "░"*(w-int(p/100*w))


# ── FETCH QUESTIONS ───────────────────────────────────────────
async def _fetch(exam, subject, count, difficulty):
    qs = list(await get_pyq_questions(exam, subject, count))
    attempts = 0
    while len(qs) < count and attempts < 4:
        needed = count - len(qs)
        batch  = min(needed, 5)
        ai = await generate_pyq_batch(exam, subject, count=batch, difficulty=difficulty)
        if ai:
            qs.extend(ai)
        else:
            attempts += 1
        await asyncio.sleep(0.2)
    return qs[:count]


async def _build(preset_key, exam, subject, section, difficulty, count):
    if subject:
        qs = await _fetch(exam, subject, count, difficulty)
        if section:
            filtered = [q for q in qs if q.get("section","").lower() == section.lower()]
            if len(filtered) < count:
                extra = await generate_pyq_batch(exam, subject, section,
                                                  count-len(filtered), difficulty)
                filtered.extend(extra)
            qs = filtered
        return qs[:count]

    preset = PRESETS.get(preset_key)
    if not preset:
        return await _fetch(exam, "GK", count, difficulty)

    all_qs = []
    for subj, cnt in preset["sections"].items():
        all_qs.extend(await _fetch(exam, subj, cnt, difficulty))
    random.shuffle(all_qs)
    return all_qs


# ── START TEST ────────────────────────────────────────────────
async def start_mock_test(client, message: Message,
                           exam, preset_key=None,
                           subject=None, section=None,
                           difficulty="Medium", custom_count=10,
                           lang="en"):
    uid  = message.from_user.id
    name = message.from_user.first_name

    # Always clear first
    await _clear_session(uid)

    m = await message.reply(
        f"🔄 **Building {exam} test...**\n`⬜⬜⬜⬜⬜` `0%`"
    )

    # Animated loading
    for bar, pct in [("🟦⬜⬜⬜⬜","20%"),("🟦🟦⬜⬜⬜","40%"),
                     ("🟦🟦🟦⬜⬜","60%"),("🟦🟦🟦🟦⬜","80%")]:
        await asyncio.sleep(1.2)
        try: await m.edit(f"🔄 **Building {exam} test...**\n`{bar}` `{pct}`")
        except Exception: pass

    qs = await _build(preset_key or "SSC_FULL", exam, subject,
                      section, difficulty, custom_count)

    if not qs:
        await m.edit("❌ Questions fetch nahi ho sake. Dobara try karo.")
        return

    mk    = MARKS.get(exam, {"c":2,"w":-0.5})
    total = len(qs)
    pyqc  = sum(1 for q in qs if q.get("is_pyq", True))
    de    = {"Easy":"🟢","Medium":"🟡","Hard":"🔴","Extreme":"💀"}.get(difficulty,"🟡")
    emins = max(1, (total*90)//60)

    # Save to memory immediately
    session = {
        "exam":       exam,
        "subject":    subject,
        "total":      total,
        "current":    0,
        "answers":    {},
        "mc":         mk["c"],
        "mw":         mk["w"],
        "difficulty": difficulty,
        "lang":       lang,
        "questions":  qs,
        "start_t":    time.time(),
    }
    await _save_session(uid, session)

    # Verify session was saved
    verify = await _get_session(uid)
    if not verify:
        await m.edit("❌ Session save failed. Dobara try karo: /test SSC")
        return

    print(f"[Session] ✅ Saved uid={uid} total={total}", flush=True)

    await m.edit(
        f"╔════════════════════╗\n"
        f"║  🎯 **{exam} MOCK TEST**  ║\n"
        f"╚════════════════════╝\n\n"
        f"👤 **{name}** | {de} **{difficulty}**\n"
        f"❓ **{total} Q** | 📅 PYQ: **{pyqc}**\n"
        f"✅ +{mk['c']} | ❌ {mk['w']} | ⏱ ~{emins}min\n\n"
        f"`🟦🟦🟦🟦🟦` `100%`\n\n"
        f"🚀 **Starting in 3s...**"
    )
    await asyncio.sleep(3)
    await _send_q(client, message.chat.id, uid)


# ── SEND QUESTION AS QUIZ POLL ────────────────────────────────
async def _send_q(client, chat_id, uid):
    sess = await _get_session(uid)
    if not sess:
        print(f"[Session] ❌ NOT FOUND for uid={uid}", flush=True)
        await client.send_message(chat_id,
            "❌ Session lost. Please start again: /test SSC")
        return

    idx   = sess.get("current", 0)
    qs    = sess.get("questions", [])
    total = sess.get("total", len(qs))

    if idx >= total or idx >= len(qs):
        await _finish(client, chat_id, uid)
        return

    q    = qs[idx]
    subj = q.get("subject","General")
    sec  = q.get("section","")
    diff = q.get("difficulty","Medium")
    src  = q.get("exam_source","")
    yr   = q.get("exam_year","")
    de   = {"Easy":"🟢","Medium":"🟡","Hard":"🔴","Extreme":"💀"}.get(diff,"🟡")

    pct  = int((idx/total)*100)
    left = total - idx
    eta  = left * 90
    em, es = divmod(eta, 60)

    src_tag = f"📅 `{src}{(' ('+yr+')') if yr else ''}`" if src else f"📅 `{sess['exam']} PYQ 2025`"

    # Try Telegram native quiz poll first
    opts = q.get("options", [])
    # Clean options (remove "A. " prefix)
    clean_opts = []
    for opt in opts[:4]:
        txt = opt[2:].strip() if len(opt)>2 and opt[1] in ".)" else opt
        clean_opts.append(txt[:100])

    # Find correct answer index
    correct_ans = str(q.get("answer","A")).strip().upper()[:1]
    correct_idx = ord(correct_ans) - ord('A')
    correct_idx = max(0, min(correct_idx, len(clean_opts)-1))

    expl = q.get("explanation","")
    sm   = q.get("short_method","") or ""
    expl_text = (f"✅ {correct_ans}: {expl[:150]}"
                 + (f" | ⚡ {sm[:80]}" if sm else ""))[:200]

    q_header = (
        f"{src_tag}\n"
        f"Q{idx+1}/{total} | {subj}" + (f" › {sec}" if sec else "") + f" {de}\n"
        f"`{_bar(pct)}` {pct}% | ⏳ ~{em}m{es}s\n\n"
        f"{q['question']}"
    )

    try:
        # Native Telegram quiz poll — expires auto, shows answer!
        poll_msg = await client.send_poll(
            chat_id         = chat_id,
            question        = q_header[:255],
            options         = clean_opts,
            type            = "quiz",
            correct_option_id = correct_idx,
            explanation     = expl_text,
            is_anonymous    = False,
            open_period     = 60,  # 60 seconds per question
        )
        # Store poll_id → q_idx mapping in session
        poll_map = sess.get("poll_map", {})
        poll_map[str(poll_msg.id)] = idx  # string key for MongoDB
        await _update_session(uid, {"poll_map": poll_map})

        # After poll expires, auto-move to next
        asyncio.create_task(_wait_and_next(client, chat_id, uid, idx, 62))
        # Live countdown timer in separate message
        asyncio.create_task(_live_timer(client, chat_id, uid, idx, 60))

    except Exception as e:
        print(f"[Poll] Failed, using buttons: {e}", flush=True)
        await _send_buttons(client, chat_id, uid, q, idx, total, sess)



async def _live_timer(client, chat_id, uid, q_idx, seconds: int):
    """Live countdown timer shown below the poll"""
    timer_icons = ["🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚","🕛"]
    
    try:
        # Send initial timer message
        t_msg = await client.send_message(
            chat_id,
            f"⏱ **{seconds}s**  {timer_icons[0]}"
        )
    except Exception:
        return

    for remaining in range(seconds-1, -1, -1):
        await asyncio.sleep(1)
        # Check if question already answered
        sess = await _get_session(uid)
        if not sess or sess.get("current", 0) != q_idx:
            try: await t_msg.delete()
            except Exception: pass
            return
        # Update every 5 seconds to avoid flood
        if remaining % 5 == 0 or remaining <= 10:
            icon = timer_icons[remaining % 12]
            bar_filled = int((remaining / seconds) * 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            color = "🟢" if remaining > 30 else "🟡" if remaining > 10 else "🔴"
            try:
                await t_msg.edit(
                    f"{color} `{bar}` **{remaining}s**  {icon}"
                )
            except Exception:
                pass

    # Timer expired
    try:
        await t_msg.edit("⏰ **Time Up!**")
        await asyncio.sleep(1)
        await t_msg.delete()
    except Exception:
        pass


async def _wait_and_next(client, chat_id, uid, q_idx, wait_secs):
    """Wait for poll to expire then auto-move"""
    await asyncio.sleep(wait_secs)
    sess = await _get_session(uid)
    if not sess or sess.get("current", 0) != q_idx:
        return  # Already answered or session gone
    # Mark as skipped and move on
    answers = sess.get("answers", {})
    if str(q_idx) not in answers:
        answers[str(q_idx)] = "SKIPPED"
        await _update_session(uid, {
            "answers": answers,
            "current": q_idx + 1
        })
        # Send next
        if q_idx + 1 >= sess.get("total", 0):
            await _finish(client, chat_id, uid)
        else:
            await _send_q(client, chat_id, uid)


async def _send_buttons(client, chat_id, uid, q, idx, total, sess):
    """Fallback: inline buttons"""
    src  = q.get("exam_source","")
    yr   = q.get("exam_year","")
    diff = q.get("difficulty","Medium")
    subj = q.get("subject","")
    sec  = q.get("section","")
    de   = {"Easy":"🟢","Medium":"🟡","Hard":"🔴","Extreme":"💀"}.get(diff,"🟡")
    pct  = int((idx/total)*100)
    left = total - idx
    src_tag = f"📅 `{src}{(' ('+yr+')') if yr else ''}`" if src else ""

    header = (
        f"{src_tag}\n" if src_tag else ""
    ) + (
        f"**Q{idx+1}/{total}** | {subj}" + (f" › {sec}" if sec else "") + f" {de}\n"
        f"`{_bar(pct)}` {pct}% | ⏳ {left} left\n\n"
        f"**{q['question']}**"
    )

    opts = q.get("options", [])
    ems  = ["🅰️","🅱️","🆎","🆑"]
    btns = []
    for i, opt in enumerate(opts[:4]):
        L   = chr(65+i)
        txt = opt[2:].strip() if len(opt)>2 and opt[1] in ".)" else opt
        btns.append([InlineKeyboardButton(
            f"{ems[i]} {txt[:55]}",
            callback_data=f"tans_{uid}_{idx}_{L}"
        )])
    btns.append([InlineKeyboardButton(
        "⏭ Skip", callback_data=f"tans_{uid}_{idx}_SKIP"
    )])

    await client.send_message(chat_id, header,
                               reply_markup=InlineKeyboardMarkup(btns))


# ── PROCESS POLL ANSWER ───────────────────────────────────────
async def process_poll_answer(client, uid: int, poll_id: int, chosen_ids: list):
    """Handle native quiz poll answers — immediately move to next"""
    sess = await _get_session(uid)
    if not sess:
        return

    poll_map = sess.get("poll_map", {})
    q_idx = poll_map.get(str(poll_id)) or poll_map.get(poll_id)
    if q_idx is None:
        return

    # Prevent double processing
    answers = sess.get("answers", {})
    if str(q_idx) in answers:
        return  # Already answered

    qs = sess.get("questions", [])
    if q_idx >= len(qs):
        return

    q           = qs[q_idx]
    correct_ans = str(q.get("answer","A")).strip().upper()[:1]
    correct_idx = ord(correct_ans) - ord('A')

    if chosen_ids:
        chosen_letter = chr(65 + chosen_ids[0])
        is_correct    = chosen_ids[0] == correct_idx
    else:
        chosen_letter = "SKIPPED"
        is_correct    = False

    answers[str(q_idx)] = chosen_letter
    nxt = q_idx + 1

    await update_subject_stat(uid, q.get("subject","General"), is_correct)
    await _update_session(uid, {"answers": answers, "current": nxt})

    # ── Immediate next question (don't wait for timer) ─────
    await asyncio.sleep(1.5)   # Small delay to let Telegram show result
    sess = await _get_session(uid)
    if not sess:
        return  # Test was stopped
    if nxt >= sess.get("total", 0):
        await _finish(client, uid, uid)
    else:
        await _send_q(client, uid, uid)


# ── PROCESS BUTTON ANSWER ─────────────────────────────────────
async def process_button_answer(client, uid, chat_id, q_idx, user_ans):
    sess = await _get_session(uid)
    if not sess:
        # Test was stopped by user — silently ignore
        return

    # Check if already answered (double tap prevention)
    existing_ans = sess.get("answers", {})
    if str(q_idx) in existing_ans:
        return

    qs  = sess.get("questions", [])
    if q_idx >= len(qs):
        return

    q           = qs[q_idx]
    correct_ans = str(q.get("answer","")).strip().upper()[:1]
    is_skip     = user_ans == "SKIP"
    is_correct  = (not is_skip) and (user_ans == correct_ans)

    answers = sess.get("answers", {})
    answers[str(q_idx)] = "SKIPPED" if is_skip else user_ans
    nxt = q_idx + 1

    await update_subject_stat(uid, q.get("subject","General"), is_correct)
    await _update_session(uid, {"answers": answers, "current": nxt})

    total = sess.get("total", len(qs))
    left  = total - nxt
    mc    = sess.get("mc", 2)
    mw    = sess.get("mw", -0.5)
    expl  = q.get("explanation","")[:160]
    sm    = q.get("short_method","") or ""
    src   = q.get("exam_source","")
    yr    = q.get("exam_year","")
    src_l = (f"\n📅 _{src}" + (f" ({yr})" if yr else "") + "_") if src else ""

    if is_skip:
        fb = f"⏭ **Skipped** | Ans: **{correct_ans}**\n💬 _{expl}_"
    elif is_correct:
        fb = (f"✅ **CORRECT!** `+{mc}`"
              + (f"\n⚡ _{sm[:140]}_" if sm else "") + src_l)
    else:
        opts = q.get("options",[])
        ct   = next((o[2:].strip() for o in opts if o.strip().upper().startswith(correct_ans)),"")
        fb   = (f"❌ **WRONG** `{mw}` | Ans: **{correct_ans}**"
                + (f"\n✅ _{ct[:80]}_" if ct else "")
                + (f"\n💬 _{expl}_" if expl else "")
                + (f"\n⚡ _{sm[:110]}_" if sm else "")
                + src_l)

    pct_d = int((nxt/total)*100)
    fb   += f"\n`{_mbar(pct_d)}` {pct_d}% | **{left}** left"
    await client.send_message(chat_id, fb)

    if nxt >= total:
        await asyncio.sleep(1.5)
        await _finish(client, chat_id, uid)
    else:
        await asyncio.sleep(1.5)  # Anti-flood delay
        # Re-check session still exists (user may have stopped test)
        check = await _get_session(uid)
        if check:
            await _send_q(client, chat_id, uid)


# ── FINISH + ANALYSIS ─────────────────────────────────────────
async def _finish(client, chat_id, uid):
    sess = await _get_session(uid)
    if not sess:
        return

    user    = await get_user(uid)
    name    = user["name"] if user else "Student"
    qs      = sess.get("questions", [])
    answers = sess.get("answers", {})
    exam    = sess.get("exam","SSC")
    mc      = sess.get("mc", 2)
    mw      = sess.get("mw",-0.5)
    elapsed = int(time.time() - sess.get("start_t", time.time()))

    correct=wrong=skipped=0
    sb = {}
    wqs = []
    pyc=pyt=0

    for i, q in enumerate(qs):
        ca   = str(q.get("answer","")).strip().upper()[:1]
        ua   = answers.get(str(i),"SKIPPED")
        subj = q.get("subject","General")
        pyq  = q.get("is_pyq",True)
        sb.setdefault(subj, {"t":0,"c":0,"w":0})
        sb[subj]["t"] += 1
        if pyq: pyt += 1
        if ua=="SKIPPED": skipped+=1
        elif ua==ca:
            correct+=1; sb[subj]["c"]+=1
            if pyq: pyc+=1
        else:
            wrong+=1; sb[subj]["w"]+=1
            wqs.append({"q":q.get("question","")[:80],"ya":ua,"ca":ca,
                        "subj":subj,"exp":q.get("explanation","")[:140],
                        "sm":q.get("short_method",""),
                        "src":q.get("exam_source",""),"yr":q.get("exam_year","")})

    tqs = len(qs)
    rs  = correct*mc + wrong*mw
    ms  = tqs*mc
    pct = round(rs/ms*100,1) if ms else 0
    acc = round(correct/(correct+wrong)*100,1) if (correct+wrong) else 0

    await save_completed_test(uid, {
        "exam":exam,"total":tqs,"correct":correct,"wrong":wrong,
        "skipped":skipped,"score":rs,"max_score":ms,
        "percentage":pct,"accuracy":acc,
        "subject_breakdown":sb,"time_taken":elapsed,
    })
    await _clear_session(uid)

    mins,secs = divmod(elapsed,60)
    grade = ("A+🌟" if pct>=90 else "A⭐" if pct>=80 else
             "B+👍" if pct>=70 else "B📚" if pct>=60 else
             "C⚠️" if pct>=50 else "D💪")

    rank_bands = {
        "SSC":    [(90,"🥇 Top 1% ~1K rank"),(80,"🥈 Top 5%"),
                   (70,"🥉 Safe Zone ✅"),(60,"📊 Near Cutoff"),(0,"❌ Below Cutoff")],
        "UPSC":   [(70,"🥇 IAS Territory"),(60,"🥈 IPS/IFS"),
                   (50,"🥉 State Svc"),(0,"❌ Below Cutoff")],
        "JEE":    [(85,"🥇 IIT Sure"),(70,"🥈 Top NIT"),
                   (55,"🥉 NIT Possible"),(0,"❌ Needs Work")],
        "RAILWAY":[(85,"🥇 Sure ✅"),(75,"🥈 High Chance"),
                   (65,"🥉 DV Round"),(0,"❌ Below Cutoff")],
    }
    rank = next((m for t,m in rank_bands.get(exam,rank_bands["SSC"]) if pct>=t),"")

    rpt = (
        f"╔══════════════════════╗\n║  🏁 **TEST COMPLETE!**  ║\n╚══════════════════════╝\n\n"
        f"👤 **{name}** | 📋 {exam}\n"
        f"`{_bar(pct)}` **{pct}%** {grade}\n\n"
        f"✅ {correct} `+{correct*mc:.0f}` | ❌ {wrong} `{wrong*mw:.1f}` | ⏭ {skipped}\n"
        f"📈 **{rs:.1f}/{ms:.0f}** | 🎯 {acc}% | ⏱ {mins}m{secs}s\n"
    )
    if pyt:
        pp = round(pyc/pyt*100)
        rpt += f"📅 PYQ: {pyc}/{pyt} `{_mbar(pp)}` {pp}%\n"
    rpt += f"\n🎯 **{rank}**\n\n**📚 SUBJECT ANALYSIS**\n"
    for subj,s in sb.items():
        p2 = round(s["c"]/s["t"]*100) if s["t"] else 0
        st = "✅" if p2>=70 else "⚠️" if p2>=40 else "❌"
        rpt += f"{st} **{subj}**: {s['c']}/{s['t']} `{_mbar(p2)}` {p2}%\n"
    weak = [s for s,v in sb.items() if v["t"]>0 and v["c"]/v["t"]<0.5]
    if weak:
        rpt += f"\n⚠️ **Weak:** {', '.join(weak)}\n`/practice {exam} {weak[0]}`"
    rpt += "\n\n📊 `/myprogress`"
    await client.send_message(chat_id, rpt)

    if wqs:
        wt = f"📝 **{name} — Mistakes:**\n\n"
        for i,wq in enumerate(wqs[:5],1):
            sl = (f"\n📅 _{wq['src']}" + (f" ({wq['yr']})" if wq['yr'] else "") + "_") if wq['src'] else ""
            sm = (f"\n⚡ _{wq['sm'][:100]}_") if wq['sm'] else ""
            wt += f"**{i}.** _{wq['q']}_\n❌`{wq['ya']}`→✅`{wq['ca']}`\n💬{wq['exp'][:120]}{sm}{sl}\n\n"
        if len(wqs)>5:
            wt += f"_+{len(wqs)-5} more_"
        await client.send_message(chat_id, wt)


# Public aliases
send_next_question = _send_q
finish_test        = _finish
clear_session      = _clear_session
get_session        = _get_session
