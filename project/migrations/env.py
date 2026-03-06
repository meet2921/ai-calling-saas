# Import your models so Alembic can detect them
from app.models.base import Base                   # 1. Define Base first
from app.models.user import User                   # 2. Then User
from app.models.organization import Organization   # 3. Then Organization
from app.models.campaigns import Campaign          # 4. Then Campaign
from app.models.lead import Lead 

import os
from dotenv import load_dotenv

from app.models.campaigns import Campaign

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
import asyncio

from app.core.config import settings
from app.models.campaigns import Campaign
from app.models.lead import Lead
from app.models.wallet import Wallet, WalletTransaction

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Load environment variables from .env
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use SYNC_DATABASE_URL from .env
    sqlalchemy_url = os.getenv("SYNC_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sqlalchemy_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()