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
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from token_verifier import verify_token
from okta_tools import dispatch

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    # Step 2 — verify token (signature + claims).
    # verify_token() currently checks presence only; full JWT validation added in Step 4.
    token_claims = verify_token(token)
    logger.info("MCP call: tool=%s  subject=%s", body.tool, token_claims.get("sub", "unknown"))

    # Step 3 — dispatch to the correct Okta tool handler
    result = await dispatch(body.tool, body.arguments)

    return {"tool": body.tool, "result": result}


@app.get("/health")
async def health():
    return {"status": "ok", "server": "mcp-okta"}
