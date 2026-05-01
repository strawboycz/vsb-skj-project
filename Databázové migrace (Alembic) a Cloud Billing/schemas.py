from pydantic import BaseModel, ConfigDict
from typing import List

# Model reprezentující jeden vrácený soubor
class FileResponse(BaseModel):
    id: str
    filename: str
    size: int

    # Toto řekne Pydanticu, aby uměl číst data přímo z ORM modelů (SQLAlchemy)
    model_config = ConfigDict(from_attributes=True)

# Model pro vrácení seznamu souborů
class FileListResponse(BaseModel):
    files: List[FileResponse]

# Model pro obecné textové odpovědi (např. po smazání)
class MessageResponse(BaseModel):
    detail: str

# --- NOVÉ MODELY PRO BUCKETY ---

# Model pro vstup od uživatele (když vytváří nový bucket, zadává jen jméno)
class BucketCreate(BaseModel):
    name: str

# Model pro výstup (co API vrátí po vytvoření bucketu)
class BucketResponse(BaseModel):
    id: int
    name: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

# Model pro vrácení stavu účtu za data (Pokročilý Billing)
class BillingResponse(BaseModel):
    bucket_id: int
    bucket_name: str
    current_storage_bytes: int
    # prichozi byty, byvaji zdarma
    ingress_bytes: int
    # odchozi byty, drahe
    egress_bytes: int
    # prenos v cloudu mezi S3, EC2
    internal_transfer_bytes: int

    model_config = ConfigDict(from_attributes=True)

from typing import Any, Optional

# --- NOVÉ MODELY PRO WEBSOCKET PROTOKOL (ÚKOL 5) ---
class WSMessageBase(BaseModel):
    action: str

class WSPublishMessage(WSMessageBase):
    payload: Any

class WSAckMessage(WSMessageBase):
    message_id: str

# Model pro zprávu, kterou Broker posílá Subscriberům
class WSDeliverMessage(WSMessageBase):
    topic: str
    message_id: str
    payload: Any

# --- MODELY PRO ZPRACOVÁNÍ OBRAZU (ÚKOL: Image Worker) ---
class ProcessImageRequest(BaseModel):
    operation: str
    params: Optional[dict] = None