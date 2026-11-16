"""Środowisko Alembic: adres bazy z konfiguracji aplikacji, metadane z modeli."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import get_settings
from app.db.models import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logging", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Adres można podać wprost (test migracji); domyślnie pochodzi z konfiguracji aplikacji.
url = config.get_main_option("sqlalchemy.url") or get_settings().sqlalchemy_url


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Indeksy pg_trgm tworzy migracja ręcznie i nie ma ich w modelach: nie porównujemy ich."""
    return not (type_ == "index" and name and name.endswith("_trgm"))


def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
