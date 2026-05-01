import asyncio
import websockets
import json
import numpy as np
from PIL import Image
import io
import os
import traceback
import httpx

# ==========================================
# 1. SYNCHRONNÍ NUMPY LOGIKA (Běží ve vlákně)
# ==========================================
def process_image_sync(input_path: str, output_path: str, job_data: dict):
    """
    Tato funkce je CPU-bound. Nesmí obsahovat 'await'.
    Načte obrázek, provede maticovou magii a uloží ho.
    """
    # 1. Načtení obrázku do NumPy
    img = Image.open(input_path).convert("RGB") # Pojistka, že máme 3 kanály
    img_array = np.array(img)
    
    op = job_data.get("operation")
    
    if op == "negative":
        # 1. Inverze barev (Vektorizace)
        new_array = 255 - img_array
        
    elif op == "flip":
        # 2. Horizontální překlopení (Slicing)
        new_array = img_array[:, ::-1, :]
        
    elif op == "crop":
        # Parametry nyní chápeme jako OKRAJE (kolik uříznout z každé strany)
        params = job_data.get("params", {})
        h, w, _ = img_array.shape
        
        # Kolik pixelů uříznout z dané strany (výchozí 0)
        m_top = params.get("top", 0)
        m_bottom = params.get("bottom", 0)
        m_left = params.get("left", 0)
        m_right = params.get("right", 0)
        
        # Výpočet cílových souřadnic (slicing)
        y_start = m_top
        y_end = h - m_bottom
        x_start = m_left
        x_end = w - m_right
        
        # Validace: Nesmíme uříznout víc, než obrázek má
        if y_start >= y_end or x_start >= x_end:
            raise ValueError(f"Neplatný ořez. Obrázek {w}x{h} nelze oříznout o {m_left}+{m_right} šířky a {m_top}+{m_bottom} výšky.")
            
        new_array = img_array[y_start:y_end, x_start:x_end, :]
        
    elif op == "brightness":
        # 4. Zesvětlení (Přetypování a Saturace)
        val = job_data.get("params", {}).get("value", 50)
        
        # Musíme převést na int16, jinak 250 + 50 přeteče na 44!
        temp_array = img_array.astype(np.int16)
        temp_array += val
        
        # Oříznutí hodnot mimo 0-255 a návrat na uint8
        new_array = np.clip(temp_array, 0, 255).astype(np.uint8)
        
    elif op == "grayscale":
        # 5. Černobílý filtr (Vážený průměr přes RGB kanály)
        # R = [:,:,0], G = [:,:,1], B = [:,:,2]
        r = img_array[:, :, 0]
        g = img_array[:, :, 1]
        b = img_array[:, :, 2]
        
        gray_2d = 0.299 * r + 0.587 * g + 0.114 * b
        new_array = gray_2d.astype(np.uint8)
        # Výsledkem je 2D matice, Pillow ji umí uložit jako "L" mód (grayscale)
        
    else:
        raise ValueError(f"Neznámá operace: {op}")

    # 3. Převod zpět a uložení
    new_img = Image.fromarray(new_array)
    new_img.save(output_path)
    return True


# ==========================================
# 2. ASYNCHRONNÍ WORKER SMYČKA (Event-Driven)
# ==========================================

TEMP_DIR = "worker_temp"
os.makedirs(TEMP_DIR, exist_ok=True)


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
                        
                    input_path = os.path.join(TEMP_DIR, f"in_{image_id}")
                    output_path = os.path.join(TEMP_DIR, f"out_{image_id}.jpg")
                    
                    print(f"[>] Zpracovávám: {operation} na {image_id} (User: {user_id})...")
                    
                    status = "success"
                    error_msg = ""
                    new_file_id = None
                    
                    # Společné hlavičky pro interní komunikaci
                    headers = {
                        "x-user-id": user_id,
                        "x-internal-source": "true" # Flag pro interní billing
                    }
                    
                    try:
                        async with httpx.AsyncClient() as client:
                            # --- 1. STÁHNUTÍ OBRÁZKU DO PAMĚTI (GET) ---
                            dl_resp = await client.get(f"{api_base_url}/files/{image_id}", headers=headers)
                            if dl_resp.status_code != 200:
                                raise Exception(f"Chyba stahování: {dl_resp.status_code} - {dl_resp.text}")
                            
                            # OPRAVA: Přečteme obrázek přímo z paměti pomocí io.BytesIO
                            img_data = io.BytesIO(dl_resp.content)
                            
                            # --- 2. ZPRACOVÁNÍ V NUMPY (Thread) ---
                            # Funkce process_image_sync si s io.BytesIO poradí místo cesty k souboru!
                            await asyncio.to_thread(process_image_sync, img_data, output_path, job_data)
                            
                            # --- 3. UPLOAD NOVÉHO OBRÁZKU (POST) ---
                            with open(output_path, "rb") as f:
                                # Tady už musíme simulovat jméno s koncovkou pro nahrávání přes API
                                files = {"file": (f"{operation}_{image_id}.jpg", f, "image/jpeg")}
                                data = {"bucket_id": bucket_id}
                                up_resp = await client.post(f"{api_base_url}/files/upload", headers=headers, data=data, files=files)
                                
                                if up_resp.status_code != 200:
                                    raise Exception(f"Chyba nahrávání: {up_resp.status_code} - {up_resp.text}")
                                
                                new_file_id = up_resp.json().get("id")

                            print(f"[+] Úspěšně zpracováno a nahráno zpět jako: {new_file_id}")
                            
                    except ValueError as ve:
                        status = "error"
                        error_msg = str(ve)
                        print(f"[!] Chyba úlohy: {error_msg}")
                    except Exception as e:
                        status = "error"
                        error_msg = str(e)
                        print(f"[!] {error_msg}")
                        
                    # Úklid dočasných souborů, abychom nezaplnili disk
                    if os.path.exists(input_path): os.remove(input_path)
                    if os.path.exists(output_path): os.remove(output_path)
                        
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