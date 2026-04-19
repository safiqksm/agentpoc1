# Request / Response Flow — SPA to Agent (Function Level)

## Scenario A — Echo Test (no LLM, no tools)
> User types "hello" → hits /chat/echo

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER  poc-client-app/src/                                           │
│                                                                         │
│  App.jsx                                                                │
│  └─ handleLogin()                                                       │
│       └─ instance.loginPopup(loginRequest)  ──────────────────────────► │
│                                              Entra ID popup login       │
│  ◄──────────────────────────────────────────── access token returned    │
│                                                                         │
│  ChatPage.jsx                                                           │
│  └─ handleSubmit()        [user clicks Send]                            │
│       └─ sendPrompt(instance, account, "hello")                         │
│                                                                         │
│  services/agentService.js                                               │
│  └─ acquireTokenSilent()  ──── token already cached in sessionStorage   │
│  └─ fetch("POST /chat/echo")                                            │
│       headers: { Authorization: "Bearer <token>" }                      │
│       body:    { "prompt": "hello" }                                    │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS POST /chat/echo
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FASTAPI AGENT  agent/                                                  │
│                                                                         │
│  main.py                                                                │
│  └─ chat_echo(request, body)          [POST /chat/echo handler]         │
│       └─ extract_bearer_token(request)                                  │
│            checks Authorization header present                          │
│            returns token string                                         │
│       └─ returns ChatResponse                                           │
│            { reply: "Echo: hello", token_preview: "Bearer eyJ..." }     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ 200 OK  { "reply": "Echo: hello" }
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                                │
│  ChatPage.jsx                                                           │
│  └─ setResponse(result)   → displays reply in the UI                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Scenario B — LLM Direct Answer (no tool needed)
> User types "What is 2+2?" → hits /chat → LLM answers directly

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER  poc-client-app/src/                                           │
│                                                                         │
│  ChatPage.jsx                                                           │
│  └─ handleSubmit()                                                      │
│       └─ sendPrompt(instance, account, "What is 2+2?")                  │
│                                                                         │
│  services/agentService.js                                               │
│  └─ acquireTokenSilent()  ──── returns cached access token              │
│  └─ fetch("POST /chat")                                                 │
│       headers: { Authorization: "Bearer <token>" }                      │
│       body:    { "prompt": "What is 2+2?" }                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS POST /chat
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  main.py                                                                │
│  └─ chat(request, body)           [POST /chat handler]                 │
│       └─ extract_bearer_token(request)   ── validates header present   │
│       └─ agent_run(prompt, token)        ── hands off to orchestrator  │
│                                                                         │
│  orchestrator.py                                                        │
│  └─ run("What is 2+2?", token)                                         │
│       builds messages = [                                               │
│         { role: "system", content: SYSTEM_PROMPT },                    │
│         { role: "user",   content: "What is 2+2?" }                   │
│       ]                                                                 │
│       └─ call_llm_with_tools(messages, TOOLS)   ── Round 1            │
│                                                                         │
│  llm.py                                                                 │
│  └─ call_llm_with_tools(messages, tools)                               │
│       └─ _build_client()          ── builds AzureOpenAI client         │
│            checks AZURE_OPENAI_API_KEY → uses API key (local dev)      │
│       └─ client.chat.completions.create(...)                           │
│            model:       gpt-4o                                          │
│            messages:    [system, user]                                  │
│            tools:       TOOLS list (7 Okta tools)                      │
│            tool_choice: "auto"                                          │
│       ◄──── LLM responds: finish_reason = "stop"  (no tool needed)    │
│       returns { type: "text", content: "2+2 is 4.", model: "gpt-4o" } │
│                                                                         │
│  orchestrator.py  (back in run())                                       │
│       response["type"] == "text"  → exit loop                          │
│       returns {                                                         │
│         reply:       "2+2 is 4.",                                       │
│         tools_called: [],                                               │
│         model:       "gpt-4o"                                           │
│       }                                                                 │
│                                                                         │
│  main.py  (back in chat())                                              │
│       returns LLMChatResponse {                                         │
│         reply:        "2+2 is 4.",                                      │
│         model:        "gpt-4o",                                         │
│         tools_called: [],                                               │
│         token_preview: "eyJ0eXAiOiJKV1..."                             │
│       }                                                                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ 200 OK
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                                │
│  ChatPage.jsx  →  setResponse(result)  →  displays "2+2 is 4."        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Scenario C — LLM calls an Okta Tool (full agent loop)
> User types "List all Okta users" → LLM calls list_users tool → formats result

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER  poc-client-app/src/                                           │
│                                                                         │
│  ChatPage.jsx                                                           │
│  └─ handleSubmit()                                                      │
│       └─ sendPrompt(instance, account, "List all Okta users")          │
│                                                                         │
│  services/agentService.js                                               │
│  └─ acquireTokenSilent()  ──── returns access token                    │
│  └─ fetch("POST /chat")                                                 │
│       body: { "prompt": "List all Okta users" }                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS POST /chat
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  main.py                                                                │
│  └─ chat(request, body)                                                 │
│       └─ extract_bearer_token(request)                                  │
│       └─ agent_run("List all Okta users", token)                       │
│                                                                         │
│  orchestrator.py                                                        │
│  └─ run("List all Okta users", token)                                  │
│       messages = [system, user("List all Okta users")]                 │
│                                                                         │
│       ┌── ROUND 1 ────────────────────────────────────────────────┐   │
│       │                                                             │   │
│       │  llm.py                                                     │   │
│       │  └─ call_llm_with_tools(messages, TOOLS)                   │   │
│       │       └─ _build_client()                                    │   │
│       │       └─ client.chat.completions.create(...)               │   │
│       │            tools: [list_users, get_user, create_user, ...]  │   │
│       │       ◄── LLM: finish_reason = "tool_calls"               │   │
│       │            tool_call: { name: "list_users", args: {} }     │   │
│       │       returns { type: "tool_call",                         │   │
│       │                 tool_call: { id: "call_abc",               │   │
│       │                              name: "list_users",           │   │
│       │                              arguments: {} } }             │   │
│       │                                                             │   │
│       │  orchestrator.py checks DESTRUCTIVE_TOOLS                  │   │
│       │       "list_users" not in DESTRUCTIVE_TOOLS → proceed      │   │
│       │                                                             │   │
│       │  mcp_client.py                                              │   │
│       │  └─ call_tool("list_users", {}, token)                     │   │
│       │       MCP_SERVER_URL not set → mock fallback               │   │
│       │       returns [                                             │   │
│       │         { id:"00u1abc", login:"alice@example.com" },       │   │
│       │         { id:"00u2def", login:"bob@example.com"   },       │   │
│       │         { id:"00u3ghi", login:"carol@example.com" }        │   │
│       │       ]                                                     │   │
│       │                                                             │   │
│       │  orchestrator.py                                            │   │
│       │       appends to messages:                                  │   │
│       │         { role: "assistant", tool_calls: [call_abc] }      │   │
│       │         { role: "tool", content: "[{...users...}]" }       │   │
│       └─────────────────────────────────────────────────────────── ┘   │
│                                                                         │
│       ┌── ROUND 2 ────────────────────────────────────────────────┐   │
│       │                                                             │   │
│       │  llm.py                                                     │   │
│       │  └─ call_llm_with_tools(messages, TOOLS)                   │   │
│       │       messages now = [system, user, assistant, tool]       │   │
│       │       LLM sees the tool result and formats an answer       │   │
│       │       ◄── LLM: finish_reason = "stop"                     │   │
│       │            content: "Here are the Okta users:              │   │
│       │                      - alice@example.com (ACTIVE)          │   │
│       │                      - bob@example.com (ACTIVE)            │   │
│       │                      - carol@example.com (INACTIVE)"       │   │
│       │       returns { type: "text", content: "Here are..." }     │   │
│       │                                                             │   │
│       └─────────────────────────────────────────────────────────── ┘   │
│                                                                         │
│       response["type"] == "text" → exit loop                           │
│       returns {                                                         │
│         reply:        "Here are the Okta users: ...",                   │
│         tools_called: [{ tool:"list_users", args:{}, result:[...] }],  │
│         model:        "gpt-4o"                                          │
│       }                                                                 │
│                                                                         │
│  main.py                                                                │
│       returns LLMChatResponse {                                         │
│         reply:        "Here are the Okta users: ...",                   │
│         model:        "gpt-4o",                                         │
│         tools_called: [{ tool: "list_users", ... }],                   │
│         token_preview: "eyJ0eXAiOiJKV1..."                             │
│       }                                                                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ 200 OK
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                                │
│  ChatPage.jsx  →  setResponse(result)                                  │
│       displays: "Here are the Okta users:                               │
│                  - alice@example.com (ACTIVE)                           │
│                  - bob@example.com (ACTIVE)                             │
│                  - carol@example.com (INACTIVE)"                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Scenario E — Full OBO for AI Flow (real tokens, real Okta)
> User types "List all Okta users" — complete flow with three token exchanges

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER  (React SPA — localhost:5173)                                  │
│                                                                         │
│  agentService.js                                                        │
│  └─ acquireTokenSilent({ scopes: ["api://6b114879.../agent.access"] })  │
│       returns TOKEN #1  (User → Agent)                                  │
│         aud : api://6b114879-c58c-4889-9355-d5d9b19647a7               │
│         scp : agent.access                                              │
│         sub : <user-oid>                                                │
│  └─ fetch("POST http://localhost:8000/chat")                            │
│       Authorization: Bearer <TOKEN #1>                                  │
│       body: { "prompt": "List all Okta users" }                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ POST /chat  Bearer <TOKEN #1>
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  AGENT  (FastAPI — localhost:8000)                                      │
│                                                                         │
│  main.py                                                                │
│  └─ chat()                                                              │
│       └─ extract_bearer_token()   validates Authorization header        │
│       └─ agent_run(prompt, TOKEN #1)                                    │
│                                                                         │
│  orchestrator.py                                                        │
│  └─ run("List all Okta users", TOKEN #1)                               │
│       │                                                                 │
│       ├── OBO EXCHANGE #1 — Token for MCP Server ──────────────────┐  │
│       │   obo.py / exchange_obo_token(TOKEN #1)                     │  │
│       │   POST login.microsoftonline.com/{tid}/oauth2/v2.0/token    │  │
│       │     grant_type : urn:ietf:params:oauth:grant-type:jwt-bearer│  │
│       │     assertion  : <TOKEN #1>                                  │  │
│       │     scope      : api://b600aeb4.../mcp.call                 │  │
│       │   ◄── Entra issues TOKEN #2  (User → MCP Server)           │  │
│       │         aud : api://b600aeb4-32e1-40a7-840c-2ab22dd46fd6   │  │
│       │         scp : mcp.call                                       │  │
│       │         sub : <user-oid>  ← same user                       │  │
│       └────────────────────────────────────────────────────────────┘  │
│       │                                                                 │
│       ├── OBO EXCHANGE #2 — Token for Azure OpenAI (OBO for AI) ───┐  │
│       │   obo.py / exchange_obo_token_for_llm(TOKEN #1)             │  │
│       │   POST login.microsoftonline.com/{tid}/oauth2/v2.0/token    │  │
│       │     grant_type : urn:ietf:params:oauth:grant-type:jwt-bearer│  │
│       │     assertion  : <TOKEN #1>                                  │  │
│       │     scope      : https://cognitiveservices.azure.com/.default│ │
│       │   ◄── Entra issues TOKEN #3  (User → Azure OpenAI)         │  │
│       │         aud : https://cognitiveservices.azure.com           │  │
│       │         scp : user_impersonation                             │  │
│       │         sub : <user-oid>  ← same user                       │  │
│       └────────────────────────────────────────────────────────────┘  │
│       │                                                                 │
│       ├── ROUND 1 ───────────────────────────────────────────────────┐ │
│       │                                                               │ │
│       │  llm.py / call_llm_with_tools(messages, TOOLS, TOKEN #3)     │ │
│       │  └─ AzureOpenAI(azure_ad_token_provider=TOKEN #3)            │ │
│       │       POST foundry3000a.cognitiveservices.azure.com/          │ │
│       │            openai/deployments/gpt-4.1/chat/completions        │ │
│       │         Authorization: Bearer <TOKEN #3>                      │ │
│       │         messages: [system, user("List all Okta users")]       │ │
│       │         tools:    [list_users, get_user, ...]                 │ │
│       │         tool_choice: "auto"                                   │ │
│       │   Azure OpenAI validates TOKEN #3 RBAC:                       │ │
│       │     user has Cognitive Services OpenAI User role ✓            │ │
│       │   ◄── finish_reason: "tool_calls"                            │ │
│       │         tool_call: { name: "list_users", args: {} }           │ │
│       │                                                               │ │
│       │  orchestrator.py                                              │ │
│       │  └─ "list_users" not in DESTRUCTIVE_TOOLS → proceed          │ │
│       │                                                               │ │
│       │  mcp_client.py / call_tool("list_users", {}, TOKEN #2)       │ │
│       │  └─ POST http://localhost:9000/mcp/call                      │ │
│       │         Authorization: Bearer <TOKEN #2>                      │ │
│       │         body: { "tool": "list_users", "arguments": {} }      │ │
│       └───────────────────────────────────────────────────────────── ┘ │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │ POST /mcp/call  Bearer <TOKEN #2>
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  MCP SERVER  (FastAPI — localhost:9000)                                 │
│                                                                         │
│  main.py / mcp_call()                                                  │
│  └─ token_verifier.py / verify_token(TOKEN #2)                         │
│       fetch JWKS from login.microsoftonline.com/{tid}/discovery/keys   │
│       ✓ RS256 signature valid                                           │
│       ✓ aud  == api://b600aeb4-32e1-40a7-840c-2ab22dd46fd6            │
│       ✓ scp  == mcp.call                                               │
│       ✓ exp  not expired                                               │
│       ✓ iss  == sts.windows.net/b66066d2...                            │
│       returns claims { sub: <user-oid> }                               │
│                                                                         │
│  okta_tools.py / dispatch("list_users", {})                            │
│  └─ okta_client.py / get_okta_token()                                  │
│       cache hit? → return cached token (1h TTL)                        │
│       cache miss →                                                      │
│         build client_assertion JWT (RS256, signed with okta_private.pem)│
│         POST oie-8764513.oktapreview.com/oauth2/v1/token               │
│           grant_type            : client_credentials                    │
│           client_assertion_type : urn:ietf:...:jwt-bearer              │
│           client_assertion      : <signed JWT>                          │
│           scope                 : okta.users.read okta.users.manage ... │
│         ◄── Okta issues OKTA TOKEN                                     │
│               aud   : https://oie-8764513.oktapreview.com              │
│               scope : okta.users.read okta.users.manage ...             │
│               sub   : 0oax4b20kdBGCVvMk1d7  (service app, not user)   │
│                                                                         │
│  okta_tools.py / list_users()                                          │
│  └─ GET oie-8764513.oktapreview.com/api/v1/users?limit=25             │
│         Authorization: Bearer <OKTA TOKEN>                              │
│   ◄── 200 OK  [ { id, status, profile.login, ... }, ... ]             │
│                                                                         │
│  main.py                                                                │
│  └─ _log_tool_call("list_users", {}, sub, result=[...])               │
│       appends to tool_call_debug.txt                                    │
│  └─ returns { "tool": "list_users", "result": [ {...}, ... ] }         │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │ 200 OK  { tool, result: [...users...] }
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  AGENT  (back in orchestrator.py)                                       │
│                                                                         │
│  └─ tools_called.append({ tool:"list_users", result:[...] })           │
│  └─ messages.append:                                                    │
│       { role:"assistant", tool_calls:[{ id, name:"list_users" }] }     │
│       { role:"tool",      content:"[{...users...}]" }                  │
│                                                                         │
│       ├── ROUND 2 ───────────────────────────────────────────────────┐ │
│       │                                                               │ │
│       │  llm.py / call_llm_with_tools(messages, TOOLS, TOKEN #3)     │ │
│       │       messages: [system, user, assistant(tool_call), tool]    │ │
│       │       POST foundry3000a.cognitiveservices.azure.com/...       │ │
│       │         Authorization: Bearer <TOKEN #3>                      │ │
│       │   ◄── finish_reason: "stop"                                  │ │
│       │         content: "Here are the active users in your Okta..."  │ │
│       │       returns { type:"text", content:"Here are...", model }   │ │
│       │                                                               │ │
│       └───────────────────────────────────────────────────────────── ┘ │
│                                                                         │
│  └─ final_result = {                                                    │
│       reply:        "Here are the active users in your Okta tenant...",│
│       tools_called: [{ tool:"list_users", args:{}, result:[...] }],    │
│       model:        "gpt-4.1"                                           │
│     }                                                                   │
│  └─ _fetch_okta_debug() → appends Okta token info to token_debug.txt  │
│                                                                         │
│  main.py                                                                │
│  └─ returns LLMChatResponse {                                           │
│       reply:        "Here are the active users...",                     │
│       model:        "gpt-4.1",                                          │
│       tools_called: [{ tool:"list_users", ... }],                      │
│       token_preview: "eyJ0eXAiOiJKV1..."                               │
│     }                                                                   │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │ 200 OK
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER  (React SPA)                                                   │
│  ChatPage.jsx → renders reply + tools_called panel                     │
└─────────────────────────────────────────────────────────────────────────┘

Token Summary
─────────────────────────────────────────────────────────────────────────
  #1  User → Agent       aud: api://6b114879...   scp: agent.access
  #2  User → MCP Server  aud: api://b600aeb4...   scp: mcp.call
  #3  User → Azure OpenAI aud: cognitiveservices.azure.com  scp: user_impersonation
  #4  MCP → Okta         aud: oie-8764513.okta...  scp: okta.users.read ...
      (service token — client_credentials, not on behalf of user)
─────────────────────────────────────────────────────────────────────────
```

---

## Scenario D — Destructive Tool Blocked (OWASP LLM06)
> User types "Show me users" but LLM tries to call deactivate_user

```
  orchestrator.py
  └─ run("Show me users", token)
       ...
       LLM unexpectedly calls { name: "deactivate_user", args: { user_id: "00u1" } }

       DESTRUCTIVE_TOOLS check:
         "deactivate_user" in DESTRUCTIVE_TOOLS → YES
         any(kw in "show me users" for kw in ["deactivate","reset",...]) → NO

       ► blocked — returns immediately:
         { reply: "I can perform 'deactivate_user' but I need explicit confirmation..." }
```

---

## Error Flows

```
agentService.js
└─ fetch() → no Authorization header sent
     main.py → extract_bearer_token() → raises HTTPException(401)
     response: { detail: "Missing or invalid Authorization header" }
     agentService.js → throws Error → ChatPage.jsx → setError(err.message)

agentService.js
└─ acquireTokenSilent() fails (token expired)
     → falls back to acquireTokenPopup()
     → Entra ID popup shown to user
     → new token acquired → request retried

main.py → agent_run() → llm.py → _build_client()
     AZURE_OPENAI_ENDPOINT not set
     → raises RuntimeError
     → main.py catches → HTTPException(500, "AZURE_OPENAI_ENDPOINT is not set")
```

---

## File Responsibility Summary

```
poc-client-app/src/
├── App.jsx              login/logout UI, renders ChatPage when authenticated
├── pages/ChatPage.jsx   prompt input form, displays reply
├── services/
│   └── agentService.js  acquires token + POSTs to agent backend
└── authConfig.js        MSAL config (clientId, authority, scopes)

agent/
├── main.py              HTTP layer — routes requests, validates token, returns response
├── orchestrator.py      ReAct loop — LLM ↔ tool calls until final answer
├── llm.py               Azure OpenAI calls (with and without tools)
├── mcp_client.py        Calls MCP Server (or mock) to execute Okta tools
└── tools.py             Tool catalogue — what the LLM is allowed to call
```
