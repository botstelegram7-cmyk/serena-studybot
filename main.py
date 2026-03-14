import asyncio
import threading
import os
from config import PORT

# ── FastAPI Web Server ────────────────────────────────────────
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn

web   = FastAPI()
START = datetime.utcnow()

@web.get("/")
async def root():
    return JSONResponse({"status": "running", "uptime": int((datetime.utcnow()-START).total_seconds())})

@web.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

@web.get("/ping")
async def ping():
    return "pong"


def run_web_server():
    """Uvicorn in its own thread with its own event loop — no conflict"""
    uvicorn.run(web, host="0.0.0.0", port=PORT, log_level="error")


# ── Bot ───────────────────────────────────────────────────────
async def run_bot():
    print("[1/4] Importing bot...", flush=True)
    from bot import app
    from modules.scheduler import daily_quiz_scheduler

    print("[2/4] Connecting to Telegram...", flush=True)
    await app.start()

    me = await app.get_me()
    print(f"[3/4] Bot connected: @{me.username}", flush=True)

    asyncio.create_task(daily_quiz_scheduler(app))
    print("[4/4] Scheduler started. Bot is LIVE! ✅", flush=True)

    await asyncio.Event().wait()   # Keep running forever


if __name__ == "__main__":
    print("=== SerenaStudyBot Starting ===", flush=True)

    # Start web server in background thread
    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()
    print(f"Web server started on port {PORT}", flush=True)

    # Run bot on main event loop
    asyncio.run(run_bot())
