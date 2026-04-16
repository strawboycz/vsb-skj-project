from sqlalchemy import String, Integer, ForeignKey
# Všimni si, že přidávám import datetime
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from sqlalchemy import String, Integer, ForeignKey, Boolean
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    files: Mapped[list["FileMetadata"]] = relationship(back_populates='owner')

class Bucket(Base):
    __tablename__ = 'buckets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Úkol 2: Pokročilé účtování
    current_storage_bytes: Mapped[int] = mapped_column(Integer, default=0)
    ingress_bytes: Mapped[int] = mapped_column(Integer, default=0)
    egress_bytes: Mapped[int] = mapped_column(Integer, default=0)
    internal_transfer_bytes: Mapped[int] = mapped_column(Integer, default=0)
    
    objects: Mapped[list["FileMetadata"]] = relationship(back_populates='bucket')

class FileMetadata(Base):
    __tablename__ = 'files'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    filename: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Úkol 3: Soft Delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    bucket_id: Mapped[int] = mapped_column(ForeignKey('buckets.id'), nullable=True)
    
    owner: Mapped["User"] = relationship(back_populates='files')
    bucket: Mapped["Bucket"] = relationship(back_populates='objects')