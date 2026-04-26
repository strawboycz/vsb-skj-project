import pytest
import json
from fastapi.testclient import TestClient

from database import engine
from models import Base
from main import app, manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.mark.asyncio
async def test_successful_connection_and_disconnection():
    """Úspěšné připojení a odpojení klienta."""
    with client.websocket_connect("/broker/test_topic") as websocket:
        assert "test_topic" in manager.active_connections
    assert "test_topic" not in manager.active_connections

@pytest.mark.asyncio
async def test_message_routing_to_same_topic():
    """Zpráva odeslaná do tématu X dorazí klientovi, který odebírá téma X."""
    with client.websocket_connect("/broker/topic_routing") as publisher:
        test_payload = {"action": "publish", "payload": "Hello from Publisher!"}
        publisher.send_bytes(json.dumps(test_payload).encode("utf-8"))
        publisher.receive_bytes() 
        
    with client.websocket_connect("/broker/topic_routing") as subscriber:
        received_data = subscriber.receive_bytes()
        received_dict = json.loads(received_data)
        
        assert received_dict["action"] == "deliver"
        assert received_dict["payload"] == "Hello from Publisher!"

@pytest.mark.asyncio
async def test_message_isolation_between_topics():
    """Zpráva odeslaná do tématu Y nedorazí klientovi na tématu X."""
    with client.websocket_connect("/broker/topic_iso_y") as client_y:
        msg_y_dict = {"action": "publish", "payload": "Top secret message for Y"}
        client_y.send_bytes(json.dumps(msg_y_dict).encode("utf-8"))
        client_y.receive_bytes()

    with client.websocket_connect("/broker/topic_iso_x") as client_x:
        msg_x_dict = {"action": "publish", "payload": "Message for X"}
        client_x.send_bytes(json.dumps(msg_x_dict).encode("utf-8"))
        
        received_by_x = client_x.receive_bytes()
        received_dict = json.loads(received_by_x)
        
        assert received_dict["payload"] == "Message for X"