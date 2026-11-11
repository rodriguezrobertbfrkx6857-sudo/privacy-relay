from app.platform import audit, audit_report, database


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_audit_tamper():
    audit("one", {"count": 1})
    audit("two", {"count": 2})
    assert audit_report()["valid"]
    with database() as db:
        db.execute("UPDATE audit SET metadata='{}' WHERE id=1")
    assert not audit_report()["valid"]


def test_request_limit(client):
    assert client.post("/api/unknown", content="x" * 131073).status_code == 413


def test_headers(client):
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"


def test_local_boundary(client):
    assert client.get("/api/health", headers={"host": "attacker.invalid"}).status_code == 400
    assert client.get("/api/health", headers={"origin": "https://attacker.invalid"}).status_code == 403


def test_concurrent_fresh_database_audit():
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: audit("parallel", {"index": i}), range(24)))
    report = audit_report()
    assert report["valid"] and report["count"] == 24
