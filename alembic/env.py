import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.common.db import Base  # Импортируем Base из вашего проекта


# Подтягиваем .env
from dotenv import load_dotenv
load_dotenv()  # читает .env из корня проекта

# Собираем DATABASE_URL из переменных
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
PG_DB = os.getenv("POSTGRES_DB", "postgres")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"

# Alembic config
config = context.config
# Прокидываем URL в alembic.ini -> env
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Логи Alembic
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = os.environ["DATABASE_URL"]
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = os.environ["DATABASE_URL"]
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
