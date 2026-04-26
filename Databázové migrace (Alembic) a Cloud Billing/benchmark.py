import asyncio
import websockets
import time
import json
import msgpack

"""
Úkol 3: Zátěžové testy a měření propustnosti (benchmarking)
"""

NUM_PUBLISHERS = 5
NUM_SUBSCRIBERS = 5
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
MESSAGES_PER_PUBLISHER = 100#00


TOTAL_MESSAGES_PER_SUB = NUM_PUBLISHERS * MESSAGES_PER_PUBLISHER  # 50,000
TOTAL_DELIVERED = TOTAL_MESSAGES_PER_SUB * NUM_SUBSCRIBERS        # 250,000

async def benchmark_subscriber(topic: str, data_format: str, ready_event: asyncio.Event, done_event: asyncio.Event, state: dict):
    uri = f"ws://localhost:8000/broker/{topic}"
    
    async with websockets.connect(uri) as websocket:
        state['connected_subs'] += 1
        
        # kdyz je 5 subscriberu pripojeni
        if state['connected_subs'] == NUM_SUBSCRIBERS:
            ready_event.set()
            
        # cekani na prijmuti vsech zprav
        for _ in range(TOTAL_MESSAGES_PER_SUB):
            msg = await websocket.recv()
            
            # dekodovani zprav
            if data_format == "json":
                parsed = json.loads(msg)
                ack = {"action": "ack", "message_id": parsed.get("message_id")}
                await websocket.send(json.dumps(ack).encode("utf-8"))
            elif data_format == "msgpack":
                parsed = msgpack.unpackb(msg)
                ack = {"action": "ack", "message_id": parsed.get("message_id")}
                await websocket.send(msgpack.packb(ack))

        state['finished_subs'] += 1
        # pokud byly prijaty veskere zpravy
        if state['finished_subs'] == NUM_SUBSCRIBERS:
            done_event.set()

async def benchmark_publisher(topic: str, data_format: str, ready_event: asyncio.Event, done_event: asyncio.Event):
    uri = f"ws://localhost:8000/broker/{topic}"
    
    # zprava
    dummy_data = {"action": "publish", "payload": {"temp": 22.5}}
    if data_format == "json":
        payload = json.dumps(dummy_data).encode("utf-8")
    elif data_format == "msgpack":
        payload = msgpack.packb(dummy_data)
       
    async with websockets.connect(uri) as websocket:
        
        # kos
        async def drain_inbox():
            try:
                while True:
                    await websocket.recv()
            except Exception:
                pass
                
        drain_task = asyncio.create_task(drain_inbox())
        
        # cekani na 5 pripojenych subscriberu
        await ready_event.wait()
        
        # odeslani zprav
        for _ in range(MESSAGES_PER_PUBLISHER):
            await websocket.send(payload)
            
        # cas at doposila vse nez se vypne
        await done_event.wait()
        drain_task.cancel()

async def run_test(data_format: str):
    # topic -> bud stress_test_json / stress_test_msgpack
    topic = f"stress_test_{data_format}"
    
    # sunchronizace
    ready_event = asyncio.Event()
    done_event = asyncio.Event()
    state = {'connected_subs': 0, 'finished_subs': 0}    
    
    print(f"Starting {data_format.upper()} benchmark...")
    
    # vytvareni tasku
    subs = [benchmark_subscriber(topic, data_format, ready_event, done_event, state) for _ in range(NUM_SUBSCRIBERS)]
    pubs = [benchmark_publisher(topic, data_format, ready_event, done_event) for _ in range(NUM_PUBLISHERS)]
    
    # counter
    start_time = time.perf_counter()
    
    # soubezne spusteni
    await asyncio.gather(*subs, *pubs)
    
    end_time = time.perf_counter()
    
    # vypocitani vysledku
    elapsed = end_time - start_time
    throughput = TOTAL_DELIVERED / elapsed
    
    print(f"  - Elapsed time: {elapsed:.2f} seconds")
    print(f"  - Throughput:   {throughput:,.0f} msgs/sec\n")
    
    return throughput

async def main():
    print("==========================================")
    print(f"  Broker Benchmark (Total: {TOTAL_DELIVERED:,} msgs)")
    print("==========================================\n")
    
    # spusteni obou testu
    throughput_json = await run_test("json")
    throughput_msgpack = await run_test("msgpack")
    
    # porovnani vysledku
    print("--- Final Conclusion ---")
    if throughput_msgpack > throughput_json:
        speedup = (throughput_msgpack / throughput_json - 1) * 100
        print(f"MessagePack was {speedup:.1f}% faster than JSON!")
    else:
        speedup = (throughput_json / throughput_msgpack - 1) * 100
        print(f"JSON was {speedup:.1f}% faster than MessagePack! (Unexpected)")

if __name__ == "__main__":
    asyncio.run(main())