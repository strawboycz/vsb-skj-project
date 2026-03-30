from pydantic import BaseModel
from datetime import datetime
from typing import List

# -------------------------
# Upload response
# -------------------------
class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int


# -------------------------
# File detail (pro seznam)
# -------------------------
class FileListItem(BaseModel):
    id: str
    filename: str
    size: int


class FileListResponse(BaseModel):
    files: List[FileListItem]


# -------------------------
# Delete response
# -------------------------
class DeleteResponse(BaseModel):
    detail: str


# -------------------------
# ORM mode (volitelný, pokud chceme přímo vracet SQLAlchemy objekty)
# -------------------------
class FileResponseModel(BaseModel):
    id: str
    filename: str
    size: int
    created_at: datetime

    class Config:
        orm_mode = True