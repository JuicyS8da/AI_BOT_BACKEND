import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "music_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL, echo=True)

# фабрика асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# базовый класс для моделей
Base = declarative_base()

# зависимость для FastAPI
async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Function to create tables (for initial setup, not for production use)
async def init_models():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # use with caution
        await conn.run_sync(Base.metadata.create_all)
        