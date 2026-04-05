# =============================================================================
# MCP Server (Okta) — receives tool calls directly from the Agent.
#
# Responsibilities:
#   1. Verify the Bearer token from the Agent (signature check in Step 4;
#      presence check only for now).
#   2. Route the tool call to the correct Okta handler.
#   3. Return the Okta API result as JSON.
#
# Token verification is done HERE — the Agent just forwards its token.
# No APIM in this path; the Agent calls this server directly.
#
# Step 9/10 (Key Vault + Okta client_credentials) will be added when the
# real Okta tenant is connected.
# =============================================================================

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from token_verifier import verify_token
from okta_tools import dispatch
from okta_client import get_last_token_info

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEBUG_FILE = Path(__file__).parent / "tool_call_debug.txt"


def _log_tool_call(tool: str, args: dict, subject: str, result=None, error: str | None = None) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "timestamp": ts,
        "tool":      tool,
        "subject":   subject,
        "request":   args,
        "response":  result,
        "error":     error,
    }
    with _DEBUG_FILE.open("a") as f:
        f.write(json.dumps(entry, indent=2) + "\n" + ("-" * 60) + "\n")

app = FastAPI(title="MCP Server — Okta")

# Only the Agent container is allowed to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_AGENT_ORIGIN", "http://localhost:8000")],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ToolCallRequest(BaseModel):
    tool: str
    arguments: dict = {}


class ToolCallResponse(BaseModel):
    tool: str
    result: dict | list


def extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token is empty")
    return token


@app.post("/mcp/call")
async def mcp_call(request: Request, body: ToolCallRequest):
    # Step 1 — extract token forwarded from the Agent
    token = extract_bearer_token(request)

    # Step 2 — verify token (signature + claims)
    token_claims = verify_token(token)
    subject = token_claims.get("sub", "unknown")
    logger.info("MCP call received: tool=%s  subject=%s  args=%s", body.tool, subject, body.arguments)

    # Step 3 — dispatch to the correct Okta tool handler
    try:
        result = await dispatch(body.tool, body.arguments)
    except Exception as exc:
        _log_tool_call(body.tool, body.arguments, subject, error=str(exc))
        raise

    _log_tool_call(body.tool, body.arguments, subject, result=result)
    logger.info("MCP call complete: tool=%s  subject=%s", body.tool, subject)
    return {"tool": body.tool, "result": result}


@app.get("/debug/okta-token")
async def debug_okta_token():
    """Debug — returns last acquired Okta token info. Remove before production."""
    return get_last_token_info()


@app.get("/health")
async def health():
    return {"status": "ok", "server": "mcp-okta"}
