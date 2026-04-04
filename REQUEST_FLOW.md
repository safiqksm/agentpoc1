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
