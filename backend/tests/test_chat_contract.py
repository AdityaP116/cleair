from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_requires_session_token():
    res = client.post("/v1/chat", json={"message": "What is the air quality?"})
    assert res.status_code == 401


def test_chat_rejects_wrong_payload_key():
    sess = client.post("/v1/session").json()
    res = client.post(
        "/v1/chat",
        json={"query": "hello"},
        headers={"x-session-token": sess["session_token"]},
    )
    assert res.status_code == 422


def test_session_to_chat_contract_flow():
    sess_res = client.post("/v1/session")
    assert sess_res.status_code == 200
    token = sess_res.json()["session_token"]

    chat_res = client.post(
        "/v1/chat",
        json={"message": "How can my family reduce PM2.5 exposure today?"},
        headers={"x-session-token": token},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "headline" in data or "summary" in data
