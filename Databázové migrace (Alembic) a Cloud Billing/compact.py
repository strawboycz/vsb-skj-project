import os
import requests
import time

# ==========================================
# KONFIGURACE KOMPAKTORU
# ==========================================
VOLUME_DIR = "volumes"
API_BASE_URL = "http://localhost:8000/admin"

def compact_volume(volume_id: int):
    print(f"[*] Zahajuji kompakci pro Volume {volume_id}...")
    
    old_file_path = os.path.join(VOLUME_DIR, f"volume_{volume_id}.dat")
    new_file_path = os.path.join(VOLUME_DIR, f"volume_{volume_id}_compacted.dat")
    
    if not os.path.exists(old_file_path):
        print(f"[-] Soubor {old_file_path} neexistuje, přeskočeno.")
        return

    # 1. Získání platných souborů ze S3 Gateway
    try:
        response = requests.get(f"{API_BASE_URL}/volume/{volume_id}/files")
        response.raise_for_status()
        valid_files = response.json().get("files", [])
    except Exception as e:
        print(f"[!] Nelze získat seznam souborů ze S3 Gateway: {e}")
        return

    if not valid_files:
        print(f"[*] Ve svazku nejsou žádné platné soubory. Můžeme ho celý smazat.")
        os.remove(old_file_path)
        return

    print(f"[*] Nalezeno {len(valid_files)} platných souborů ke kompakci.")

    # 2. Samotný proces defragmentace a přenosu dat
    try:
        with open(old_file_path, "rb") as old_file, open(new_file_path, "wb") as new_file:
            for file_meta in valid_files:
                file_id = file_meta["id"]
                old_offset = file_meta["offset"]
                size = file_meta["size"]
                
                # Zjištění nové pozice v kompaktním souboru
                new_offset = new_file.tell()
                
                # Přesun čtecí hlavy a zkopírování bloků bajtů
                old_file.seek(old_offset)
                data_chunk = old_file.read(size)
                new_file.write(data_chunk)
                
                # 3. Aktualizace nových souřadnic zpět do Gatewaye
                try:
                    relocate_payload = {
                        "new_volume_id": volume_id,
                        "new_offset": new_offset
                    }
                    reloc_resp = requests.patch(
                        f"{API_BASE_URL}/files/{file_id}/relocate", 
                        json=relocate_payload
                    )
                    reloc_resp.raise_for_status()
                    print(f"  [+] {file_id}: Úspěšně přesunut na offset {new_offset}")
                except Exception as e:
                    print(f"  [!] Selhala aktualizace DB pro {file_id}: {e}")
                    raise # Zastavíme to, jinak bychom ztratili přehled o souřadnicích
                    
        # 4. Provedení fyzické výměny svazků
        print(f"[*] Kompakce úspěšná, provádím prohození souborů...")
        os.replace(new_file_path, old_file_path) # Atomic operace (Smaže starý, přejmenuje nový)
        print(f"[+] Svazek {volume_id} je nyní zkompaktněn a připraven!")

    except Exception as e:
        print(f"[!] Došlo k chybě během defragmentace: {e}")
        # V případě chyby zkusíme smazat neúplný nový soubor, starý zůstává nedotčen
        if os.path.exists(new_file_path):
             os.remove(new_file_path)


if __name__ == "__main__":
    # Test spuštění (např. defragmentace svazku 1)
    compact_volume(1)