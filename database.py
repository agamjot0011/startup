"""
WZDM LiveRecord - Database connection helpers.

Provides engine creation, session management, and Supabase client setup.
"""

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLAlchemy engine (connected to Supabase PostgreSQL)
# ---------------------------------------------------------------------------


def create_database_engine() -> Engine:
    """Create and return a SQLAlchemy engine pointed at Supabase."""
    database_url = settings.SUPABASE_URL

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 10,
            "application_name": "wzdm-liverecord-api",
        },
    )

    # Verify connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Supabase connection established")
    except Exception:
        logger.error("Failed to connect to Supabase", exc_info=True)
        raise

    return engine


engine = create_database_engine()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """Yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Check that the database is reachable."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


# ---------------------------------------------------------------------------
# Supabase client (for auth & storage, not for DB queries)
# ---------------------------------------------------------------------------

try:
    import supabase

    _supa_client = supabase.CreateClient(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY.get_secret_value(),
    )
    SUPA_CLIENT = _supa_client
except ImportError:
    logger.warning("supabase client not installed - auth endpoints will be limited")
    SUPA_CLIENT = None
except Exception:
    logger.exception("Failed to initialise Supabase client")
    SUPA_CLIENT = None
