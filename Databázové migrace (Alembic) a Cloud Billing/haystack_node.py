import os
import asyncio
import websockets
import msgpack
import json
from fastapi import FastAPI, HTTPException, Response

# ==========================================
# KONFIGURACE HAYSTACK UZLU
# ==========================================
VOLUME_DIR = "volumes"
MAX_VOLUME_SIZE = 100 * 1024 * 1024  # 100 MB limit
BROKER_URL = "ws://localhost:8000/broker"

# Globální stav pro aktuální svazek
current_volume_id = 1

app = FastAPI(title="Haystack Storage Node")

# Ujistíme se, že složka pro svazky existuje
os.makedirs(VOLUME_DIR, exist_ok=True)

# ==========================================
# POMOCNÉ FUNKCE PRO ROTACI A ZÁPIS
# ==========================================
def get_active_volume_path() -> str:
    global current_volume_id
    
    file_path = os.path.join(VOLUME_DIR, f"volume_{current_volume_id}.dat")
    
    # Pokud soubor existuje, zkontrolujeme jeho velikost
    if os.path.exists(file_path):
        if os.path.getsize(file_path) >= MAX_VOLUME_SIZE:
            current_volume_id += 1  # Rotace svazku!
            file_path = os.path.join(VOLUME_DIR, f"volume_{current_volume_id}.dat")
            
    return file_path

async def publish_metadata_to_gateway(object_id: str, vol_id: int, offset: int, size: int):
    """Odešle metadata o uložení zpět Gatewayi přes téma storage.ack"""
    uri = f"{BROKER_URL}/storage.ack"
    
    # Payload, který říká Gatewayi: "Uložil jsem to, tady máš souřadnice!"
    metadata_payload = {
        "object_id": object_id,
        "volume_id": vol_id,
        "offset": offset,
        "size": size
    }
    
    publish_msg = {
        "action": "publish",
        "payload": metadata_payload
    }
    
    try:
        async with websockets.connect(uri, ping_interval=None) as ws:
            # Metadata posíláme pro jednoduchost v JSONu
            await ws.send(json.dumps(publish_msg).encode("utf-8"))
    except Exception as e:
        print(f"[!] Chyba při odesílání metadat do storage.ack: {e}")

# ==========================================
# BACKGROUND TASK: NASLOUCHÁNÍ BROKERU
# ==========================================
async def listen_to_broker():
    """Naslouchá na tématu storage.write a zapisuje příchozí fotky do svazku."""
    uri = f"{BROKER_URL}/storage.write"
    
    while True:
        try:
            print("[*] Haystack Node se připojuje k brokeru...")
            async with websockets.connect(uri, ping_interval=None) as websocket:
                print("[*] Haystack Node úspěšně připojen! Čekám na fotky k zápisu.")
                
                while True:
                    message = await websocket.recv()
                    
                    try:
                        data = msgpack.unpackb(message)
                    except:
                        data = json.loads(message)

                    if data.get("action") == "deliver":
                        message_id = data.get("message_id")
                        payload = data.get("payload", {})
                        
                        object_id = payload.get("object_id")
                        image_data = payload.get("image_data")
                        
                        # ROBUSTNÍ KONTROLA: Zpracujeme jen zprávy, co dávají smysl
                        if object_id and image_data:
                            
                            # Kdyby data přišla přes JSON (jako string), převedeme je na byty
                            if isinstance(image_data, str):
                                image_data = image_data.encode('utf-8')

                            active_file = get_active_volume_path()
                            vol_id = current_volume_id
                            
                            # Přejmenováno z 'f' na 'file_obj' pro absolutní jistotu
                            with open(active_file, "ab+") as file_obj:
                                offset = file_obj.tell()
                                file_obj.write(image_data)
                                size = len(image_data)
                                
                            print(f"[+] Uloženo! Vol: {vol_id}, Offset: {offset}, Size: {size}")
                            
                            ack_msg = msgpack.packb({"action": "ack", "message_id": message_id})
                            await websocket.send(ack_msg)
                            
                            await publish_metadata_to_gateway(object_id, vol_id, offset, size)
                        
                        else:
                            print(f"[?] Ignorována neplatná zpráva (Poison Pill): {message_id}")
                            ack_msg = msgpack.packb({"action": "ack", "message_id": message_id})
                            await websocket.send(ack_msg)
                            
        except websockets.exceptions.ConnectionClosed:
            print("[!] Spojení s brokerem ztraceno. Zkouším se připojit znovu...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[!] Kritická chyba v naslouchání: {e}")
            await asyncio.sleep(3)

# ==========================================
# FASTAPI LIFESPAN A ENDPOINTY
# ==========================================
@app.on_event("startup")
async def startup_event():
    # Spustíme naslouchání brokeru na pozadí, jakmile nastartuje server
    asyncio.create_task(listen_to_broker())

@app.get("/volume/{volume_id}/{offset}/{size}")
async def read_image(volume_id: int, offset: int, size: int):
    """Endpoint pro čtení fotky z obřího souboru podle souřadnic."""
    file_path = os.path.join(VOLUME_DIR, f"volume_{volume_id}.dat")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Svazek nenalezen")
        
    try:
        # Přečteme jen přesný výsek velkého souboru
        with open(file_path, "rb") as f:
            f.seek(offset)            # Skočí čtecí hlavou na začátek fotky
            data = f.read(size)       # Přečte přesně daný počet bajtů
            
        return Response(content=data, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))