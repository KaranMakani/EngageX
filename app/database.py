from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# dependency for FastAPI routes
async def get_db():
    async with async_session() as session:
        yield session

# run this at startup to create tables
async def init_db():
    async with engine.begin() as conn:
        from app.models import User, Referral, Task, UserTask, ActivityLog
        await conn.run_sync(Base.metadata.create_all)
