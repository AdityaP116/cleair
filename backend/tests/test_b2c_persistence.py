from fastapi.testclient import TestClient
from app.main import app
from app.repositories.memory import repo

client = TestClient(app)


def test_profile_persists_and_deletes():
    sess = client.post("/v1/session").json()
    hdr = {"x-session-token": sess["session_token"]}

    # Update profile
    res = client.patch("/v1/profile", json={"city": "Thane", "has_child": True}, headers=hdr)
    assert res.status_code == 200
    assert res.json()["city"] == "Thane"

    # Fetch profile
    get_res = client.get("/v1/profile", headers=hdr)
    assert get_res.status_code == 200
    assert get_res.json()["city"] == "Thane"
    assert get_res.json()["has_child"] is True

    # Delete profile & sessions
    del_res = client.delete("/v1/profile", headers=hdr)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Session is now invalid -> 401
    after_res = client.get("/v1/profile", headers=hdr)
    assert after_res.status_code == 401


def test_expired_session_rejected():
    repo.create_session("expired-tok-123", "user-exp", ttl_hours=-1)
    res = client.get("/v1/profile", headers={"x-session-token": "expired-tok-123"})
    assert res.status_code == 401
