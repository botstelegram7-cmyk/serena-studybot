from database import get_user, get_user_tests, get_leaderboard, users_col
from config import EXAMS


def _bar(pct: float, w: int = 10) -> str:
    f = int((pct/100)*w)
    return "█"*f + "░"*(w-f)


async def get_progress_report(uid: int, lang: str = "en") -> str:
    user = await get_user(uid)
    if not user:
        return "❌ User not found. Use /start first."

    name    = user["name"]
    t_tests = user.get("total_tests",0)
    t_qs    = user.get("total_questions",0)
    t_corr  = user.get("correct",0)
    stats   = user.get("subject_stats",{})
    o_acc   = round((t_corr/t_qs)*100,1) if t_qs>0 else 0

    tests = await get_user_tests(uid, 5)

    if lang == "hi":
        header = f"📊 **{name} की प्रगति रिपोर्ट**\n━━━━━━━━━━━━━━━━\n\n"
        labels = ("📝 टेस्ट:", "❓ प्रश्न:", "✅ सही:", "🎯 सटीकता:",
                  "📚 विषयवार:", "🕐 हाल के टेस्ट:", "⚠️ ध्यान दें:")
    elif lang == "bn":
        header = f"📊 **{name}-এর অগ্রগতি রিপোর্ট**\n━━━━━━━━━━━━━━━━\n\n"
        labels = ("📝 পরীক্ষা:", "❓ প্রশ্ন:", "✅ সঠিক:", "🎯 নির্ভুলতা:",
                  "📚 বিষয়ভিত্তিক:", "🕐 সাম্প্রতিক:", "⚠️ মনোযোগ:")
    else:
        header = f"📊 **{name}'s Progress Report**\n━━━━━━━━━━━━━━━━\n\n"
        labels = ("📝 Tests:", "❓ Questions:", "✅ Correct:", "🎯 Accuracy:",
                  "📚 Subject-wise:", "🕐 Recent Tests:", "⚠️ Focus:")

    text = (
        header +
        f"{labels[0]}    **{t_tests}**\n"
        f"{labels[1]} **{t_qs}**\n"
        f"{labels[2]}  **{t_corr}**\n"
        f"{labels[3]}  **{o_acc}%** `{_bar(o_acc)}`\n\n"
    )

    if stats:
        text += f"**{labels[4]}**\n"
        for subj, s in sorted(stats.items(), key=lambda x: x[1].get("total",0), reverse=True):
            tt = s.get("total",0)
            cc = s.get("correct",0)
            if tt == 0: continue
            pct = round((cc/tt)*100)
            st  = "✅" if pct>=70 else ("⚠️" if pct>=50 else "❌")
            text += f"{st} {subj}: **{pct}%** ({cc}/{tt}) `{_bar(pct,8)}`\n"

    if tests:
        text += f"\n**{labels[5]}**\n"
        for t in tests[:5]:
            d = t.get("completed_at")
            ds = d.strftime("%d %b") if d else "?"
            text += f"• {t['exam']} — **{t['percentage']}%** ({t['correct']}/{t['total']}) _{ds}_\n"

    weak = [s for s,v in stats.items()
            if v.get("total",0)>=5 and (v.get("correct",0)/v["total"])<0.5]
    if weak:
        text += f"\n**{labels[6]}** {', '.join(weak)}\n"

    return text


async def get_leaderboard_text(exam: str) -> str:
    board = await get_leaderboard(exam, 10)
    if not board:
        return f"📭 No {exam} scores yet. Be first!\n/test {exam}"

    text   = f"🏆 **{exam} Leaderboard — Top 10**\n━━━━━━━━━━━━━━\n\n"
    medals = ["🥇","🥈","🥉"] + ["🏅"]*7

    for i, entry in enumerate(board):
        uid   = entry["_id"]
        best  = round(entry["best_score"],1)
        att   = entry["attempts"]
        u     = await users_col.find_one({"uid": uid})
        uname = u["name"] if u else f"User{str(uid)[-4:]}"
        text += f"{medals[i]} **{uname}** — {best}% _{att} attempts_\n"

    return text
