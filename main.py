import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import aiofiles

from schemas import (
    FileUploadResponse,
    FileListResponse,
    FileListItem,
    DeleteResponse
)



from database import (
    get_db,
    init_db,
    create_file,
    get_file,
    delete_file,
    get_user_files
)

# -------------------------
# ⚙️ APP + LIFESPAN
# -------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Mini Cloud Storage",
    lifespan=lifespan
)

STORAGE_DIR = "storage"


# -------------------------
# 📤 UPLOAD
# -------------------------

@app.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    file_id = str(uuid.uuid4())

    user_dir = os.path.join(STORAGE_DIR, x_user_id)
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, file_id)

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    create_file(db, {
        "id": file_id,
        "user_id": x_user_id,
        "filename": file.filename,
        "path": file_path,
        "size": len(content),
        "created_at": datetime.utcnow()
    })

    return FileUploadResponse(
        id=file_id,
        filename=file.filename,
        size=len(content)
    )


# -------------------------
# 📥 DOWNLOAD
# -------------------------

@app.get("/files", response_model=FileListResponse)
async def list_files(
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    files = get_user_files(db, x_user_id)

    return FileListResponse(
        files=[
            FileListItem(
                id=f.id,
                filename=f.filename,
                size=f.size
            )
            for f in files
        ]
    )


# -------------------------
# 🗑️ DELETE
# -------------------------

@app.delete("/files/{id}", response_model=DeleteResponse)
async def delete_file_endpoint(
    id: str,
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    file_info = get_file(db, id)

    if not file_info:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")

    if file_info.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup")

    if os.path.exists(file_info.path):
        os.remove(file_info.path)

    delete_file(db, id)

    return DeleteResponse(
        detail=f"Soubor {file_info.filename} byl smazán"
    )