import os

import httpx
from fastapi import HTTPException
from pydantic import Field

from app.platform import StrictModel, audit, make_app, mount_ui
from app.privacy import detect, vault

app = make_app("Privacy Relay")


class Protect(StrictModel):
    text: str = Field(min_length=1, max_length=20000)
    session_token: str | None = Field(default=None, min_length=20, max_length=100)
    ttl: int = Field(default=300, ge=30, le=900)


class Restore(StrictModel):
    text: str = Field(min_length=1, max_length=30000)
    session_token: str = Field(min_length=20, max_length=100)


class Revoke(StrictModel):
    session_token: str = Field(min_length=20, max_length=100)


@app.post("/api/protect")
def protect(body: Protect):
    result = vault.protect(body.text, body.session_token, body.ttl)
    audit(
        "protect",
        {
            "entity_count": len(result["entities"]),
            "irreversible": result["irreversible"],
            "characters": len(body.text),
        },
    )
    return result


@app.post("/api/restore")
def restore(body: Restore):
    text = vault.restore(body.text, body.session_token)
    audit("restore", {"characters": len(text)})
    return {"text": text}


@app.post("/api/revoke")
def revoke(body: Revoke):
    vault.revoke(body.session_token)
    audit("revoke", {})
    return {"revoked": True}


@app.post("/api/relay")
def relay(body: Protect):
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        raise HTTPException(503, "Set OLLAMA_MODEL to enable the local model relay")
    protected = protect(body)
    try:
        response = httpx.post(
            os.getenv("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat",
            timeout=45,
            json={
                "model": model,
                "stream": False,
                "options": {"num_predict": 500},
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer the request. Preserve privacy placeholders exactly. Never invent or expand personal information.",
                    },
                    {"role": "user", "content": protected["text"]},
                ],
            },
        )
        response.raise_for_status()
        output = response.json()["message"]["content"]
        if not isinstance(output, str) or len(output) > 30000:
            raise ValueError("Invalid output")
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, "Local provider failed") from exc
    # Output DLP catches newly generated recognizable PII; restoration remains an explicit separate action.
    findings = detect(output)
    for entity in reversed(findings):
        output = output[: entity["start"]] + "[OUTPUT_REDACTED]" + output[entity["end"] :]
    audit("relay", {"output_redactions": len(findings)})
    return {**protected, "model_output": output, "output_redactions": len(findings), "provider": "ollama"}


mount_ui(app)
