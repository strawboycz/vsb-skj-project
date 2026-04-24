import pytest
from fastapi.testclient import TestClient

# fastapi, instance ConnectionManageru
from main import app, manager

client = TestClient(app)

def test_successful_connection_and_disconnection():
    """
    Úspěšné připojení a odpojení klienta.
    """
    
    with client.websocket_connect("/broker/test_topic") as websocket:
        # pokud se nevyvola vyjimka, je pripojeni
        assert "test_topic" in manager.active_connections
        assert len(manager.active_connections["test_topic"]) == 1
        
    # kontrola odpojeni
    assert "test_topic" not in manager.active_connections


def test_message_routing_to_same_topic():
    """
    Zpráva odeslaná do tématu x dorazí klientovi, který odebírá téma x.
    """
    
    # pripojeni dvou klientu
    with client.websocket_connect("/broker/topic_x") as publisher, \
         client.websocket_connect("/broker/topic_x") as subscriber:
        
        test_message = b"Hello from Publisher!"
        publisher.send_bytes(test_message)
        
        # subscriber prijme data
        received_data = subscriber.receive_bytes()
        
        # kontrola dat
        assert received_data == test_message


def test_message_isolation_between_topics():
    """
    Zpráva odeslaná do tématu y nedorazí klientovi na tématu x.
    """
    
    # pripojeni k jinym topicum
    with client.websocket_connect("/broker/topic_x") as client_x, \
         client.websocket_connect("/broker/topic_y") as client_y:
        
        # klienti poslou zpravu
        client_y.send_bytes(b"Top secret message for Y")
        client_x.send_bytes(b"Message for X")
        
        # kontrola, ze klient ziskal jen svuj topic
        received_by_x = client_x.receive_bytes()
        
        assert received_by_x == b"Message for X"
        assert received_by_x != b"Top secret message for Y"