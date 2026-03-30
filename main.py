# main.py
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import FileResponse
import aiofiles
from sqlalchemy.orm import Session

from database import init_db, get_db, create_file, get_file, get_user_files, delete_file
from schemas import FileUploadResponse, FileListResponse, FileListItem, DeleteResponse

app = FastAPI(title="Mini Cloud Storage")
STORAGE_DIR = "storage"

# -------------------------
# Inicializace DB
# -------------------------
init_db()


# -------------------------
# 1️⃣ Upload souboru
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

    file_obj = create_file(db, {
        "id": file_id,
        "user_id": x_user_id,
        "filename": file.filename,
        "path": file_path,
        "size": len(content),
        "created_at": datetime.utcnow()
    })

    return FileUploadResponse(
        id=file_obj.id,
        filename=file_obj.filename,
        size=file_obj.size
    )


# -------------------------
# 2️⃣ Výpis souborů uživatele
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
# 3️⃣ Smazání souboru
# -------------------------
@app.delete("/files/{file_id}", response_model=DeleteResponse)
async def delete_file_endpoint(
    file_id: str,
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    file_info = get_file(db, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")

    if file_info.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup")

    if os.path.exists(file_info.path):
        os.remove(file_info.path)

    delete_file(db, file_id)
    return DeleteResponse(detail=f"Soubor {file_info.filename} byl smazán")


# -------------------------
# 4️⃣ Stažení souboru
# -------------------------
@app.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    file_info = get_file(db, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")

    if file_info.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup")

    if not os.path.exists(file_info.path):
        raise HTTPException(status_code=404, detail="Fyzický soubor nenalezen na disku")

    return FileResponse(path=file_info.path, filename=file_info.filename)