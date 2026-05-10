import pytest
import asyncio
import websockets
import json

@pytest.mark.asyncio
async def test_worker_processes_10_tasks():
    """
    Integrační test pro Image Worker (Sekvenční verze).
    Obchází limit SQLite zamykání tím, že na každou zprávu počká, než pošle další.
    """
    jobs_uri = "ws://localhost:8000/broker/image.jobs"
    done_uri = "ws://localhost:8000/broker/image.done"

    # Připojení na obě fronty
    async with websockets.connect(done_uri, ping_interval=None) as sub_ws:
        async with websockets.connect(jobs_uri, ping_interval=None) as pub_ws:

            print("\n[Test] Začínám sekvenční odesílání 10 úloh...")
            responses = []
            
            for i in range(1, 11):
                job_msg = {
                    "action": "publish",
                    "payload": {
                        "operation": "negative",
                        # POUŽITO REÁLNÉ ID Z TVOJÍ DATABÁZE
                        "image_id": "5a7bdcba-4b66-4c70-bd8d-a26148d44470", 
                        "user_id": "cloud_user_123",
                        "bucket_id": 1
                    }
                }
                
                # 1. Pošleme JEDNU úlohu (Odesíláme jako byty)
                await pub_ws.send(json.dumps(job_msg).encode("utf-8"))
                
                # 2. Okamžitě počkáme na její vyřízení (aby si databáze odpočinula)
                try:
                    response = await asyncio.wait_for(sub_ws.recv(), timeout=10.0)
                    response_dict = json.loads(response)
                    responses.append(response_dict)
                    
                    # 3. ÚKLID DB: Pošleme Brokerovi ACK, že jsme výsledek v testu přijali
                    msg_id = response_dict.get("message_id")
                    if msg_id:
                        ack_msg = {"action": "ack", "message_id": msg_id}
                        await sub_ws.send(json.dumps(ack_msg).encode("utf-8"))
                        
                    print(f"[Test] Úloha {i}/10 úspěšně vyřízena.")
                    
                except asyncio.TimeoutError:
                    pytest.fail(f"Timeout u úlohy {i}. Worker nestihl odpovědět.")

            # 4. Finální ověření testu
            assert len(responses) == 10
            for resp in responses:
                assert resp.get("payload", {}).get("operation") == "negative"
                assert "status" in resp.get("payload", {})
                
            print("[Test] Všech 10 zpráv projelo systémem čistě a bezpečně!")