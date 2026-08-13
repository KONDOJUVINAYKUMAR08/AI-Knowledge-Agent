# AI Knowledge Agent - Project Handoff

## 1. Project Identity
- **Repository name**: AI-Knowledge-Agent
- **GitHub remote**: https://github.com/KONDOJUVINAYKUMAR08/AI-Knowledge-Agent.git
- **Current branch**: main
- **Current HEAD commit**: ba02b2f docs: update PROJECT_HANDOFF.md for Phase 10 completion
- **Current working tree status**: Phase 11 changes present and intentionally uncommitted pending review and EC2 validation
- **Project directory structure**:
  - `docs/`: Documentation and project handoff.
  - `frontend/`: React frontend application.
  - `knowledge-agent/`: FastAPI backend + LangGraph Agent + MCP Client.
  - `mcp-server/`: MCP Server providing Mock Jira tools.
  - `shared/`: Shared Pydantic models across components.

## 2. Project Objective
The AI Knowledge Agent POC is intended to demonstrate whether an AI Knowledge Agent can help freshers/support engineers understand Jira tickets faster. It retrieves ticket contexts, historical resolutions, and generates structured troubleshooting guidance to reduce onboarding time and improve incident response.

## 3. Architecture
The complete architecture currently implemented is as follows:

```
User
↓
Frontend / API
↓
FastAPI
↓
LangGraph Knowledge Agent
↓
MCP Client
↓
Streamable HTTP
↓
MCP Server
↓
Mock Jira repository/tools
↓
Retrieved ticket/context
↓
LLM
↓
Structured Knowledge Response
```

**Role of each component:**
- **Frontend / API**: Handles user queries and presents the structured output.
- **FastAPI**: Provides the REST API layer for incoming requests.
- **LangGraph Knowledge Agent**: Executes a deterministic workflow (Understand -> Retrieve -> Generate) orchestrating the LLM and tool calls.
- **MCP Client**: Standardized interface enabling the agent to request tools from the server.
- **Streamable HTTP**: Transport layer enabling cross-container communication.
- **MCP Server**: Houses the available tools and safely abstracts access to the data layer.
- **Mock Jira repository/tools**: Simulates an actual Jira environment to fetch data without needing real credentials during the POC.
- **LLM**: Analyzes the context and generates the final, structured JSON knowledge response.

### Deployment & Configuration
- **AWS/EC2 deployment approach**: Cloud hosting environment for testing via AWS Systems Manager (SSM). Deploys via git pull and `docker compose up --build -d`.
- **Docker Compose architecture**: Three containers (`frontend`, `knowledge-agent`, `mcp-server`) on a default bridge network.
- **Current LLM provider/model**: Gemini (`gemini-3.5-flash`), with OpenAI supported via abstraction.
- **MCP transport**: Streamable HTTP over Docker internal networking.
- **Important constraints/decisions**: Mock Jira data is exclusively accessed via MCP tools. Similar-ticket retrieval is deterministic (no vector DBs).

## 4. Completed Phases

### Phase 1 — COMPLETE
- **Objective**: Initial project structure and mock JIRA repository.
- **What was implemented**: Core directories and mock data generation logic.
- **Important files changed**: `mcp-server/src/tools/mock_jira_tools.py`, `shared/models/ticket.py`.
- **Testing performed**: Unit testing for mock data retrieval.
- **Acceptance result**: Verified mock ticket retrieval.
- **Relevant commit hash**: Early project commits.

### Phase 2 — COMPLETE
- **Objective**: MCP Server implementation.
- **What was implemented**: Standardized Model Context Protocol server exposing tools.
- **Important files changed**: `mcp-server/src/server/main.py`.
- **Testing performed**: Start server and call basic tools.
- **Acceptance result**: Verified tool exposure via MCP.

### Phase 3 — COMPLETE
- **Objective**: FastAPI Backend & MCP Client.
- **What was implemented**: Initial REST API scaffolding and MCP client connectivity.
- **Important files changed**: `knowledge-agent/src/api/main.py`, `knowledge-agent/src/mcp_client/client.py`.
- **Testing performed**: Client-to-server connection check.
- **Acceptance result**: Verified MCP client connection.

### Phase 4 — COMPLETE
- **Objective**: Dockerization & Streamable HTTP.
- **What was implemented**: Replaced stdio MCP with Streamable HTTP. Created `docker-compose.yml`.
- **Important files changed**: `docker-compose.yml`, `knowledge-agent/Dockerfile`, `mcp-server/Dockerfile`.
- **Testing performed**: Docker network connectivity tests.
- **Acceptance result**: Verified cross-container bridge network communication.

### Phase 5 — COMPLETE
- **Objective**: LangGraph Workflow & Tool Integration.
- **What was implemented**: Deterministic LangGraph state machine (Understand -> Retrieve -> Generate).
- **Important files changed**: `knowledge-agent/src/agent/agent.py`.
- **Testing performed**: Executing the node graph manually.
- **Acceptance result**: Verified LangGraph state transitions.

### Phase 6 — COMPLETE
- **Objective**: LLM Integration & E2E Validation.
- **What was implemented**: LLM abstraction (Gemini/OpenAI), Gemini integration, strict Pydantic structured output.
- **Important files changed**: `knowledge-agent/src/agent/llm_factory.py`, `src/core/config.py`.
- **Testing performed**: End-to-end "Help me understand PROJ-1002".
- **Acceptance result**: Verified PROJ-1002 end-to-end response.

### Phase 7 — COMPLETE
- **Objective**: Knowledge Agent/MCP integration refinement and verification.
- **What was implemented**: 
  - MCP client resilience improvements with `asyncio.Lock` to protect shared state across concurrent requests.
  - `ensure_connected` auto-reconnect logic to recover gracefully if the MCP server restarts.
  - Strict separation of transport/session error handling (which triggers disconnects) vs tool logic error handling (which keeps connections alive).
  - Preserved LangGraph workflow by translating ToolInvocationError appropriately.
- **Important files changed**: `knowledge-agent/src/agent/agent.py`, `knowledge-agent/src/mcp_client/client.py`, `knowledge-agent/tests/test_mcp_client.py`.
- **Testing performed**: 
  - 7 new pytest unit tests added/modified in `test_mcp_client.py`.
  - Tested transport drops, logic errors, concurrent reconnects, and timeouts.
  - EC2/SSM validation via a simulated bash script checking HTTP behavior under Docker container restarts.
- **Acceptance result**: 
  - Happy-path PROJ-1002 regression passed.
  - MCP disconnect test passed (graceful failure).
  - MCP recovery/reconnect test passed (subsequent query reconnected and succeeded).
- **Relevant commit hash**: bb7c9e4

## 5. Current Repository State
- **Current branch**: main
- **Current HEAD commit**: ba02b2f docs: update PROJECT_HANDOFF.md for Phase 10 completion
- **Working tree is clean**: No — Phase 11 implementation and tests are pending review
- **Origin/main synchronized at baseline commit**: Yes (`ba02b2f`); Phase 11 changes have not been committed or pushed

## 6. Phase 8 — COMPLETE

**Phase 8: Historical/similar-ticket retrieval refinement**
- **Objective**: Improve the Mock Jira deterministic retrieval logic for finding related issues.
- **Algorithm Changes**:
  - Filtered generic stop-words without removing technical terms (e.g. `timeout`, `bug`, `error` retained).
  - Adjusted retrieval weights: Service=5, Components=4, Summary=3, Labels=2, Description=1.
  - Implemented stable secondary/tertiary sorts by score and ticket key to ensure 100% deterministic ordering.
- **Dataset Changes**:
  - Added test tickets `PROJ-908`, `PROJ-909`, `PROJ-910` as specific edge cases (exact matches, stop-word dominance, label-only matches).
- **Files Changed**:
  - `mcp-server/src/tools/mock_jira_tools.py`
  - `mcp-server/tests/test_mock_jira_tools.py` (New file)
  - `mcp-server/tests/test_tools.py`
- **Tests Added**:
  - `test_find_similar_exact_component_match`
  - `test_find_similar_stop_words_ignored`
  - `test_find_similar_deterministic_ordering`
  - `test_search_tickets_basic`
  - `test_find_similar_technical_terms`
  - `test_find_similar_labels`
- **Test Results**: All tests passed mathematically asserting weights, stop words, deterministic sorting, and edge cases.
- **Docker/EC2 Validation**: Rebuilt Docker Compose on EC2 and successfully ran `curl` for PROJ-1002, validating the LLM used the highly relevant `PROJ-908` ticket.
- **Acceptance Criteria**: `find_similar_tickets` successfully returns highly relevant Mock Jira tickets deterministically.
- **Commit hash**: Will be the HEAD of `test-phase8` when merged to main.

## 7. Phase 9 — COMPLETE

**Phase 9: FastAPI Backend Integration**
- **Objective**: Expose the existing LangGraph Knowledge Agent functionality through a stable REST API, handling errors safely without exposing sensitive internals.
- **Implementation Details**:
  - Validated the existing FastAPI routing (`/query`, `/health`, `/tools`, `/ws`) against Phase 9 requirements.
  - Implemented a custom `RequestValidationError` handler to safely return `422 Unprocessable Entity` without leaking request internals.
  - Implemented a global `Exception` handler to intercept unexpected backend/agent failures and return a sanitized `500 Internal Server Error`, ensuring no API keys or stack traces are ever exposed to the client.
  - Created a robust API test suite covering all endpoints, edge cases (missing/invalid payloads), and internal error propagation using FastAPI's `TestClient`.
- **Files Changed**:
  - `knowledge-agent/src/api/main.py`
  - `knowledge-agent/tests/test_api.py` (New file)
- **Technical Decisions**:
  - Maintained the existing Docker Compose, MCP Streamable HTTP, and LangGraph workflow without introducing new architectural layers.
  - Forced `raise_server_exceptions=False` in `TestClient` to strictly test the 500 error handler output schema.
- **Tests Executed**:
  - `test_health_check`
  - `test_list_tools`
  - `test_query_valid`
  - `test_query_missing_payload`
  - `test_query_invalid_payload`
  - `test_query_internal_error_safe`
  - `test_websocket_flow`
- **Test Results**: All 24 tests across the `knowledge-agent` suite passed (100% success).
- **Docker/EC2/SSM Validation**:
  - Pushed to EC2, rebuilt Docker Compose, and executed API `curl` commands.
  - `/health` correctly returned `status: healthy` and listed MCP tools.
  - `PROJ-1002` regression succeeded, returning the structured knowledge response containing deterministic matching from Phase 8.
  - Simulated a bad request which correctly returned a safe 422 JSON validation error.
- **Security Scan Result**: Passed. No `.env`, secrets, or temporary SSM artifacts were committed.
- **Commit hash**: Will be the HEAD of `test-phase9` when merged to main.

## 8. Phase 10 — COMPLETE

**Phase 10: React Frontend Integration**
- **Objective**: Integrate the existing React frontend chat UI with the FastAPI backend to correctly display the Knowledge Agent's structured response.
- **Implementation Details**:
  - Maintained existing React and Zustand architecture and Docker bridge networking.
  - Re-mapped the `AgentQueryResponse` and `StructuredResponse` TypeScript interfaces to perfectly match the Pydantic schema returned by LangGraph in Phase 6.
  - Rewrote the `AgentResponseRenderer.tsx` to explicitly present all sections: Ticket Summary, What We Know, Similar Historical Tickets, Previous Resolution, Recommended Investigation, Missing Information, and Sources.
  - Created a multi-stage Dockerfile and an `nginx.conf` proxy mapping `/api/` and `/ws` to the FastAPI backend, identical to the Vite development setup.
- **Files Changed**:
  - `frontend/src/types/index.ts`
  - `frontend/src/components/AgentResponseRenderer.tsx`
  - `frontend/src/components/TicketCard.tsx`
  - `frontend/src/store/chatStore.ts`
  - `frontend/Dockerfile`
  - `frontend/nginx.conf`
  - `frontend/vite.config.ts`
  - `frontend/package.json`
  - `frontend/src/__tests__/AgentResponseRenderer.test.tsx`
- **Architecture Changes**: No new architectural layers introduced. Docker Compose was finalized with the Nginx frontend serving the static React app.
- **Technical Decisions**:
  - Added `@testing-library/react` and `jsdom` to support accurate DOM assertions without relying on brittle structure.
  - Addressed React boolean rendering edge-case where `''` or falsy strings render as text nodes by forcing strict boolean casting (`Boolean(missing_info?.trim())`).
- **Tests Performed**:
  - Unit tests for `AgentResponseRenderer` ensuring error states, missing structured_response, complete structures, and empty missing_information omitted properly.
  - Local Vite production build test (`npm run build`).
- **Test Results**: All 4 Vitest UI tests passed. TypeScript compiler passed cleanly.
- **Docker Validation**: Rebuilt Docker Compose stack successfully.
- **EC2/SSM Validation**: Deployed via SSM command `AWS-RunShellScript`. Docker Compose ran successfully, pulling `origin main`.
- **PROJ-1002 End-to-End Validation**: SSM verification confirmed that `curl -s -X POST http://localhost:5173/api/query -d '{"query":"Help me understand PROJ-1002"}'` successfully routes through Nginx to FastAPI, yielding the Knowledge Agent response. (AWS SSM `ResponseCode: 0`).
- **Acceptance Criteria**: The frontend correctly renders all pieces of the structured Knowledge response, loading states work, error states work, and Docker proxy routes effectively. (Passed)
- **Issues Encountered & Fixes**: 
  - `vitest` tests weren't unmounting DOM between cases. Added `afterEach(cleanup)` from testing-library.
  - React was unexpectedly generating DOM elements for falsy strings when evaluating logical `&&`. Fixed by wrapping truthy/falsy check in explicit `Boolean(...)`.
  - EC2 docker compose build failed due to missing `@testing-library/react` in `package.json`. Committed `package.json` and re-deployed successfully.
- **Security Verification**: Clean `git diff`. No credentials, `.env`, SSM b64, or temporary debugging scripts were committed.
- **Commit hash**: eecc894
- **Current branch**: main
- **Current HEAD**: eecc894
- **Origin/main synchronization**: Synchronized.
- **Working tree status**: Clean.

## 9. Phase 11–14

- **Phase 10 — COMPLETE**
- **Phase 11 — IN PROGRESS / NOT FULLY VALIDATED**: End-to-end application integration (CORS, network verification).
- **Phase 12 — NOT STARTED**: Security, validation, error handling, structured logging.
- **Phase 13 — NOT STARTED**: Testing and reliability (increase pytest/vitest coverage).
- **Phase 14 — NOT STARTED**: Final demo preparation and documentation ("Help me understand PROJ-1002" final validation).

### Phase 11 — Local Implementation Record

**Objective**: Verify and prepare the complete supported path without changing the architecture:

```text
Browser -> React/Zustand -> Nginx -> FastAPI -> LangGraph -> MCP client
-> Streamable HTTP -> Mock Jira MCP server -> structured LLM response
-> React AgentResponseRenderer
```

**Local implementation completed so far**:
- CORS now defaults only to the supported direct-development origin, `http://localhost:5173`; legacy `http://localhost:3000` was removed because no active repository consumer uses it.
- CORS credentials were disabled because the frontend does not use cookies, authorization headers, or credentialed fetch requests.
- CORS methods and headers were limited to the actual API contract: `GET`, `POST`, and `Content-Type`.
- `API_CORS_ORIGINS` remains a Pydantic environment setting and is forwarded into the knowledge-agent service by Docker Compose. Its value must be a JSON list when overridden.
- Backend tests were added for the allowed origin, disallowed origin, JSON POST preflight, credentials behavior, and environment configuration.
- WebSocket tests were added for malformed messages, unsupported messages, empty queries, agent query errors, and unavailable-agent handling. Production WebSocket behavior did not need modification.
- Frontend tests were added for the same-origin `/api/query` REST request and Zustand REST fallback when WebSocket is already unavailable.
- Renderer coverage was strengthened to assert all seven structured sections.
- Nginx was inspected and not changed: `/api/` strips the prefix and proxies to `knowledge-agent:8000`; `/ws` forwards the required WebSocket upgrade headers.
- No readiness/healthcheck behavior was added because the possible startup race has not been reproduced.
- No Dockerfile, LangGraph, MCP transport, Mock Jira, LLM, or dependency declaration was changed.

**Files changed**:
- `knowledge-agent/src/core/config.py`
- `knowledge-agent/src/api/main.py`
- `knowledge-agent/tests/test_api.py`
- `frontend/src/__tests__/AgentResponseRenderer.test.tsx`
- `frontend/src/__tests__/AgentRestService.test.ts`
- `frontend/src/__tests__/chatStore.test.ts`
- `docker-compose.yml`
- `docs/PROJECT_HANDOFF.md`

**Local environment prepared**:
- Python 3.13.2 virtual environments created at `knowledge-agent/.venv` and `mcp-server/.venv`.
- Both Python projects installed from their existing `pyproject.toml` declarations with `pip install -e ".[dev]"`.
- No Python lockfile, requirements file, or dependency declaration was created or changed.
- Node.js 20.18.3 and npm 10.8.2 were used for the frontend installation attempt.

**Test and build results**:
- Knowledge-agent baseline: all existing 24 tests reached `PASSED`, but pytest could not exit because its cache provider could not write in the restricted workspace sandbox.
- Knowledge-agent final local run with cache collection disabled: **31 passed**, with two existing Starlette deprecation warnings for the 422 status constant.
- MCP server: **11 passed**.
- Static Compose YAML parsing: passed; `API_CORS_ORIGINS` remains one environment value and `mcp-server` has no `ports` mapping.
- `npm ci`: incomplete. It emitted Node engine warnings and npm's internal `Exit handler never called!` error. The resulting `node_modules` tree has no `.bin`, `vitest`, `tsc`, or Vite executable.
- Frontend Vitest: not runnable (`'vitest' is not recognized`).
- Frontend production build: not runnable (`'tsc' is not recognized`).
- No frontend lockfile or package declaration was modified.
- Docker/Compose/Nginx runtime validation: not run because Docker/WSL are unavailable on the corporate laptop.
- AWS/EC2 validation: not run because this laptop cannot use the AWS CLI through the corporate TLS path.
- Real LLM regression: not run locally; unit tests use mocks and require no real key.

**Mock Jira demonstration boundary**:
- Jira data and Jira-oriented tools are intentionally mocked and read-only because organizational Jira access is unavailable.
- React, Zustand, Nginx, FastAPI, LangGraph, MCP client/server, Streamable HTTP, structured validation, and rendering are real application components.
- The canonical supported demonstration is `Help me understand PROJ-1002`.
- The deterministic tool path is `get_ticket(PROJ-1002)` followed by `find_similar_tickets(PROJ-1002)`; `PROJ-908` is the deterministic top historical match.
- Generic UI examples that do not contain a ticket ID remain outside Phase 11 scope.

**Known risks still requiring validation**:
- Docker `depends_on` provides start order but not readiness. Repeated cold starts must determine whether the MCP startup race is reproducible before any healthcheck/readiness change is considered.
- The frontend dependency tree must be installed and tested in a supported Node environment; local Node 20.18.3 does not satisfy several locked packages' reported engine requirements.
- The configured provider/model and approved runtime key must be validated on EC2 without exposing the key.
- CORS middleware does not enforce WebSocket origins; Phase 11 validates the supported same-origin Nginx route only.
- Host port 8000 remains published for existing diagnostics. MCP port 8001 must remain internal.

### Phase 11 EC2 Validation Runbook — Still Required

Use AWS Console Session Manager, Systems Manager Run Command, AWS CloudShell, or another authorized machine. Do not use `--no-verify-ssl`, do not widen security groups, and do not put secrets in Git or command arguments.

1. Confirm and update the repository after an approved Phase 11 commit exists:

```bash
sudo -iu ubuntu
REPO_DIR=/home/ubuntu/AI-Knowledge-Agent
test -d "$REPO_DIR/.git"
cd "$REPO_DIR"

git status --short --branch
git branch --show-current
git fetch origin main
git log --oneline -10

APPROVED_COMMIT=<approved-phase-11-commit>
test "$(git rev-parse origin/main)" = "$APPROVED_COMMIT"
git pull --ff-only origin main
test "$(git rev-parse HEAD)" = "$APPROVED_COMMIT"
```

2. Verify Docker and Compose, then validate the Compose model without printing resolved secrets:

```bash
docker --version
docker compose version
docker info
docker compose config -q
```

3. Configure the selected LLM credential outside the repository. Prefer an existing approved secret manager. If none exists, use a permission-restricted file without typing the key into command history:

```bash
RUNTIME_DIR=/home/ubuntu/.config/ai-knowledge-agent
RUNTIME_ENV="$RUNTIME_DIR/runtime.env"
install -d -m 700 "$RUNTIME_DIR"
umask 077
read -rsp "Google API key: " DEMO_GOOGLE_KEY
echo
printf 'LLM_PROVIDER=gemini\nLLM_MODEL=gemini-3.5-flash\nGOOGLE_API_KEY=%s\n' \
  "$DEMO_GOOGLE_KEY" > "$RUNTIME_ENV"
unset DEMO_GOOGLE_KEY
chmod 600 "$RUNTIME_ENV"
stat -c '%a %U %n' "$RUNTIME_ENV"
```

Never print or commit `runtime.env`.

4. Build and start the three-container stack:

```bash
docker compose --env-file "$RUNTIME_ENV" build
docker compose --env-file "$RUNTIME_ENV" up -d
docker compose ps
```

5. Verify direct FastAPI and Nginx REST routing:

```bash
curl -fsS http://localhost:8000/health | python3 -m json.tool
curl -fsS http://localhost:5173/api/health | python3 -m json.tool
curl -fsS http://localhost:5173/api/tools | python3 -m json.tool
curl -fsSI http://localhost:5173/
```

Expected: health is `healthy`, `mcp_connected` is true, and all five tools are listed.

6. Verify Docker DNS and that MCP port 8001 remains internal:

```bash
docker compose exec -T knowledge-agent python -c "import socket; print(socket.gethostbyname('mcp-server')); s=socket.create_connection(('mcp-server',8001),5); print('mcp-server:8001 reachable internally'); s.close()"
docker inspect -f '{{json .NetworkSettings.Ports}}' knowledge-agent-mcp-server
docker compose port mcp-server 8001
```

Expected: internal DNS/socket connectivity succeeds; there is no host binding for 8001.

7. Verify the canonical REST query through Nginx:

```bash
QUERY_RESULT=$(mktemp /tmp/phase11-query.XXXXXX.json)
curl -fsS -X POST http://localhost:5173/api/query \
  -H 'Content-Type: application/json' \
  --data '{"query":"Help me understand PROJ-1002"}' \
  -o "$QUERY_RESULT"
python3 -m json.tool "$QUERY_RESULT"
python3 - "$QUERY_RESULT" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "ticket_summary",
    "what_we_know",
    "similar_historical_tickets",
    "previous_resolution",
    "recommended_investigation",
    "missing_information",
    "sources",
}
assert data["success"] is True
assert required <= set(data["structured_response"])
print("PROJ-1002 structured REST response: PASS")
PY
rm -f "$QUERY_RESULT"
```

8. Verify malformed/error handling and a valid query through the host-published Nginx WebSocket path:

```bash
BACKEND_IMAGE=$(docker compose images -q knowledge-agent)
docker run --rm --network host "$BACKEND_IMAGE" python - <<'PY'
import asyncio
import json
import websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:5173/ws", open_timeout=10) as ws:
        await ws.send("not-json")
        invalid = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        assert invalid["type"] == "error"

        await ws.send(json.dumps({"type": "ping", "payload": {}}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        assert pong["type"] == "pong"

        await ws.send(json.dumps({
            "type": "query",
            "payload": {"query": "Help me understand PROJ-1002"},
        }))
        thinking = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
        assert thinking["type"] == "thinking"
        assert response["type"] == "response"
        assert response["payload"]["success"] is True
        print("Nginx WebSocket PROJ-1002 flow: PASS")

asyncio.run(main())
PY
```

9. Verify CORS directly against FastAPI. The same-origin Nginx browser path does not require CORS:

```bash
curl -sS -D - -o /dev/null \
  -H 'Origin: http://localhost:5173' \
  http://localhost:8000/health

curl -sS -D - -o /dev/null \
  -H 'Origin: http://localhost:3000' \
  http://localhost:8000/health

curl -sS -D - -o /dev/null -X OPTIONS \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: Content-Type' \
  http://localhost:8000/query
```

Expected: only `localhost:5173` receives `Access-Control-Allow-Origin`; the preflight permits POST and Content-Type; credentials are not allowed.

10. Inspect safe logs and perform browser evidence collection:

```bash
docker compose logs --since 10m --no-color frontend knowledge-agent mcp-server
```

Capture `docker compose ps`, `/api/health`, `/api/tools`, REST JSON, WebSocket PASS output, internal-only MCP port evidence, and browser screenshots showing all seven rendered sections. Do not collect environment dumps or secrets.

11. Conditional startup-readiness test, only during an approved validation window:

```bash
docker compose --env-file "$RUNTIME_ENV" down
docker compose --env-file "$RUNTIME_ENV" up -d
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://localhost:5173/api/health; then
    break
  fi
  sleep 3
done
docker compose ps
```

Repeat cold startup sufficiently to determine whether FastAPI can remain degraded after MCP starts. Do not add healthchecks/readiness unless this failure is actually reproduced.

**Phase 11 completion status**: NOT COMPLETE. Local backend/MCP validation has passed, but frontend tests/build and the required Docker/Compose/Nginx/MCP/LLM/EC2 REST and WebSocket validation remain outstanding. Phase 12 must not start.

## 10. Continuation Instructions for Future Agents
**CONTINUATION INSTRUCTIONS FOR FUTURE AGENTS**
1. Read `docs/PROJECT_HANDOFF.md` before doing anything.
2. Read `README.md`.
3. Run `git status`.
4. Run `git log --oneline -15`.
5. Verify current branch and `origin/main`.
6. Inspect the current phase status.
7. Never assume a phase is complete unless documented and supported by Git/repository state.
8. Do not redo completed phases.
9. Continue from the first phase marked **NEXT / NOT STARTED**.
10. Preserve existing architecture and constraints unless the user explicitly approves a change.
11. Never expose or commit secrets.
12. Never commit `.env`.
13. Do not create temporary debugging/SSM files in the repository.
14. Keep temporary scripts outside the repository or delete them before committing.
15. After completing every phase, update `docs/PROJECT_HANDOFF.md` BEFORE moving to the next phase.
16. Commit the handoff update together with the phase completion or in a dedicated documentation commit.
17. Push the updated state to `origin/main`.
18. Leave the working tree clean.

## 11. Phase Completion Protocol
For EVERY phase:

**BEFORE:**
- Read `PROJECT_HANDOFF.md`
- Confirm previous phase is complete
- Create implementation plan
- Wait for user approval when implementation approval is required

**DURING:**
- Implement only the current phase
- Do not modify unrelated architecture
- Test incrementally

**AFTER:**
- Run tests
- Run relevant EC2/SSM validation if required
- Verify no secrets
- Update `PROJECT_HANDOFF.md`
- Update `README/docs` if appropriate
- Record files changed
- Record tests/results
- Record acceptance criteria
- Record commit hash
- Push to `origin/main`
- Verify git status is clean
- Only then declare the phase complete

## 12. Laptop-to-Laptop Continuation
This project may be continued from multiple developer machines. 
The repository is the permanent source of truth.

A future developer/agent should be able to:
```bash
git clone <repo>
cd AI-Knowledge-Agent
git checkout main
git pull origin main
```
Then read:
`docs/PROJECT_HANDOFF.md`
and continue from the documented **NEXT** phase.

**Do NOT rely on Antigravity's local chat history, brain files, temporary artifacts, or IDE-specific state.**

## 13. Security
- `.env` must remain untracked.
- API keys must never be committed.
- AWS credentials must never be committed.
- `GOOGLE_API_KEY` must only exist in runtime environment.
- `OPENAI_API_KEY` must only exist in runtime environment when OpenAI is selected.
- Frontend must never receive LLM API keys.
- MCP server must not receive LLM API keys.
- Temporary SSM/debug files must not be committed.

## 14. Known Issues / Fixes
- **MCP stdio → Streamable HTTP**: Docker containerization required migrating to Streamable HTTP.
- **CallToolResult isError compatibility issue**: Addressed attribute names (`isError` vs `is_error`) dynamically.
- **EC2 Git/SSM permission synchronization issue**: Fixed by ensuring git commands execute via `sudo -u ubuntu`.
- **Docker bridge communication**: Fixed by referencing containers by service name.
- **Concurrent FastAPI connections**: Fixed by adding `asyncio.Lock()` to `MCPClient` lifecycle during Phase 7.

## 15. Important Engineering Constraints
- Jira data must be accessed through MCP.
- Knowledge Agent must not directly access MockJiraRepository.
- MCP communication uses Streamable HTTP.
- Similar-ticket retrieval is deterministic and does not use embeddings/vector DB unless explicitly introduced.
- Structured output must remain validated.
- Do not break completed phases while implementing later phases.
- Do not rewrite Git history unless explicitly approved.
