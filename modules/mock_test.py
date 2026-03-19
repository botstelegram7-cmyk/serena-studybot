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


# ── SESSION HELPERS (fresh db ref every call = no stale conn) ──
def _col():
    """Always get fresh collection — prevents MongoDB timeout issues"""
    return db["sessions_v2"]


async def _save_session(uid: int, data: dict):
    col = _col()
    # Ensure index exists for fast lookups
    try:
        await col.create_index("uid", unique=False)
    except Exception:
        pass
    await col.delete_many({"uid": uid})
    data["uid"]        = uid
    data["created_at"] = time.time()
    data["expire_at"]  = time.time() + 7200  # 2hr auto-expire hint
    await col.insert_one(data)
    print(f"[Session] Saved for uid={uid}, total_q={data.get('total',0)}", flush=True)


async def _get_session(uid: int):
    """Fetch with retry on connection error"""
    for attempt in range(3):
        try:
            return await _col().find_one({"uid": uid})
        except Exception as e:
            print(f"[Session] get attempt {attempt+1} failed: {e}")
            await asyncio.sleep(0.5)
    return None


async def _update_session(uid: int, updates: dict):
    for attempt in range(3):
        try:
            await _col().update_one({"uid": uid}, {"$set": updates})
            return
        except Exception as e:
            print(f"[Session] update attempt {attempt+1} failed: {e}")
            await asyncio.sleep(0.5)


async def _clear_session(uid: int):
    try:
        await _col().delete_many({"uid": uid})
    except Exception as e:
        print(f"[Session] clear failed: {e}")


# ── PROGRESS BARS ─────────────────────────────────────────────
def _bar(p, w=12):  return "█"*int(p/100*w) + "░"*(w-int(p/100*w))
def _mbar(p, w=8):  return "▓"*int(p/100*w) + "░"*(w-int(p/100*w))


# ── FETCH QUESTIONS ───────────────────────────────────────────
async def _fetch(exam, subject, count, difficulty):
    qs = []
    qs.extend(await get_pyq_questions(exam, subject, count))
    if len(qs) < count:
        qs.extend(await get_questions(exam, subject,
                   difficulty=difficulty, count=count-len(qs)))
    attempts = 0
    while len(qs) < count and attempts < 3:
        need  = count - len(qs)
        batch = min(need, 5)
        ai    = await generate_pyq_batch(exam, subject,
                 count=batch, difficulty=difficulty)
        if ai: qs.extend(ai)
        else:  attempts += 1
        await asyncio.sleep(0.2)
    return qs[:count]


async def _build(preset_key, exam, subject, section, difficulty, count):
    if subject:
        qs = await _fetch(exam, subject, count, difficulty)
        if section:
            filtered = [q for q in qs
                        if q.get("section","").lower() == section.lower()]
            if len(filtered) < count:
                extra = await generate_pyq_batch(
                    exam, subject, section, count-len(filtered), difficulty)
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
        f"🔄 **Building {exam} test...**\n"
        f"`⬜⬜⬜⬜⬜` `0%`\n⏱ ~15 sec"
    )

    # Animated loading
    for i, (bar, pct) in enumerate([
        ("🟦⬜⬜⬜⬜","20%"), ("🟦🟦⬜⬜⬜","40%"),
        ("🟦🟦🟦⬜⬜","60%"), ("🟦🟦🟦🟦⬜","80%")
    ]):
        await asyncio.sleep(1.5)
        try:
            await m.edit(f"🔄 **Building {exam} test...**\n`{bar}` `{pct}`")
        except Exception:
            pass

    qs = await _build(preset_key or "SSC_FULL", exam, subject,
                      section, difficulty, custom_count)

    if not qs:
        await m.edit("❌ Could not fetch questions. Try again.")
        return

    mk     = MARKS.get(exam, {"c":2,"w":-0.5})
    total  = len(qs)
    pyq_c  = sum(1 for q in qs if q.get("is_pyq", True))
    de     = {"Easy":"🟢","Medium":"🟡","Hard":"🔴","Extreme":"💀"}.get(difficulty,"🟡")

    # Save EVERYTHING in one document
    await _save_session(uid, {
        "exam":      exam,
        "subject":   subject,
        "total":     total,
        "current":   0,
        "answers":   {},
        "mc":        mk["c"],
        "mw":        mk["w"],
        "difficulty":difficulty,
        "lang":      lang,
        "questions": qs,       # ← all in one doc
        "start_t":   time.time(),
    })

    emins = max(1, (total*90)//60)
    await m.edit(
        f"╔════════════════════╗\n"
        f"║  🎯 **{exam} MOCK TEST**  ║\n"
        f"╚════════════════════╝\n\n"
        f"👤 **{name}** | {de} **{difficulty}**\n"
        f"❓ **{total} Q** | 📅 PYQ: **{pyq_c}**\n"
        f"✅ +{mk['c']} | ❌ {mk['w']} | ⏱ ~{emins}min\n\n"
        f"🟦🟦🟦🟦🟦 `100%`\n\n"
        f"🚀 Starting in **3s...**"
    )
    await asyncio.sleep(3)
    await _send_q(client, message.chat.id, uid)


# ── SEND QUESTION ─────────────────────────────────────────────
async def _send_q(client, chat_id, uid):
    sess = await _get_session(uid)
    if not sess:
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

    src_tag = f"📅 `{src}{' ('+yr+')' if yr else ''}`" if src else f"📅 `{sess['exam']} PYQ 2025`"

    header = (
        f"{src_tag}\n"
        f"**Q{idx+1}/{total}** {subj}" + (f"›{sec}" if sec else "") + f" {de}\n"
        f"`{_bar(pct)}` {pct}% | ⏳ ~{em}m{es}s\n\n"
        f"**{q['question']}**"
    )

    opts = q.get("options", [])
    ems  = ["🅰️","🅱️","🆎","🆑"]
    btns = []
    for i, opt in enumerate(opts[:4]):
        L    = chr(65+i)
        txt  = opt[2:].strip() if len(opt)>2 and opt[1] in ".)" else opt
        btns.append([InlineKeyboardButton(
            f"{ems[i]} {txt[:55]}",
            callback_data=f"tans_{uid}_{idx}_{L}"
        )])
    btns.append([InlineKeyboardButton(
        "⏭ Skip", callback_data=f"tans_{uid}_{idx}_SKIP"
    )])

    await client.send_message(chat_id, header,
                               reply_markup=InlineKeyboardMarkup(btns))


# ── PROCESS ANSWER ────────────────────────────────────────────
async def process_button_answer(client, uid, chat_id, q_idx, user_ans):
    sess = await _get_session(uid)
    if not sess:
        print(f"[Session] NOT FOUND for uid={uid}, q_idx={q_idx}", flush=True)
        await client.send_message(chat_id,
            "⚠️ Session timeout hua.\n/stoptest karo phir /test SSC se dobara shuru karo!")
        return
    print(f"[Session] Found for uid={uid}, current={sess.get('current',0)}", flush=True)

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

    await update_subject_stat(uid, q.get("subject","General"),
                               is_correct)
    await _update_session(uid, {"answers": answers, "current": nxt})

    # Feedback
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
        fb = (f"✅ **CORRECT!** `+{mc}`\n"
              + (f"⚡ _{sm[:140]}_" if sm else "") + src_l)
    else:
        opts = q.get("options",[])
        ct   = next((o[2:].strip() for o in opts
                     if o.strip().upper().startswith(correct_ans)),"")
        fb   = (f"❌ **WRONG** `{mw}` | Ans: **{correct_ans}**"
                + (f"\n✅ _{ct[:80]}_" if ct else "")
                + (f"\n💬 _{expl}_" if expl else "")
                + (f"\n⚡ _{sm[:110]}_" if sm else "")
                + src_l)

    pct_d = int((nxt/total)*100)
    fb   += f"\n`{_mbar(pct_d)}` {pct_d}% | **{left}** left"

    await client.send_message(chat_id, fb)

    if nxt >= total:
        await asyncio.sleep(2)
        await _finish(client, chat_id, uid)
    else:
        await asyncio.sleep(1.5)
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

    tqs  = len(qs)
    rs   = correct*mc + wrong*mw
    ms   = tqs*mc
    pct  = round(rs/ms*100,1) if ms else 0
    acc  = round(correct/(correct+wrong)*100,1) if (correct+wrong) else 0

    await save_completed_test(uid, {
        "exam":exam,"total":tqs,"correct":correct,"wrong":wrong,
        "skipped":skipped,"score":rs,"max_score":ms,
        "percentage":pct,"accuracy":acc,
        "subject_breakdown":sb,"time_taken":elapsed,
    })
    await _clear_session(uid)

    mins,secs = divmod(elapsed,60)
    grade  = ("A+🌟" if pct>=90 else "A⭐" if pct>=80 else
              "B+👍" if pct>=70 else "B📚" if pct>=60 else
              "C⚠️" if pct>=50 else "D💪")

    rank_bands = {
        "SSC":    [(90,"🥇 Top 1% ~1K rank"),(80,"🥈 Top 5%"),(70,"🥉 Safe Zone ✅"),
                   (60,"📊 Near Cutoff"),(0,"❌ Below Cutoff")],
        "UPSC":   [(70,"🥇 IAS Territory"),(60,"🥈 IPS/IFS"),(50,"🥉 State Svc"),(0,"❌ Below")],
        "JEE":    [(85,"🥇 IIT Sure"),(70,"🥈 Top NIT"),(55,"🥉 NIT Possible"),(0,"❌ Below")],
        "RAILWAY":[(85,"🥇 Sure✅"),(75,"🥈 High Chance"),(65,"🥉 DV Round"),(0,"❌ Below")],
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
        p2  = round(s["c"]/s["t"]*100) if s["t"] else 0
        st  = "✅" if p2>=70 else "⚠️" if p2>=40 else "❌"
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


# Public aliases for bot.py
send_next_question = _send_q
finish_test        = _finish
clear_session      = _clear_session
get_session        = _get_session
