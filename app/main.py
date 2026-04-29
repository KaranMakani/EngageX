"""
EngageX - Intelligent Referral, Task & Engagement Engine

This is the main entry point. It starts both the FastAPI server
and the Discord bot together as a single process.

Run with: poetry run python -m app.main
"""
import asyncio
import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import init_db
from app.routes.api import router
from app.bot import bot, setup_slash_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("engagex")

# set API_ONLY=1 to skip the bot (useful for Railway deployment)
API_ONLY = os.getenv("API_ONLY", "0") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # create tables on first run
    await init_db()
    logger.info("Database tables ready")

    # start the Discord bot in the background (skip on Railway - bot runs locally)
    if not API_ONLY and settings.DISCORD_TOKEN != "mock-token":
        asyncio.create_task(_start_bot())
        logger.info("Discord bot starting...")
    else:
        logger.info("API-only mode - bot not started")

    yield

    # cleanup
    if not API_ONLY and not bot.is_closed():
        await bot.close()


app = FastAPI(
    title="EngageX API",
    description="Intelligent Referral, Task & Engagement Engine",
    version="0.1.0",
    lifespan=lifespan,
)

# register all routes
app.include_router(router, prefix="/api", tags=["engagex"])


async def _start_bot():
    """Start the Discord bot as a background task."""
    try:
        await bot.login(settings.DISCORD_TOKEN)
        await setup_slash_commands()
        await bot.connect()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")


# health check
@app.get("/")
async def root():
    return {"status": "running", "name": "EngageX"}


@app.get("/health")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
