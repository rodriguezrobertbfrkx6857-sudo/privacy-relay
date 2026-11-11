"""Ephemeral session vault. PII never enters SQLite. Secrets cannot be restored."""

import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field
from threading import RLock

from fastapi import HTTPException

TOKEN = re.compile(r"⟦[A-Z_]+:[a-f0-9]{16}⟧")
PATTERNS = [
    (
        "SECRET",
        100,
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}|(?:api_key|password|secret)\s*[=:]\s*[^\s,;]{6,})",
            re.IGNORECASE,
        ),
    ),
    (
        "EMAIL",
        80,
        re.compile(r"(?<![\w.+-])[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"),
    ),
    ("CARD", 70, re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")),
    (
        "PHONE",
        60,
        re.compile(
            r"(?<!\w)(?:\+?1[ .-]?)?\(?[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)|(?<!\d)1[3-9]\d{9}(?!\d)"
        ),
    ),
]


def luhn(value):
    digits = [int(c) for c in value if c.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) < 2:
        return False
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2:
            digit = digit * 2
            digit = digit - 9 if digit > 9 else digit
        total += digit
    return total % 10 == 0


def detect(text):
    candidates = []
    for kind, priority, pattern in PATTERNS:
        for match in pattern.finditer(text):
            if kind == "CARD" and not luhn(match[0]):
                continue
            candidates.append(
                {"kind": kind, "start": match.start(), "end": match.end(), "priority": priority}
            )
    selected = []
    for item in sorted(candidates, key=lambda c: (-c["priority"], c["start"])):
        if not any(item["start"] < other["end"] and other["start"] < item["end"] for other in selected):
            selected.append(item)
    return sorted(selected, key=lambda c: c["start"])


@dataclass
class Session:
    expires: float
    mapping: dict = field(default_factory=dict)
    reverse: dict = field(default_factory=dict)
    chars: int = 0


class Vault:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.sessions = {}
        self.lock = RLock()

    def prune(self):
        for key in list(self.sessions):
            if self.sessions[key].expires <= self.clock():
                del self.sessions[key]

    def session(self, token, ttl):
        self.prune()
        if token:
            key = hashlib.sha256(token.encode()).hexdigest()
            session = self.sessions.get(key)
            if not session:
                raise HTTPException(
                    410, "Session is expired, revoked, or belongs to a previous server process"
                )
            return token, session
        if len(self.sessions) >= 1000:
            raise HTTPException(429, "Session capacity reached")
        token = secrets.token_urlsafe(32)
        session = Session(self.clock() + ttl)
        self.sessions[hashlib.sha256(token.encode()).hexdigest()] = session
        return token, session

    def protect(self, text, token=None, ttl=300):
        if "⟦" in text or "⟧" in text:
            raise HTTPException(422, "Reserved token delimiters are not allowed in input")
        with self.lock:
            token, session = self.session(token, ttl)
            if session.chars + len(text) > 200000:
                raise HTTPException(429, "Session text budget exceeded")
            entities = detect(text)
            parts = []
            cursor = 0
            for item in entities:
                raw = text[item["start"] : item["end"]]
                kind = item["kind"]
                if kind == "SECRET":
                    placeholder = "[SECRET_REDACTED]"
                else:
                    lookup = (kind, raw)
                    if lookup not in session.reverse:
                        placeholder = f"⟦{kind}:{secrets.token_hex(8)}⟧"
                        session.reverse[lookup] = placeholder
                        session.mapping[placeholder] = raw
                    placeholder = session.reverse[lookup]
                parts.extend([text[cursor : item["start"]], placeholder])
                cursor = item["end"]
            parts.append(text[cursor:])
            session.chars += len(text)
            return {
                "text": "".join(parts),
                "session_token": token,
                "expires_at": session.expires,
                "entities": [{k: v for k, v in e.items() if k != "priority"} for e in entities],
                "restorable": sum(e["kind"] != "SECRET" for e in entities),
                "irreversible": sum(e["kind"] == "SECRET" for e in entities),
            }

    def restore(self, text, token):
        with self.lock:
            _, session = self.session(token, 300)
            tokens = TOKEN.findall(text)
            if any(t not in session.mapping for t in tokens):
                raise HTTPException(403, "Unknown token or cross-session token substitution")
            remainder = TOKEN.sub("", text)
            if "⟦" in remainder or "⟧" in remainder:
                raise HTTPException(422, "Malformed token")
            return TOKEN.sub(lambda m: session.mapping[m[0]], text)

    def revoke(self, token):
        with self.lock:
            self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)


vault = Vault()
