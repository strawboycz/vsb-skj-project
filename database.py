# database.py
import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime

# -------------------------
# Konfigurace DB (SQLite)
# -------------------------
DB_FILE = "storage.db"
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# -------------------------
# SQLAlchemy model souboru
# -------------------------
class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    filename = Column(String)
    path = Column(String)
    size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# -------------------------
# Inicializace DB
# -------------------------
def init_db():
    Base.metadata.create_all(bind=engine)


# -------------------------
# Session dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# CRUD helper funkce
# -------------------------
def create_file(db: Session, file_data: dict):
    file_obj = File(**file_data)
    db.add(file_obj)
    db.commit()
    db.refresh(file_obj)
    return file_obj


def get_file(db: Session, file_id: str):
    return db.query(File).filter(File.id == file_id).first()


def get_user_files(db: Session, user_id: str):
    return db.query(File).filter(File.user_id == user_id).all()


def delete_file(db: Session, file_id: str):
    file_obj = get_file(db, file_id)
    if file_obj:
        db.delete(file_obj)
        db.commit()