import asyncio
from bot import app
from modules.scheduler import daily_quiz_scheduler
from config import PORT

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn

web   = FastAPI(title="SerenaStudyBot")
START = datetime.utcnow()


@web.get("/")
async def root():
    return JSONResponse({"status": "running", "bot": "SerenaStudyBot",
                         "uptime": int((datetime.utcnow()-START).total_seconds())})

@web.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

@web.get("/ping")
async def ping():
    return JSONResponse({"ping": "pong"})


async def start_web():
    """Run uvicorn on SAME event loop as pyrogram — no threading conflict!"""
    config = uvicorn.Config(
        app   = web,
        host  = "0.0.0.0",
        port  = PORT,
        loop  = "none",   # Use existing event loop
        log_level = "warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    print("🚀 SerenaStudyBot starting...")

    # Run BOTH on same event loop — no conflict!
    await asyncio.gather(
        start_web(),
        start_bot(),
    )


async def start_bot():
    await asyncio.sleep(1)  # Let web server start first
    await app.start()
    me = await app.get_me()
    print(f"✅ Bot @{me.username} is LIVE!")
    asyncio.create_task(daily_quiz_scheduler(app))
    print("✅ Daily quiz scheduler started")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
