# =============================================================================
# STEP 2 — ACA Ingress / Agent entry point
# Receives HTTPS requests from the React client app (Step 1).
# Validates the Bearer token is present (signature validation in Step 4).
# Enforces CORS and input length — OWASP LLM01/AA01 mitigation.
# =============================================================================

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from llm import call_llm
from orchestrator import run as agent_run
from obo import exchange_obo_token, exchange_obo_token_for_llm
from jose import jwt as jose_jwt

# Always load .env from the same directory as this file, regardless of CWD
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

_LOG_FILE = Path(__file__).parent / "agent.log"
_fmt = logging.Formatter("%(asctime)s  %(levelname)s  %(name)s  %(message)s")
_file_handler = RotatingFileHandler(_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3)
_file_handler.setFormatter(_fmt)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console_handler, _file_handler])
logger = logging.getLogger(__name__)
logger.info("Agent starting — MCP_SERVER_URL=%s", os.getenv("MCP_SERVER_URL") or "(not set)")

app = FastAPI(title="AgentPOC1")

# STEP 2 — CORS restricted to the known SPA origin (React dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGIN", "http://localhost:5173").split(","),
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Auth-Provider"],
)

# STEP 2 — Input length cap (OWASP LLM01: Prompt Injection mitigation)
MAX_PROMPT_LENGTH = 2000


# STEP 2 — Request/response shapes (validated automatically on parse)
class ChatRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def prompt_max_length(cls, v):
        if len(v) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters")
        return v.strip()


class ChatResponse(BaseModel):
    reply: str
    token_preview: str


class LLMChatResponse(BaseModel):
    reply: str
    model: str
    tools_called: list
    token_preview: str


# STEP 2 — Extract and validate Bearer token from Authorization header.
# Step 4 will add full JWT signature + claims validation (OBO token).
def extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token is empty")
    return token


# STEP 3 — Main chat endpoint: routes through the agent orchestrator.
# The orchestrator (Step 3) calls the LLM (Step 13) and optionally
# calls Okta tools via the MCP client (Steps 5–12).
@app.post("/chat", response_model=LLMChatResponse)
async def chat(request: Request, body: ChatRequest):
    # STEP 2 — validate token presence
    token = extract_bearer_token(request)
    auth_provider = request.headers.get("X-Auth-Provider", "entra")
    token_preview = token[:20] + "..." if len(token) > 20 else token

    try:
        # STEP 3 — hand off to orchestrator (ReAct loop)
        result = await agent_run(body.prompt, token, auth_provider)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")

    return LLMChatResponse(
        reply=result["reply"],
        model=result["model"],
        tools_called=result["tools_called"],
        token_preview=token_preview,
    )


# STEP 2 — Echo endpoint kept for testing without Azure OpenAI credentials.
# Bypasses the orchestrator and LLM entirely.
@app.post("/chat/echo", response_model=ChatResponse)
async def chat_echo(request: Request, body: ChatRequest):
    token = extract_bearer_token(request)
    token_preview = token[:20] + "..." if len(token) > 20 else token

    return ChatResponse(
        reply=f"Echo: {body.prompt}",
        token_preview=token_preview,
    )


# DEBUG — Token trace endpoint: shows user token claims + OBO token claims
# Remove this endpoint before production deployment
@app.get("/debug/token")
async def debug_token(request: Request):
    token = extract_bearer_token(request)

    def decode_claims(t):
        try:
            return jose_jwt.decode(t, "", options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
        except Exception as e:
            return {"error": str(e), "raw": t[:40]}

    user_claims = decode_claims(token)

    try:
        obo_token = await exchange_obo_token(token)
        obo_claims = decode_claims(obo_token)
        obo_error = None
    except RuntimeError as e:
        obo_token = None
        obo_claims = None
        obo_error = str(e)

    return {
        "user_token": {
            "aud": user_claims.get("aud"),
            "scp": user_claims.get("scp"),
            "sub": user_claims.get("sub"),
            "iss": user_claims.get("iss"),
            "exp": user_claims.get("exp"),
        },
        "obo_token": {
            "aud": obo_claims.get("aud") if obo_claims else None,
            "scp": obo_claims.get("scp") if obo_claims else None,
            "sub": obo_claims.get("sub") if obo_claims else None,
            "iss": obo_claims.get("iss") if obo_claims else None,
            "exp": obo_claims.get("exp") if obo_claims else None,
        } if obo_claims else None,
        "obo_error": obo_error,
    }


# DEBUG — LLM token trace: shows user token claims + OBO LLM token claims
# Remove this endpoint before production deployment
@app.get("/debug/token/llm")
async def debug_token_llm(request: Request):
    token = extract_bearer_token(request)

    def decode_claims(t):
        try:
            return jose_jwt.decode(t, "", options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
        except Exception as e:
            return {"error": str(e), "raw": t[:40]}

    user_claims = decode_claims(token)

    try:
        llm_token = await exchange_obo_token_for_llm(token)
        llm_claims = decode_claims(llm_token) if llm_token else None
        llm_error = None
    except RuntimeError as e:
        llm_token = None
        llm_claims = None
        llm_error = str(e)

    return {
        "user_token": {
            "aud": user_claims.get("aud"),
            "scp": user_claims.get("scp"),
            "sub": user_claims.get("sub"),
            "iss": user_claims.get("iss"),
        },
        "llm_token": {
            "aud": llm_claims.get("aud") if llm_claims else None,
            "scp": llm_claims.get("scp") if llm_claims else None,
            "sub": llm_claims.get("sub") if llm_claims else None,
            "iss": llm_claims.get("iss") if llm_claims else None,
        } if llm_claims else None,
        "llm_error": llm_error,
    }


# STEP 2 — Health check for ACA liveness/readiness probes
@app.get("/health")
async def health():
    return {"status": "ok"}
