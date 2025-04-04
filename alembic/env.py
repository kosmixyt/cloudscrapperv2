from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
import sys
import os
import asyncio

# Add the project root directory to the path so we can import our app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import our SQLAlchemy models and database configuration
from app.models import Base
from app.database import engine, SQLALCHEMY_DATABASE_URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set the database URL in the config
config.set_main_option("sqlalchemy.url", str(SQLALCHEMY_DATABASE_URL))

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def _run_async_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True
    )
    
    async with context.begin_transaction():
        await context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use AsyncEngine instead of regular Engine
    connectable = engine

    # Special handling for AsyncEngine
    if isinstance(connectable, AsyncEngine):
        asyncio.run(_do_run_migrations_async(connectable))
    else:
        # For synchronous engines (if ever used)
        do_run_migrations_sync(connectable)

async def _do_run_migrations_async(connectable):
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations_sync)

def do_run_migrations_sync(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True
    )
    
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()