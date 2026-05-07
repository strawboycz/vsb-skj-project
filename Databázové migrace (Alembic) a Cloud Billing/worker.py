import asyncio
import websockets
import json
import numpy as np
from PIL import Image
import io
import traceback
import httpx

# ==========================================
# 1. SYNCHRONNÍ NUMPY LOGIKA (Běží ve vlákně)
# ==========================================
def process_image_sync(image_data, job_data: dict):
    """
    Tato funkce je CPU-bound. Nesmí obsahovat 'await'.
    Načte obrázek, provede maticovou magii a uloží ho.
    """
    # OPRAVA: Používáme image_data, nikoliv input_path!
    img = Image.open(image_data).convert("RGB") 
    img_array = np.array(img)
    
    op = job_data.get("operation")
    
    if op == "negative":
        # 1. Inverze barev (Vektorizace)
        new_array = 255 - img_array
        
    elif op == "flip":
        # 2. Horizontální překlopení (Slicing)
        new_array = img_array[:, ::-1, :]
        
    elif op == "crop":
        params = job_data.get("params", {})
        h, w, _ = img_array.shape
        
        # Bezpečné přetypování na integer (kdyby web poslal stringy)
        try:
            m_top = int(params.get("top", 0))
            m_bottom = int(params.get("bottom", 0))
            m_left = int(params.get("left", 0))
            m_right = int(params.get("right", 0))
            
            # TADY JE TEN KONTROLNÍ TISK
            print(f"[DEBUG] Crop hodnoty přijaté workerem: Top={m_top}, Bottom={m_bottom}, Left={m_left}, Right={m_right}")
            
        except (ValueError, TypeError):
            raise ValueError("Ořezové parametry musí být platná celá čísla.")
        
        # Výpočet cílových souřadnic (slicing)
        y_start = m_top
        y_end = h - m_bottom
        x_start = m_left
        x_end = w - m_right

        # Validace: Nesmíme uříznout víc, než obrázek má, ani jít do záporných hranic
        if m_top < 0 or m_bottom < 0 or m_left < 0 or m_right < 0:
             raise ValueError("Ořezové parametry nemohou být záporné.")
        if m_top + m_bottom >= h or m_left + m_right >= w:
             raise ValueError(f"Neplatný ořez. Obrázek {w}x{h} je příliš malý na ořezání o {m_left}+{m_right} a {m_top}+{m_bottom}.")
             
        if y_start >= y_end or x_start >= x_end:
            raise ValueError(f"Neplatný ořez. Obrázek {w}x{h} nelze oříznout o {m_left}+{m_right} šířky a {m_top}+{m_bottom} výšky.")
            
        new_array = img_array[y_start:y_end, x_start:x_end, :]
        
    elif op == "brightness":
        # 4. Zesvětlení (Přetypování a Saturace)
        try:
            val = int(job_data.get("params", {}).get("value", 50))
        except (ValueError, TypeError):
            raise ValueError("Hodnota jasu musí být celé číslo.")
        
        # Musíme převést na int16, jinak 250 + 50 přeteče na 44!
        temp_array = img_array.astype(np.int16)
        temp_array += val
        
        # Oříznutí hodnot mimo 0-255 a návrat na uint8
        new_array = np.clip(temp_array, 0, 255).astype(np.uint8)
        
    elif op == "grayscale":
        # 5. Černobílý filtr (Vážený průměr přes RGB kanály)
        r = img_array[:, :, 0]
        g = img_array[:, :, 1]
        b = img_array[:, :, 2]
        
        gray_2d = 0.299 * r + 0.587 * g + 0.114 * b
        new_array = gray_2d.astype(np.uint8)
        
    else:
        raise ValueError(f"Neznámá operace: {op}")

    # 3. Převod zpět a uložení do paměti (bez disku)
    new_img = Image.fromarray(new_array)
    output_buffer = io.BytesIO()
    new_img.save(output_buffer, format="JPEG") 
    output_buffer.seek(0) 
    return output_buffer


# ==========================================
# 2. ASYNCHRONNÍ WORKER SMYČKA (Event-Driven)
# ==========================================
async def worker_loop():
    broker_url = "ws://localhost:8000/broker/image.jobs"
    api_base_url = "http://localhost:8000"
    
    print("[*] Image Worker startuje a připojuje se k brokeru...")
    
    while True:
        try:
            async with websockets.connect(broker_url) as websocket:
                print("[*] Připojeno k tématu image.jobs. Čekám na práci...")
                
                while True:
                    message = await websocket.recv()
                    
                    try:
                        raw_data = json.loads(message)
                        message_id = raw_data.get("message_id") 
                        job_data = raw_data.get("payload", raw_data)
                    except json.JSONDecodeError:
                        continue
                        
                    image_id = job_data.get("image_id")
                    user_id = job_data.get("user_id")
                    bucket_id = job_data.get("bucket_id")
                    operation = job_data.get("operation")
                    
                    if not all([image_id, user_id, bucket_id]):
                        print("[-] Chybí potřebné parametry (image_id, user_id, bucket_id), přeskakuji.")
                        continue
                        
                    print(f"[>] Zpracovávám: {operation} na {image_id} (User: {user_id})...")
                    
                    status = "success"
                    error_msg = ""
                    new_file_id = None
                    
                    headers = {
                        "x-user-id": user_id,
                        "x-internal-source": "true" 
                    }
                    
                    try:
                        async with httpx.AsyncClient() as client:
                            # --- 1. STÁHNUTÍ OBRÁZKU DO PAMĚTI ---
                            dl_resp = await client.get(f"{api_base_url}/files/{image_id}", headers=headers)
                            if dl_resp.status_code not in [200, 201, 202]:
                                raise Exception(f"Chyba stahování: {dl_resp.status_code} - {dl_resp.text}")
                            
                            img_data = io.BytesIO(dl_resp.content)
                            
                            # --- 2. ZPRACOVÁNÍ V NUMPY ---
                            result_buffer = await asyncio.to_thread(process_image_sync, img_data, job_data)
                            
                            # --- 3. UPLOAD Z PAMĚTI ---
                            files = {"file": (f"{operation}_{image_id}.jpg", result_buffer, "image/jpeg")}
                            data = {"bucket_id": str(bucket_id)} # Pro jistotu převedeno na string pro Form data
                            up_resp = await client.post(f"{api_base_url}/files/upload", headers=headers, data=data, files=files)
                                
                            # OPRAVENO: Přidán kód 202 mezi povolené (úspěšné) stavy
                            if up_resp.status_code not in [200, 201, 202]:
                                raise Exception(f"Chyba nahrávání: {up_resp.status_code} - {up_resp.text}")
                                
                            # FastAPI nám při statusu 202 vrací {"detail": "...", "object_id": "uuid..."} nebo objekt
                            # Musíme se ujistit, že vytáhneme správné ID (id nebo object_id podle toho, co vrací main.py)
                            up_data = up_resp.json()
                            new_file_id = up_data.get("id") or up_data.get("object_id")
                            
                            print(f"[+] Úspěšně zpracováno a nahráno zpět jako: {new_file_id}")
                            
                    except ValueError as ve:
                        status = "error"
                        error_msg = str(ve)
                        print(f"[!] Chyba úlohy: {error_msg}")
                    except Exception as e:
                        status = "error"
                        error_msg = str(e)
                        print(f"[!] {error_msg}")
                        
                    # --- 4. ODESLÁNÍ VÝSLEDKU DO TÉMATU image.done ---
                    async with websockets.connect("ws://localhost:8000/broker/image.done") as done_ws:
                        result_msg = {
                            "action": "publish",
                            "payload": {
                                "original_image_id": image_id,
                                "new_image_id": new_file_id,
                                "status": status,
                                "operation": operation
                            }
                        }
                        if status == "error":
                            result_msg["payload"]["error"] = error_msg
                            
                        await done_ws.send(json.dumps(result_msg).encode("utf-8"))
                        print(f"[<] Odeslán status do image.done")
                        
                        await asyncio.sleep(0.25)
                    # --- 5. POTVRZENÍ BROKEROVI (ACK) ---
                    if message_id:
                        ack_msg = {
                            "action": "ack",
                            "message_id": message_id
                        }
                        await websocket.send(json.dumps(ack_msg).encode("utf-8"))
                        print(f"[<] Odesláno ACK pro message_id: {message_id}")

        except websockets.exceptions.ConnectionClosed:
            print("[!] Spojení s brokerem ztraceno. Zkouším se znovu připojit za 3s...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[!] Kritická chyba workeru: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(worker_loop())