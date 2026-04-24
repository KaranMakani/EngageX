# grab stuff from .env
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    # discord
    DISCORD_TOKEN: str = "mock-token"

    # database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/engagex"

    # n8n
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook"

    # openai / openrouter
    OPENAI_API_KEY: str = "mock-key"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"  # change to openrouter URL in .env

    # app
    APP_URL: str = "http://localhost:8000"
    BOT_PREFIX: str = "!"

settings = Settings()
