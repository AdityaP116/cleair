from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cleair_dev.db")

# Standard synchronous SQLAlchemy engine with timeout for SQLite concurrent access
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"timeout": 15} if "sqlite" in DATABASE_URL else {}
)

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
