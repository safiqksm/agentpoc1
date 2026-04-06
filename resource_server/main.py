# =============================================================================
# HR Resource Server — FastAPI app
#
# Exposes HR employee data via a single tool-call endpoint.
# Tokens are validated as XAA access tokens issued by an Okta Custom AS.
#
# Endpoints:
#   POST /tools/call   — execute an HR tool (get_employee_profile, etc.)
#   GET  /health       — liveness check
#
# Start with:
#   uvicorn main:app --port 8100 --reload
# =============================================================================

import os
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from token_verifier import verify_token
from hr_tools import dispatch

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
_LOG_FILE = Path(__file__).parent / "resource_server.log"
_fmt = logging.Formatter("%(asctime)s  %(levelname)s  %(name)s  %(message)s")
_file_handler = RotatingFileHandler(_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3)
_file_handler.setFormatter(_fmt)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)
logging.basicConfig(level=logging.DEBUG, handlers=[_console_handler, _file_handler])
logger = logging.getLogger(__name__)

_TOKEN_LOG = Path(__file__).parent / "token_debug.txt"


def _log_token_event(section: str, detail: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {section}\n{detail}\n{'-' * 72}\n"
    logger.debug("%s | %s", section, detail)
    with _TOKEN_LOG.open("a") as f:
        f.write(line)

app = FastAPI(title="HR Resource Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_AGENT_ORIGIN", "http://localhost:8000")],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ToolCallRequest(BaseModel):
    tool: str
    arguments: dict = {}


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = auth[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token")
    return token


@app.post("/tools/call")
async def tools_call(request: Request, body: ToolCallRequest):
    token = _extract_bearer_token(request)

    # Log the raw token for debugging — first 40 chars + length to avoid huge files
    _log_token_event(
        "RESOURCE SERVER — token received",
        f"token_prefix={token[:40]}...  len={len(token)}  tool={body.tool}",
    )

    try:
        claims = verify_token(token)
    except HTTPException as exc:
        _log_token_event(
            "RESOURCE SERVER — token REJECTED",
            f"status={exc.status_code}  detail={exc.detail}",
        )
        raise

    subject = claims.get("sub", "unknown")
    scp = claims.get("scp") or claims.get("scope", "?")
    iss = claims.get("iss", "?")
    aud = claims.get("aud", "?")
    _log_token_event(
        "RESOURCE SERVER — token VALID",
        f"sub={subject}  scp={scp}  iss={iss}  aud={aud}",
    )

    logger.info("Tool call: tool=%s  subject=%s  args=%s", body.tool, subject, body.arguments)
    result = await dispatch(body.tool, body.arguments)
    return {"tool": body.tool, "result": result}


@app.get("/health")
async def health():
    return {"status": "ok", "server": "hr-resource-server"}
