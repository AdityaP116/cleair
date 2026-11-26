from sqlalchemy import create_engine, event, Engine, text
from sqlalchemy.orm import sessionmaker, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cleair_dev.db")
IS_SQLITE = "sqlite" in DATABASE_URL

engine_kwargs = {
    "echo": False,
    "future": True,
    "connect_args": {"timeout": 15} if IS_SQLITE else {"connect_timeout": 5},
}

if not IS_SQLITE:
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

def check_db_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# Enforce foreign key constraints in SQLite
if "sqlite" in DATABASE_URL:
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
