import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Automatically create database directory if it does not exist
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Also support database/ if specified
if "sqlite:///./database/" in settings.DATABASE_URL:
    Path("database").mkdir(exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import all models to ensure they are registered on Base.metadata
    from app.models.user import User  # noqa
    from app.models.chat import Conversation, Message, LongTermMemory  # noqa

    Base.metadata.create_all(bind=engine)
