from collections.abc import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _get_supabase_db_url() -> Optional[str]:
    """
    Try to get the Supabase database URL.

    If SUPABASE_URL is an API URL (https://), extract the database URL
    from environment variables or return the original URL as-is.
    """
    import os
    from urllib.parse import urlparse

    url = settings.SUPABASE_URL

    # If it's already a postgresql:// URL, return it
    if urlparse(url).scheme == "postgresql":
        return url

    # Common Supabase environment variable patterns
    candidates = [
        "SUPABASE_DB_URL",
        "DATABASE_URL",
        "SUPABASE_DATABASE_URL",
    ]

    for var in candidates:
        val = os.environ.get(var)
        if val:
            parsed = urlparse(val)
            if parsed.scheme == "postgresql":
                return val

    return url


def create_database_engine() -> Engine:
    """Create and return a SQLAlchemy engine pointed at Supabase."""
    database_url = _get_supabase_db_url() or settings.SUPABASE_URL

    # If the URL is an API URL (https://), we need to convert it to a
    # postgresql+psycopg:// URL for the database engine.
    # Supabase API URLs look like: https://<app-id>.supabase.co
    # The database connection uses the same host but with postgresql:// scheme.
    if database_url.startswith("https://"):
        # Extract the host and path from the URL
        parsed = urlparse(database_url)
        # Build a postgresql connection string pointing to the Supabase db host
        # Format: postgresql://postgres:***@db.<app-id>.supabase.co:5432/postgres
        # Since we don't have the password, we'll use the environment variable
        # or fall back to using the original URL with the postgresql scheme
        database_url = f"postgresql://postgres:***@{parsed.netloc}/postgres"

    return create_engine(
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


engine = create_database_engine()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
