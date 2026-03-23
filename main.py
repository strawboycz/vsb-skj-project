import os
import json
import uuid
from datetime import datetime
# Přidali jsme import Header
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
import aiofiles
from fastapi.responses import FileResponse

app = FastAPI(title="Mini Cloud Storage")

# Konfigurace úložiště (MOCK_USER_ID je pryč)
STORAGE_DIR = "storage"
METADATA_FILE = "metadata.json"

def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return {}
    with open(METADATA_FILE, "r") as f:
        return json.load(f)

def save_metadata(data):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 1. Upload souboru s dynamickým uživatelem
@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...), x_user_id: str = Header(...)):
    file_id = str(uuid.uuid4())
    
    # Složka se teď jmenuje podle toho, co přijde v hlavičce
    user_dir = os.path.join(STORAGE_DIR, x_user_id)
    os.makedirs(user_dir, exist_ok=True)
    
    file_path = os.path.join(user_dir, file_id)
    
    file_size = 0
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        file_size = len(content)
        
    metadata = load_metadata()
    file_info = {
        "id": file_id,
        "user_id": x_user_id, # Uložíme si reálného uživatele do metadat
        "filename": file.filename,
        "path": file_path,
        "size": file_size,
        "created_at": datetime.utcnow().isoformat()
    }
    
    metadata[file_id] = file_info
    save_metadata(metadata)
    
    return {
        "id": file_id,
        "filename": file.filename,
        "size": file_size
    }

# 2. Stažení souboru (ověřuje uživatele)
@app.get("/files/{id}")
async def download_file(id: str, x_user_id: str = Header(...)):
    metadata = load_metadata()
    
    if id not in metadata:
        raise HTTPException(status_code=404, detail="Soubor nenalezen v metadatech")
    
    file_info = metadata[id]
    
    # Zkontrolujeme, jestli ID z hlavičky sedí s ID vlastníka v metadatech
    if file_info["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup k tomuto souboru")
        
    file_path = file_info["path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fyzický soubor nenalezen na disku")
        
    return FileResponse(path=file_path, filename=file_info["filename"])

# 3. Smazání souboru
@app.delete("/files/{id}")
async def delete_file(id: str, x_user_id: str = Header(...)):
    metadata = load_metadata()
    
    if id not in metadata:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
        
    file_info = metadata[id]
    
    # Opět kontrola přístupu
    if file_info["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Nemáte přístup k tomuto souboru")
        
    file_path = file_info["path"]
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    del metadata[id]
    save_metadata(metadata)
    
    return {"detail": f"Soubor {file_info['filename']} byl úspěšně smazán"}

# 4. Výpis všech souborů (jen pro daného uživatele)
@app.get("/files")
async def list_files(x_user_id: str = Header(...)):
    metadata = load_metadata()
    
    user_files = []
    for file_id, file_info in metadata.items():
        if file_info["user_id"] == x_user_id:
            user_files.append({
                "id": file_info["id"],
                "filename": file_info["filename"],
                "size": file_info["size"]
            })
            
    return {"files": user_files}