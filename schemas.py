from pydantic import BaseModel
from datetime import datetime


# -------------------------
# 📤 RESPONSE: Upload
# -------------------------

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int


# -------------------------
# 📄 RESPONSE: File detail
# -------------------------

class FileResponseModel(BaseModel):
    id: str
    filename: str
    size: int
    created_at: datetime


# -------------------------
# 📄 RESPONSE: List files
# -------------------------

class FileListItem(BaseModel):
    id: str
    filename: str
    size: int


class FileListResponse(BaseModel):
    files: list[FileListItem]


# -------------------------
# 🗑️ RESPONSE: Delete
# -------------------------

class DeleteResponse(BaseModel):
    detail: str