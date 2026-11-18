"""Silnik bazy i zależność FastAPI zwracająca sesję."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    url = get_settings().sqlalchemy_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def get_db() -> Iterator[Session]:
    with sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session


def get_session_factory() -> sessionmaker[Session]:
    """Fabryka sesji dla zadań w tle (po odpowiedzi żądanie nie ma już swojej sesji)."""
    return sessionmaker(get_engine(), expire_on_commit=False)
