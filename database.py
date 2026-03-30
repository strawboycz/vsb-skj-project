from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Generator

# -------------------------
# ⚙️ KONFIGURACE DB
# -------------------------

DATABASE_URL = "sqlite:///./files.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # nutné pro SQLite
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# -------------------------
# 🧱 MODEL
# -------------------------

class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# -------------------------
# 🏗️ INIT DB
# -------------------------

def init_db():
    Base.metadata.create_all(bind=engine)


# -------------------------
# 🔌 DEPENDENCY (FastAPI)
# -------------------------

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# 📦 CRUD OPERACE
# -------------------------

def create_file(db: Session, file_data: dict) -> File:
    file = File(**file_data)
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_file(db: Session, file_id: str) -> File | None:
    return db.query(File).filter(File.id == file_id).first()


def delete_file(db: Session, file_id: str) -> File | None:
    file = get_file(db, file_id)
    if file:
        db.delete(file)
        db.commit()
    return file


def get_user_files(db: Session, user_id: str) -> list[File]:
    return db.query(File).filter(File.user_id == user_id).all()