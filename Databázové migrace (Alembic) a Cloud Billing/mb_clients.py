import asyncio
import websockets
# pro parsovani CL argumentu
import argparse
import json
import msgpack

"""
Úkol 2: Klient a podpora více formátů zpráv
"""

async def subscribe(topic: str, data_format: str):
    uri = f"ws://localhost:8000/broker/{topic}"

    # pripojeni k brokeru
    async with websockets.connect(uri, ping_interval=None) as websocket:
        print(f"[*] Subscribed to '{topic}' using {data_format}. Waiting for message.")

        while True:
            # cekani na zpravu
            message = await websocket.recv()

            # dekodovani
            if data_format == "json":
                # prijde jako byty/string, dekodovani na slovnik
                data = json.loads(message)
            elif data_format == "msgpack":
                # prijde jako byty
                data = msgpack.unpackb(message)

            print(f"[>] Received: {data}")

            # pokud je to zprava k doruceni, odesleme ack
            if data.get("action") == "deliver":
                message_id = data.get("message_id")
                
                ack_msg = {
                    "action": "ack",
                    "message_id": message_id
                }
                
                if data_format == "json":
                    ack_bytes = json.dumps(ack_msg).encode("utf-8")
                elif data_format == "msgpack":
                    ack_bytes = msgpack.packb(ack_msg)
                    
                await websocket.send(ack_bytes)

                print(f"[<] Sent ACK for message_id: {message_id}")

async def publish(topic:str, data_format:str, data:str):
    uri = f"ws://localhost:8000/broker/{topic}"

    # prevede string payload (data v API requestu) na slovnik
    data_dict = json.loads(data)

    async with websockets.connect(uri, ping_interval=None) as websocket:
        # enkodovani
        if data_format == "json":
            # prevede slovnik na json, pak na byty
            out_message = json.dumps(data_dict).encode("utf-8")
        elif data_format == "msgpack":
            # prevede slovnik na byty
            out_message = msgpack.packb(data_dict)

        # posle zpravu
        await websocket.send(out_message)
        print(f"[<] Sent to '{topic}': {data_dict}")

def main():
    # argparser pro nastaveni CL argumentu
    parser = argparse.ArgumentParser(description= "pub/sub client")
    parser.add_argument("--mode", choices=["publish", "subscribe"], required = True)
    parser.add_argument("--topic", required=True, help="topic to subscribe=publish to")
    parser.add_argument("--format", choices=["json", "msgpack"], default="json", help="serialization format")
    parser.add_argument("--data", default='{"action": "publish", "payload": {"temp": 22.5}}', 
                        help="data to send (JSON string format)")
    
    args = parser.parse_args()

    # presmerovani do spravne async metody
    if args.mode == "subscribe":
        asyncio.run(subscribe(args.topic, args.format))
    elif args.mode == "publish":
        asyncio.run(publish(args.topic, args.format, args.data))

if __name__ == "__main__":
    main()