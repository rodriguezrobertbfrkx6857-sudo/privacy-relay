from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from app.privacy import Vault, detect, luhn


def test_card_checksum():
    assert luhn("4111 1111 1111 1111")
    assert not luhn("4111 1111 1111 1112")
    assert not luhn("0000 0000 0000 0000")


@pytest.mark.parametrize(
    "text,kind",
    [
        ("demo@example.com", "EMAIL"),
        ("202-555-0142", "PHONE"),
        ("13800138000", "PHONE"),
        ("4111 1111 1111 1111", "CARD"),
        ("api_key=synthetic_demo_123456", "SECRET"),
    ],
)
def test_entities(text, kind):
    assert detect(text)[0]["kind"] == kind


def test_roundtrip_and_stability():
    vault = Vault()
    a = vault.protect("Contact demo@example.com and demo@example.com")
    assert len(set(a["text"].split("⟦EMAIL:")[1:])) >= 1
    assert vault.restore(a["text"], a["session_token"]) == "Contact demo@example.com and demo@example.com"
    b = vault.protect("demo@example.com", a["session_token"])
    assert b["text"] in a["text"]


def test_session_unlinkability():
    v = Vault()
    a = v.protect("demo@example.com")
    b = v.protect("demo@example.com")
    assert a["text"] != b["text"]
    with pytest.raises(HTTPException) as e:
        v.restore(a["text"], b["session_token"])
    assert e.value.status_code == 403


def test_ttl_and_revoke():
    now = [100.0]
    v = Vault(clock=lambda: now[0])
    a = v.protect("a@example.com", ttl=30)
    now[0] = 131
    with pytest.raises(HTTPException):
        v.restore(a["text"], a["session_token"])
    b = v.protect("b@example.com")
    v.revoke(b["session_token"])
    with pytest.raises(HTTPException):
        v.restore(b["text"], b["session_token"])


def test_irreversible_secret():
    v = Vault()
    a = v.protect("api_key=synthetic_demo_123456")
    assert a["text"] == "[SECRET_REDACTED]"
    assert v.restore(a["text"], a["session_token"]) == "[SECRET_REDACTED]"
    assert a["irreversible"] == 1


def test_overlap_secret_wins():
    assert [e["kind"] for e in detect("password=person@example.com")] == ["SECRET"]


def test_injected_token_rejected():
    with pytest.raises(HTTPException):
        Vault().protect("⟦EMAIL:1234567812345678⟧")


def test_budget():
    v = Vault()
    a = v.protect("a" * 200000)
    with pytest.raises(HTTPException):
        v.protect("a", a["session_token"])


def test_concurrent_session_mapping():
    v = Vault()
    a = v.protect("hello")
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: v.protect("demo@example.com", a["session_token"]), range(8)))
    assert len({r["text"] for r in results}) == 1


def test_api_audit_no_sensitive_values(client):
    a = client.post("/api/protect", json={"text": "demo@example.com"}).json()
    history = client.get("/api/audit").text
    assert "demo@example.com" not in history and a["session_token"] not in history
    assert (
        client.post("/api/restore", json={"text": a["text"], "session_token": a["session_token"]}).json()[
            "text"
        ]
        == "demo@example.com"
    )
    assert client.post("/api/revoke", json={"session_token": a["session_token"]}).status_code == 200
    assert (
        client.post("/api/restore", json={"text": a["text"], "session_token": a["session_token"]}).status_code
        == 410
    )


def test_relay_only_sanitized_input(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "New PII: generated@example.com"}}

    def provider(*args, **kwargs):
        assert "demo@example.com" not in str(kwargs["json"])
        assert "⟦EMAIL:" in str(kwargs["json"])
        return Response()

    monkeypatch.setattr("app.main.httpx.post", provider)
    result = client.post("/api/relay", json={"text": "Email demo@example.com"}).json()
    assert result["output_redactions"] == 1
    assert "generated@example.com" not in result["model_output"]
