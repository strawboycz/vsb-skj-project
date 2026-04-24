from fastapi import WebSocket

"""
Úkol 1: Implementace Brokera (FastAPI WebSockets)
"""


class ConnectionManager:
    def __init__(self):
        # Mapa: název tématu -> množina připojených WebSocketů
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str):
        await websocket.accept()
        if topic not in self.active_connections:
            self.active_connections[topic] = set()
        self.active_connections[topic].add(websocket)

    def disconnect(self, websocket: WebSocket, topic: str):
        if topic in self.active_connections:
            self.active_connections[topic].discard(websocket)
            # Pokud je téma prázdné, můžeme ho smazat pro úsporu paměti
            if not self.active_connections[topic]:
                del self.active_connections[topic]

    async def broadcast(self, message: bytes, topic: str):
        # V reálném nasazení zde použijeme asynchronní rozeslání
        # všem klientům v self.active_connections[topic]
        if topic in self.active_connections:
            # kopie aktivnich pripojeni
            active_sockets = list(self.active_connections[topic])
            
            for connection in active_sockets:
                try:
                    # poslani zpravy
                    await connection.send_bytes(message)
                except Exception:
                    # pokud klient vypadnul zrovna kdyz se posilala zprava
                    pass