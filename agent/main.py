# =============================================================================
# STEP 2 — ACA Ingress / Agent entry point
# Receives HTTPS requests from the React client app (Step 1).
# Validates the Bearer token is present (signature validation in Step 4).
# Enforces CORS and input length — OWASP LLM01/AA01 mitigation.
# =============================================================================

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from llm import call_llm
from orchestrator import run as agent_run

load_dotenv()

app = FastAPI(title="AgentPOC1")

# STEP 2 — CORS restricted to the known SPA origin (React dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "http://localhost:5173")],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
    # STEP 4 (TODO) — OBO token exchange happens here before passing token downstream
    token_preview = token[:20] + "..." if len(token) > 20 else token

    try:
        # STEP 3 — hand off to orchestrator (ReAct loop)
        result = await agent_run(body.prompt, token)
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


# STEP 2 — Health check for ACA liveness/readiness probes
@app.get("/health")
async def health():
    return {"status": "ok"}
