import threading

from sqlalchemy import Engine, create_engine

_engine: Engine | None = None
_engine_lock = threading.Lock()


def get_postgres_engine(settings) -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_engine(
                    settings.POSTGRES_URL,
                    pool_size=settings.POSTGRES_POOL_SIZE,
                    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
                    pool_pre_ping=True,
                    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
                )
    return _engine


def dispose_postgres_engine() -> None:
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
