from pydantic import BaseModel, ConfigDict, Field
from typing import List, Any, Optional, Dict

# ==========================================
# MODELY PRO SOUBORY A BUCKETY
# ==========================================
class FileResponse(BaseModel):
    id: str
    filename: str
    size: int
    model_config = ConfigDict(from_attributes=True)

class FileListResponse(BaseModel):
    files: List[FileResponse]

class MessageResponse(BaseModel):
    detail: str

class BucketCreate(BaseModel):
    name: str

class BucketResponse(BaseModel):
    id: int
    name: str
    created_at: str
    model_config = ConfigDict(from_attributes=True)

class BillingResponse(BaseModel):
    bucket_id: int
    bucket_name: str
    current_storage_bytes: int
    ingress_bytes: int
    egress_bytes: int
    internal_transfer_bytes: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# MODELY PRO WEBSOCKET BROKERA
# ==========================================
class WSMessageBase(BaseModel):
    action: str

class WSPublishMessage(WSMessageBase):
    payload: Any

class WSAckMessage(WSMessageBase):
    message_id: str

class WSDeliverMessage(WSMessageBase):
    topic: str
    message_id: str
    payload: Any

# ==========================================
# MODELY PRO ZPRACOVÁNÍ OBRAZU
# ==========================================
class CropParams(BaseModel):
    top: int = Field(0, description="Počet pixelů k odříznutí shora")
    bottom: int = Field(0, description="Počet pixelů k odříznutí zdola")
    left: int = Field(0, description="Počet pixelů k odříznutí zleva")
    right: int = Field(0, description="Počet pixelů k odříznutí zprava")

class BrightnessParams(BaseModel):
    value: int = Field(50, description="Hodnota přičtená ke každému pixelu", le=255, ge=-255)

class ProcessImageRequest(BaseModel):
    operation: str = Field(..., description="Typ operace (negative, flip, crop, brightness, grayscale)")
    params: Optional[Dict[str, Any]] = None