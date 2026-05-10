import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so Alembic can detect them
from app.models.user import Base, User  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.product import Section, Product  # noqa: F401
from app.models.sync_job import SyncJob  # noqa: F401
from app.models.visual_brief import VisualBrief  # noqa: F401
from app.models.settings import GlobalSettings, KeywordMapping  # noqa: F401
from app.models.banner import Banner  # noqa: F401
from app.models.template import Template  # noqa: F401
from app.models.theme import Theme  # noqa: F401
from app.models.manual_override import ManualOverride  # noqa: F401
from app.models.text_override import TextOverride  # noqa: F401
from app.models.snapshot import Snapshot  # noqa: F401
from app.models.user_preference import UserPreference  # noqa: F401
from app.models.review_token import ReviewToken  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.approval_event import ApprovalEvent  # noqa: F401
from app.models.sheet_version import SheetVersion, SheetVersionRow  # noqa: F401
from app.config import settings

config = context.config

# Override the sqlalchemy.url from alembic.ini with the one from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

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


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
