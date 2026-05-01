import os
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse as FastAPIFileResponse
from fastapi.concurrency import run_in_threadpool
import json
import msgpack
import aiofiles
import ConnectionManager

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine, get_db
import models
import schemas

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mini Cloud Storage")

# --- POVOLENÍ CORS PRO REACT ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # V produkci by zde byla jen URL React aplikace
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
STORAGE_DIR = "storage"

# globalni instance ConnectionManagera
manager = ConnectionManager.ConnectionManager()

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

    # je soubor soucasti bucketu?
    if db_file.bucket_id:
        # najde radek kde je id stejne jako bucket id souboru
        stmt_bucket = select(models.Bucket).where(models.Bucket.id == db_file.bucket_id)
        bucket = db.execute(stmt_bucket).scalar_one_or_none()
        # pokud existuje (scalar_one_or_none() nevyhodi none)
        if bucket:
            # odecte velikost souboru, ktery se maze od hodnoty v current_storage_bytes odstavci
            bucket.current_storage_bytes -= db_file.size
    
    # ted uz se current_storage_bytes snizi
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



# ukol 5 -> pomocne funkce pro databazi
from sqlalchemy.orm import Session
from database import engine

def save_msg_to_db(message: models.QueuedMessage):
    with Session(engine) as db:
        db.add(message)
        db.commit()

def mark_msg_delivered_in_db(message_id: str):
    with Session(engine) as db:
        stmt = select(models.QueuedMessage).where(models.QueuedMessage.id == message_id)
        msg = db.execute(stmt).scalar_one_or_none()
        if msg:
            msg.is_delivered = True
            db.commit()

def get_undelivered_from_db(topic: str):
    with Session(engine) as db:
        stmt = select(models.QueuedMessage).where(
            models.QueuedMessage.topic == topic,
            models.QueuedMessage.is_delivered == False
        )
        msgs = db.execute(stmt).scalars().all()
        # Magie: Odpojíme zprávy od DB, aby nezařvaly chybu po zavření bloku 'with'
        db.expunge_all() 
        return msgs


@app.websocket("/broker/{topic}")
async def broker_endpoint(websocket: WebSocket, topic: str):  # <-- TADY SMAZÁNO 'db: Session = Depends(get_db)'
    await manager.connect(websocket, topic)

    undelivered = await run_in_threadpool(get_undelivered_from_db, topic)
    for msg in undelivered:
        try:
            # Zkusíme jako JSON
            original_dict = json.loads(msg.payload)
            inner_payload = original_dict.get("payload") # Vytáhneme pouze čistá data
            
            # Vytvoříme striktní objekt pomocí Pydantic modelu
            deliver_msg = schemas.WSDeliverMessage(
                action="deliver",
                topic=topic,
                message_id=msg.id,
                payload=inner_payload
            )
            out_msg = deliver_msg.model_dump_json().encode('utf-8')
            
        except Exception:
            # Pokud to selže, jde o MessagePack
            original_dict = msgpack.unpackb(msg.payload)
            inner_payload = original_dict.get("payload")
            
            deliver_msg = schemas.WSDeliverMessage(
                action="deliver",
                topic=topic,
                message_id=msg.id,
                payload=inner_payload
            )
            out_msg = msgpack.packb(deliver_msg.model_dump())
            
        await websocket.send_bytes(out_msg)

    try:
        while True:
            data = await websocket.receive_bytes()

            try:
                msg_dict = json.loads(data)
                is_json = True
            except:
                msg_dict = msgpack.unpackb(data)
                is_json = False

            # --- VALIDACE PYDANTIC MODELEM (ÚKOL 5) ---
            action = msg_dict.get("action")
            
            try:
                if action == "publish":
                    # Validujeme, že publish zpráva má správný formát
                    valid_msg = schemas.WSPublishMessage(**msg_dict)
                elif action == "ack":
                    # Validujeme, že ack zpráva obsahuje message_id
                    valid_msg = schemas.WSAckMessage(**msg_dict)
                else:
                    continue # Neznámá akce, ignorujeme
            except Exception as e:
                # Pokud zpráva neodpovídá Pydantic modelu, zahodíme ji
                continue

            if action == "publish":
                msg_id = str(uuid.uuid4())
                
                new_message = models.QueuedMessage(
                    id=msg_id, 
                    topic=topic,
                    payload=data # do DB ukládáme raw byty
                )
                
                await run_in_threadpool(save_msg_to_db, new_message)

                # SPRAVNÉ POUŽITÍ PYDANTICU: Vytvoříme bezpečný objekt pro odeslání
                deliver_msg = schemas.WSDeliverMessage(
                    action="deliver",
                    topic=topic,
                    message_id=msg_id,
                    payload=valid_msg.payload # Použijeme payload ze zvalidovaného objektu!
                )
                
                # Serializace čistého Pydantic objektu
                if is_json:
                    deliver_bytes = deliver_msg.model_dump_json().encode("utf-8")
                else:
                    deliver_bytes = msgpack.packb(deliver_msg.model_dump())

                await manager.broadcast(deliver_bytes, topic)

            elif action == "ack":
                msg_id = msg_dict.get("message_id")
                if msg_id:
                    await run_in_threadpool(mark_msg_delivered_in_db, msg_id)
                    
    except Exception:
        pass
    finally:
        manager.disconnect(websocket, topic)

# ==========================================
# ENDPOINT PRO ZPRACOVÁNÍ OBRAZU (S3 Gateway -> Broker)
# ==========================================
@app.post("/buckets/{bucket_id}/objects/{object_id}/process")
async def process_image(
    bucket_id: int, 
    object_id: str, 
    request: schemas.ProcessImageRequest,
    x_user_id: str = Header(...), # Přidáno pro autentizaci a cestu
    db: Session = Depends(get_db)
):
    # 1. Ověříme, že obrázek existuje a patří uživateli
    stmt = select(models.FileMetadata).where(
        models.FileMetadata.id == object_id,
        models.FileMetadata.bucket_id == bucket_id,
        models.FileMetadata.user_id == x_user_id,
        models.FileMetadata.is_deleted == False
    )
    db_file = db.execute(stmt).scalar_one_or_none()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="Obrázek nenalezen nebo k němu nemáte přístup")

    # 2. Vytvoříme payload pro Workera (PŘIDÁNO user_id)
    job_payload = {
        "operation": request.operation,
        "image_id": object_id, 
        "user_id": x_user_id,
        "bucket_id": bucket_id,
        "params": request.params
    }

    # 3. Uložíme zprávu do Durable Queues
    msg_id = str(uuid.uuid4())
    topic = "image.jobs"
    
    raw_publish_data = json.dumps({"action": "publish", "payload": job_payload}).encode("utf-8")
    
    new_message = models.QueuedMessage(
        id=msg_id,
        topic=topic,
        payload=raw_publish_data
    )
    await run_in_threadpool(save_msg_to_db, new_message)

    # 4. Odešleme zprávu Workerům
    deliver_msg = schemas.WSDeliverMessage(
        action="deliver",
        topic=topic,
        message_id=msg_id,
        payload=job_payload
    )
    deliver_bytes = deliver_msg.model_dump_json().encode("utf-8")
    
    await manager.broadcast(deliver_bytes, topic)

    return {"status": "processing_started"}