import os
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends, Form
from fastapi.responses import FileResponse as FastAPIFileResponse
import aiofiles

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine, get_db
import models
import schemas

app = FastAPI(title="Mini Cloud Storage")
STORAGE_DIR = "storage"

# ==========================================
# ENDPOINTY PRO BUCKETY
# ==========================================

@app.post("/buckets/", response_model=schemas.BucketResponse)
async def create_bucket(bucket: schemas.BucketCreate, db: Session = Depends(get_db)):
    stmt = select(models.Bucket).where(models.Bucket.name == bucket.name)
    existing_bucket = db.execute(stmt).scalar_one_or_none()
    
    if existing_bucket:
        raise HTTPException(status_code=400, detail="Bucket s tímto názvem již existuje")
        
    new_bucket = models.Bucket(
        name=bucket.name,
        created_at=datetime.utcnow().isoformat()
    )
    
    db.add(new_bucket)
    db.commit()
    db.refresh(new_bucket)
    
    return new_bucket


@app.get("/buckets/{bucket_id}/objects/", response_model=schemas.FileListResponse)
async def list_bucket_objects(bucket_id: int, db: Session = Depends(get_db)):
    stmt_bucket = select(models.Bucket).where(models.Bucket.id == bucket_id)
    bucket = db.execute(stmt_bucket).scalar_one_or_none()
    
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket nenalezen")
        
    # SOFT DELETE FILTR: Vypisujeme jen nesmazané soubory
    stmt_files = select(models.FileMetadata).where(
        models.FileMetadata.bucket_id == bucket_id,
        models.FileMetadata.is_deleted == False
    )
    files = db.execute(stmt_files).scalars().all()
    
    return {"files": files}


@app.get("/buckets/{bucket_id}/billing/", response_model=schemas.BillingResponse)
async def get_bucket_billing(bucket_id: int, db: Session = Depends(get_db)):
    stmt = select(models.Bucket).where(models.Bucket.id == bucket_id)
    bucket = db.execute(stmt).scalar_one_or_none()
    
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket nenalezen")
        
    return {
        "bucket_id": bucket.id,
        "bucket_name": bucket.name,
        "current_storage_bytes": bucket.current_storage_bytes,
        "ingress_bytes": bucket.ingress_bytes,
        "egress_bytes": bucket.egress_bytes,
        "internal_transfer_bytes": bucket.internal_transfer_bytes
    }

# ==========================================
# ENDPOINTY PRO SOUBORY
# ==========================================

# 1. Upload
@app.post("/files/upload", response_model=schemas.FileResponse)
async def upload_file(
    file: UploadFile = File(...), 
    x_user_id: str = Header(...),
    bucket_id: int = Form(...),
    x_internal_source: bool = Header(False, description="True pro interní provoz"),
    db: Session = Depends(get_db)
):
    stmt_user = select(models.User).where(models.User.id == x_user_id)
    user = db.execute(stmt_user).scalar_one_or_none()
    
    if not user:
        user = models.User(id=x_user_id)
        db.add(user)
        db.commit()

    stmt_bucket = select(models.Bucket).where(models.Bucket.id == bucket_id)
    bucket = db.execute(stmt_bucket).scalar_one_or_none()
    
    if not bucket:
        raise HTTPException(status_code=404, detail="Zadaný bucket neexistuje")

    file_id = str(uuid.uuid4())
    user_dir = os.path.join(STORAGE_DIR, x_user_id)
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, file_id)
    
    file_size = 0
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        file_size = len(content)
        
    db_file = models.FileMetadata(
        id=file_id,
        filename=file.filename,
        path=file_path,
        size=file_size,
        created_at=datetime.utcnow().isoformat(),
        user_id=x_user_id,
        bucket_id=bucket.id,
        is_deleted=False
    )
    
    # ADVANCED BILLING: Rozlišení původu dat a přidání do storage
    bucket.current_storage_bytes += file_size
    if x_internal_source:
        bucket.internal_transfer_bytes += file_size
    else:
        bucket.ingress_bytes += file_size
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file


# 2. Stažení
@app.get("/files/{id}")
async def download_file(
    id: str, 
    x_user_id: str = Header(...), 
    x_internal_source: bool = Header(False, description="True pro interní provoz"),
    db: Session = Depends(get_db)
):
    # SOFT DELETE FILTR: Nedovolí stáhnout smazaný soubor
    stmt = select(models.FileMetadata).where(
        models.FileMetadata.id == id,
        models.FileMetadata.is_deleted == False
    )
    db_file = db.execute(stmt).scalar_one_or_none()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="Soubor nenalezen nebo byl přesunut do koše")
    
    if db_file.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup k tomuto souboru")
        
    if not os.path.exists(db_file.path):
        raise HTTPException(status_code=404, detail="Fyzický soubor nenalezen na disku")
        
    # ADVANCED BILLING: Stahování je Egress nebo Interní přenos
    if db_file.bucket_id:
        stmt_bucket = select(models.Bucket).where(models.Bucket.id == db_file.bucket_id)
        bucket = db.execute(stmt_bucket).scalar_one_or_none()
        if bucket:
            if x_internal_source:
                bucket.internal_transfer_bytes += db_file.size
            else:
                bucket.egress_bytes += db_file.size
            db.commit()
            
    return FastAPIFileResponse(path=db_file.path, filename=db_file.filename)


# 3. Smazání
@app.delete("/files/{id}", response_model=schemas.MessageResponse)
async def delete_file(id: str, x_user_id: str = Header(...), db: Session = Depends(get_db)):
    stmt = select(models.FileMetadata).where(
        models.FileMetadata.id == id,
        models.FileMetadata.is_deleted == False
    )
    db_file = db.execute(stmt).scalar_one_or_none()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="Soubor nenalezen nebo už je v koši")
        
    if db_file.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup k tomuto souboru")
        
    # Místo db.delete(db_file) použijeme SOFT DELETE
    db_file.is_deleted = True
    
    # Pozor: Při soft delete se 'current_storage_bytes' NESNÍŽÍ, protože data na serveru stále fyzicky leží.
    db.commit()
    
    return {"detail": f"Soubor {db_file.filename} byl přesunut do koše (Soft Delete)"}


# 4. Výpis všech
@app.get("/files", response_model=schemas.FileListResponse)
async def list_files(x_user_id: str = Header(...), db: Session = Depends(get_db)):
    # SOFT DELETE FILTR
    stmt = select(models.FileMetadata).where(
        models.FileMetadata.user_id == x_user_id,
        models.FileMetadata.is_deleted == False
    )
    user_files = db.execute(stmt).scalars().all()
    
    return {"files": user_files}