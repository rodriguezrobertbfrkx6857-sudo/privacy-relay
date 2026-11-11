"""Shared infrastructure: bounded input, metadata-only hash-chain audit, local UI."""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from starlette.middleware.trustedhost import TrustedHostMiddleware


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManagedConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


_INIT_LOCK = Lock()
_INITIALIZED = set()


def database():
    path = Path(os.getenv("APP_DB", "data/app.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, factory=ManagedConnection)
    db.row_factory = sqlite3.Row
    # Switching journal mode concurrently on a fresh file can fail before busy_timeout applies.
    # Initialize once per database path under a process-local lock; request transactions remain independent.
    identity = str(path.resolve())
    with _INIT_LOCK:
        if identity not in _INITIALIZED:
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, ts REAL, event TEXT, metadata TEXT, previous TEXT, digest TEXT)"
                )
                db.commit()
                _INITIALIZED.add(identity)
            except Exception:
                db.close()
                raise
    return db


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def audit(event, metadata):
    # Callers supply counts/IDs/decisions only, never prompts, credentials or PII.
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        last = db.execute("SELECT digest FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        previous = last[0] if last else "0" * 64
        stamp = time.time()
        payload = canonical(metadata)
        digest = hashlib.sha256(canonical([stamp, event, payload, previous]).encode()).hexdigest()
        db.execute(
            "INSERT INTO audit(ts,event,metadata,previous,digest) VALUES(?,?,?,?,?)",
            (stamp, event, payload, previous, digest),
        )


def audit_report():
    with database() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM audit ORDER BY id")]
    previous = "0" * 64
    valid = True
    for row in rows:
        expected = hashlib.sha256(
            canonical([row["ts"], row["event"], row["metadata"], previous]).encode()
        ).hexdigest()
        valid = valid and row["previous"] == previous and row["digest"] == expected
        previous = row["digest"]
    return {
        "valid": valid,
        "count": len(rows),
        "head": previous,
        "events": rows[-50:],
        "scope": "Detects modification/reordering; not anchored externally and cannot detect tail truncation.",
    }


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 131072:
                return await JSONResponse({"detail": "Body exceeds 128 KiB"}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(message)
            if not message.get("more_body"):
                break

        async def replay():
            if chunks:
                return chunks.pop(0)
            return await receive()

        await self.app(scope, replay, send)


def make_app(title):
    app = FastAPI(
        title=title,
        version="0.1.0",
        description="Local research workbench. See SECURITY.md before deployment.",
    )
    app.add_middleware(BodyLimit)
    allowed_hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware("http")
    async def headers(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).hostname not in allowed_hosts:
            return JSONResponse({"detail": "Origin is not trusted"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
            )
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "service": title}

    @app.get("/api/audit")
    def history():
        return audit_report()

    return app


def mount_ui(app):
    path = Path(__file__).resolve().parents[1] / "web" / "dist"
    if path.exists():
        app.mount("/", StaticFiles(directory=path, html=True), name="ui")
