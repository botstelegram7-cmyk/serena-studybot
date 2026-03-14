import asyncio
from datetime import datetime
from database import get_all_users, get_questions
from modules.question_gen import generate_pyq_batch


async def send_daily_quiz(bot):
    print(f"[DailyQuiz] Sending daily quiz — {datetime.utcnow()}")
    users = await get_all_users()

    for user in users:
        uid  = user["uid"]
        name = user["name"]
        lang = user.get("lang","en")
        exam = (user.get("exams") or ["SSC"])[0]

        try:
            qs = await get_questions(exam, is_pyq=True, count=5)
            if len(qs) < 5:
                qs += await generate_pyq_batch(exam, list({"SSC":["GK"],"UPSC":["Current Affairs"],"JEE":["Physics"],"RAILWAY":["GK"]}.get(exam,["GK"]))[0], count=5-len(qs))

            headers = {
                "en": f"🌅 **Good Morning, {name}!**\n📅 Daily Quiz ({exam}) — 5 Questions\n_Roz solve karo, exam crack karo!_ 💪",
                "hi": f"🌅 **शुभ प्रभात, {name}!**\n📅 दैनिक प्रश्नोत्तरी ({exam}) — 5 प्रश्न\n_रोज़ हल करो, परीक्षा पास करो!_ 💪",
                "bn": f"🌅 **শুভ সকাল, {name}!**\n📅 দৈনিক কুইজ ({exam}) — ৫টি প্রশ্ন\n_প্রতিদিন সমাধান করো!_ 💪",
            }
            await bot.send_message(uid, headers.get(lang, headers["en"]))

            for i, q in enumerate(qs[:5], 1):
                src  = q.get("exam_source","")
                yr   = q.get("exam_year","")
                src_line = (f"📅 _{src}" + (f" ({yr})" if yr else "") + "_\n") if src else ""
                qtext = (
                    f"{src_line}**Q{i}.** {q['question']}\n\n"
                    + "\n".join(q.get("options",[]))
                    + f"\n\n||✅ **{q.get('answer','?')}** — {q.get('explanation','')[:100]}||"
                )
                await bot.send_message(uid, qtext)
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[DailyQuiz] Failed {uid}: {e}")
        await asyncio.sleep(0.3)


async def daily_quiz_scheduler(bot):
    """Runs every day at 8:00 AM IST (2:30 AM UTC)"""
    while True:
        now = datetime.utcnow()
        th, tm = 2, 30
        secs = ((th - now.hour)*3600 + (tm - now.minute)*60 - now.second) % 86400
        print(f"[DailyQuiz] Next in {secs//3600}h {(secs%3600)//60}m")
        await asyncio.sleep(secs)
        await send_daily_quiz(bot)
        await asyncio.sleep(61)
