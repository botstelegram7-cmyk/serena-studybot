import asyncio, random
from datetime import datetime
from database import get_all_users, get_questions
from modules.question_gen import generate_pyq_batch
from modules.ai_helper import ask_ai


# ── AI GREETING GENERATOR ─────────────────────────────────────
async def _ai_morning(name: str, exam: str) -> str:
    prompt = f"""Write a short motivational morning message for a student named {name} preparing for {exam} exam.

Rules:
- Max 6 lines
- Hinglish (mix of Hindi and English)
- Start with a morning emoji
- Include 1 motivational line (not cliché)
- End with one actionable tip like /quick SSC 10
- Warm, energetic, personal tone
- Different every time — be creative
- Do NOT use "Good morning" as opening
- Name use karo warmly"""

    try:
        return await ask_ai(prompt)
    except Exception:
        return (f"🌅 **{name}, uth jao!**\n\n"
                f"Aaj ek aur din {exam} ke paas jaane ka mauka hai! 💪\n"
                f"_/quick {exam} 10_ se shuru karo!")


async def _ai_night(name: str, exam: str) -> str:
    prompt = f"""Write a short night message for a student named {name} preparing for {exam} exam.

Rules:
- Max 6 lines  
- Hinglish (mix of Hindi and English)
- Start with a night/moon emoji
- Give them relief, satisfaction, peace
- Remind them rest is part of preparation
- Gentle and calming tone — not motivational, just soothing
- End with a soft good night line
- Name use karo warmly
- Different every time — be creative"""

    try:
        return await ask_ai(prompt)
    except Exception:
        return (f"🌙 **{name}, aaj ka din complete!**\n\n"
                f"Jo pada woh brain store kar raha hai. 😌\n"
                f"Kal phir fresh mind se aayenge!\n\n"
                f"_Good night_ 💤")


# ── SEND GREETINGS ────────────────────────────────────────────
async def send_morning_greetings(bot):
    print(f"[Scheduler] Morning greetings — {datetime.utcnow()}", flush=True)
    users = await get_all_users()
    for user in users:
        uid  = user["uid"]
        name = user["name"].split()[0] if user.get("name") else "Student"
        exam = (user.get("exams") or ["SSC"])[0]
        try:
            msg = await _ai_morning(name, exam)
            await bot.send_message(uid, msg)
        except Exception as e:
            print(f"[Morning] {uid}: {e}")
        await asyncio.sleep(0.5)


async def send_night_messages(bot):
    print(f"[Scheduler] Night messages — {datetime.utcnow()}", flush=True)
    users = await get_all_users()
    for user in users:
        uid  = user["uid"]
        name = user["name"].split()[0] if user.get("name") else "Student"
        exam = (user.get("exams") or ["SSC"])[0]
        try:
            msg = await _ai_night(name, exam)
            await bot.send_message(uid, msg)
        except Exception as e:
            print(f"[Night] {uid}: {e}")
        await asyncio.sleep(0.5)


# ── DAILY QUIZ ────────────────────────────────────────────────
async def send_daily_quiz(bot):
    print(f"[Scheduler] Daily quiz — {datetime.utcnow()}", flush=True)
    users = await get_all_users()
    for user in users:
        uid  = user["uid"]
        name = user["name"]
        exam = (user.get("exams") or ["SSC"])[0]
        try:
            qs = await get_questions(exam, is_pyq=True, count=3)
            if len(qs) < 3:
                qs += await generate_pyq_batch(exam, "GK", count=3-len(qs))
            await bot.send_message(uid,
                f"📅 **Daily Quiz — {exam}** | 3 PYQ\n"
                f"_Roz solve karo, exam crack karo!_")
            for i, q in enumerate(qs[:3], 1):
                src = q.get("exam_source","")
                yr  = q.get("exam_year","")
                sl  = (f"📅 _{src}" + (f" ({yr})" if yr else "") + "_\n") if src else ""
                await bot.send_message(uid,
                    f"{sl}**Q{i}.** {q['question']}\n\n"
                    + "\n".join(q.get("options",[]))
                    + f"\n\n||✅ **{q.get('answer','?')}** — {q.get('explanation','')[:80]}||")
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[Quiz] {uid}: {e}")
        await asyncio.sleep(0.3)


# ── SCHEDULER ─────────────────────────────────────────────────
def _secs_until(h, m):
    now  = datetime.utcnow()
    return ((h - now.hour)*3600 + (m - now.minute)*60 - now.second) % 86400


async def daily_quiz_scheduler(bot):
    """
    06:00 AM IST = 00:30 UTC → AI Morning greeting
    08:00 AM IST = 02:30 UTC → Daily quiz
    09:30 PM IST = 16:00 UTC → AI Night message
    """
    print("[Scheduler] Started ✅", flush=True)

    async def run_at(h, m, fn, label):
        while True:
            secs = _secs_until(h, m)
            print(f"[Scheduler] {label} in {secs//3600}h {(secs%3600)//60}m", flush=True)
            await asyncio.sleep(secs)
            await fn(bot)
            await asyncio.sleep(61)

    await asyncio.gather(
        run_at(0, 30, send_morning_greetings, "Morning"),
        run_at(2, 30, send_daily_quiz,        "Daily Quiz"),
        run_at(16, 0, send_night_messages,    "Night"),
    )
