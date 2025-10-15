import os
from alembic import context
from sqlalchemy import pool, create_engine
from logging.config import fileConfig
from app.common.db import Base

from dotenv import load_dotenv
load_dotenv()

config = context.config

# ВАЖНО: sync-URL (psycopg2), а не asyncpg
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
if not DATABASE_URL_SYNC:
    raise RuntimeError("DATABASE_URL_SYNC not set")

config.set_main_option("sqlalchemy.url", DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=DATABASE_URL_SYNC, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    engine = create_engine(DATABASE_URL_SYNC, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
