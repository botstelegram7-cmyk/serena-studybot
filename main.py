import asyncio, threading
from bot import app
from modules.scheduler import daily_quiz_scheduler
from config import PORT

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime

web   = FastAPI(title="SerenaStudyBot")
START = datetime.utcnow()


@web.get("/")
async def root():
    return JSONResponse({"status":"running","bot":"SerenaStudyBot",
                         "uptime":int((datetime.utcnow()-START).total_seconds())})
@web.get("/health")
async def health():
    return JSONResponse({"status":"ok","time":datetime.utcnow().isoformat()})


def run_web():
    uvicorn.run(web, host="0.0.0.0", port=PORT, log_level="warning")


async def main():
    print("🚀 SerenaStudyBot starting...")
    threading.Thread(target=run_web, daemon=True).start()
    print(f"✅ Web server → port {PORT}")

    await app.start()
    me = await app.get_me()
    print(f"✅ Bot: @{me.username}")

    asyncio.create_task(daily_quiz_scheduler(app))
    print("✅ Daily quiz: 8:00 AM IST")
    print("\n🎓 SerenaStudyBot is LIVE!\n")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
