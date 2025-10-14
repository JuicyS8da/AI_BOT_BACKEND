import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from app.common.db import Base  # ваша metadata
from dotenv import load_dotenv

load_dotenv()  # .env из корня

config = context.config

# 1) Берём sync-URL, либо конвертируем из async
url_sync = os.getenv("DATABASE_URL_SYNC")
if not url_sync:
    url_async = os.getenv("DATABASE_URL")
    if not url_async:
        raise RuntimeError("Neither DATABASE_URL_SYNC nor DATABASE_URL is set")
    # простая конвертация драйвера
    url_sync = url_async.replace("+asyncpg", "+psycopg2")

# Прокидываем в alembic.ini (на случай если там пусто)
config.set_main_option("sqlalchemy.url", url_sync)

# Логи Alembic
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=url_sync,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(url_sync, poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
