# AI Knowledge Agent - Project Handoff

## 1. Project Identity
- **Repository name**: AI-Knowledge-Agent
- **GitHub remote**: https://github.com/KONDOJUVINAYKUMAR08/AI-Knowledge-Agent.git
- **Current branch**: main
- **Current HEAD commit**: 04a6086 fix(phase-11): expose production frontend on port 80
- **Current working tree status**: Port-80 implementation is pushed and deployed; this validation evidence update is pending review and commit
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
- **Public HTTP entry point**: EC2 host port `80` maps to the frontend Nginx container on port `80`. Port `5173` remains reserved for the local Vite development server and is no longer the intended EC2 public port.
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
- **Current HEAD commit**: 04a6086 fix(phase-11): expose production frontend on port 80
- **Working tree was clean before this handoff evidence update**: Yes
- **Origin/main synchronized at deployed implementation commit**: Yes (`04a6086dad9005b29b69ca84ff64b82a29b95095`)

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
- The frontend Docker build stage was pinned from Node 20 to `node:22.22.2-alpine` after EC2 Vitest reproduced a `jsdom`/`undici` incompatibility under Node 20. No frontend dependency declaration or lockfile was changed.
- MCP SDK tool schema serialization was corrected from the legacy `inputSchema` attribute to `input_schema`, with the API test fixture updated to match the installed SDK.
- The Compose frontend publication was changed from host `5173` -> container `80` to host `80` -> container `80`. The container-side Nginx listener remains unchanged on port 80; mapping host `80` to container `5173` would be invalid because production Nginx does not listen on 5173.
- No LangGraph, MCP transport, Mock Jira, LLM, Nginx, frontend dependency declaration, or frontend lockfile was changed.

**Files changed**:
- `knowledge-agent/src/core/config.py`
- `knowledge-agent/src/api/main.py`
- `knowledge-agent/tests/test_api.py`
- `frontend/src/__tests__/AgentResponseRenderer.test.tsx`
- `frontend/src/__tests__/AgentRestService.test.ts`
- `frontend/src/__tests__/chatStore.test.ts`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `README.md`
- `docs/PROJECT_HANDOFF.md`

**Phase 11 implementation commits**:
- `122606084347da33ae875da527172c54af7745ab` — `test(phase-11): validate application integration paths`
- `376530cde12891630c33c914ef1124bd728a9ab4` — `fix(phase-11): align frontend build with Node requirements`
- `f56299f5333862cbe25f226ccbe9ccd062873374` — `Fix MCP tool schema handling`
- `04a6086dad9005b29b69ca84ff64b82a29b95095` — `fix(phase-11): expose production frontend on port 80`

**Local environment prepared**:
- Python 3.13.2 virtual environments created at `knowledge-agent/.venv` and `mcp-server/.venv`.
- Both Python projects installed from their existing `pyproject.toml` declarations with `pip install -e ".[dev]"`.
- No Python lockfile, requirements file, or dependency declaration was created or changed.
- Node.js 20.18.3 and npm 10.8.2 were used for the frontend installation attempt.

**Test and build results**:
- Knowledge-agent baseline: all existing 24 tests reached `PASSED`, but pytest could not exit because its cache provider could not write in the restricted workspace sandbox.
- Knowledge-agent final local run with cache collection disabled: **31 passed**, with two existing Starlette deprecation warnings for the 422 status constant.
- MCP server: **11 passed**.
- Final workstation regression at `04a6086`: knowledge-agent **31 passed, 2 warnings in 3.07s** and MCP server **11 passed in 1.37s**.
- Static Compose YAML parsing: passed; `API_CORS_ORIGINS` remains one environment value and `mcp-server` has no `ports` mapping.
- Standard-port configuration was parsed locally and asserted as frontend host `80` -> container `80`, knowledge-agent diagnostic host `8000` -> container `8000`, and no MCP host publication. EC2 `docker compose config -q`, full build, and force-recreate deployment subsequently passed.
- `npm ci`: incomplete. It emitted Node engine warnings and npm's internal `Exit handler never called!` error. The resulting `node_modules` tree has no `.bin`, `vitest`, `tsc`, or Vite executable.
- Final workstation frontend commands remain environment-blocked: `npm test -- --run` returned `'vitest' is not recognized`, and `npm run build` returned `'tsc' is not recognized`. No installation or dependency change was attempted. The Dockerized Node 22.22.2 results below remain the authoritative frontend validation.
- EC2 frontend build stage used Node **v22.22.2**. TypeScript and the Vite production build passed (`514 modules transformed`).
- EC2 frontend Vitest: **3 test files passed, 6 tests passed**. The prior `markAsUncloneable` failure was not present after the Node 22.22.2 remediation.
- No frontend lockfile or package declaration was modified.
- EC2 knowledge-agent container test suite: **31 passed**, with the same two Starlette 422 deprecation warnings. The existing `.[dev]` extras were installed into the running validation container because the production image intentionally excludes test dependencies; no dependency declaration changed.
- Full EC2 Docker Compose build and `up -d --force-recreate`: passed for all three services.
- Nginx `/api/health`: passed with `status: healthy`, `mcp_connected: true`, and five tools.
- Nginx `/api/tools`: passed with all five expected tools and current MCP input schemas.
- Docker DNS and TCP connectivity from `knowledge-agent` to `mcp-server:8001`: passed. `HostConfig.PortBindings` was `{}` and MCP had no host port binding.
- Nginx REST `PROJ-1002` query with the configured Gemini runtime: passed with all seven structured fields and `PROJ-908` as the top historical match.
- Nginx WebSocket validation: malformed JSON error, ping/pong, thinking event, successful structured response, seven fields, and `PROJ-908` all passed.
- EC2 CORS validation: `http://localhost:5173` allowed, legacy `http://localhost:3000` not allowed, POST/Content-Type preflight passed, and credentials were not enabled.
- Runtime environment file remained outside the repository with mode `600`; its contents were not printed.
- The earlier mobile-browser screenshot at the former host port 5173 confirmed six visible response sections and `PROJ-908`; that evidence has been superseded by browser-driven validation against the production port-80 URL.
- Headless Chrome loaded `http://44.201.26.241/` as a real React application, displayed all five MCP tools, showed and then removed the visible `Calling MCP tools...` state, rendered all seven response sections including a visible `SOURCES:` label, and displayed `PROJ-908` for `PROJ-1002`.
- The same browser session submitted `PROJ-9999`, received a clean error without a traceback or internal path, remained usable, and then recovered with another successful `PROJ-1002` response.
- Browser network/console/storage inspection found same-origin `/api/health` and `ws://44.201.26.241/ws` traffic, no calls to ports 8000 or 8001, no internal Docker hostname or LLM endpoint calls, no JavaScript runtime or console errors, and empty local storage, session storage, and cookies. The page separately loads Google Fonts over HTTPS; this is a font dependency, not an LLM call.
- Headless Chrome checks at 1440x900 and 390x844 confirmed visible input/button controls and no horizontal document overflow; the mobile media query hid the sidebar as intended.
- The standard public URL `http://44.201.26.241/` is deployed. EC2 `docker compose ps` showed `0.0.0.0:80->80/tcp`, `docker compose port frontend 80` returned `0.0.0.0:80`, Nginx returned HTTP 200, and `/api/health` was healthy with MCP connected.
- Independent public port-80 checks from the corporate Codex workstation passed for the Nginx page and both built assets, `/api/health`, `/api/tools`, canonical `PROJ-1002` and additional `PROJ-1001` REST responses, and the Nginx WebSocket path. Both public `PROJ-1002` query paths returned all seven structured fields and `PROJ-908`; malformed WebSocket input, empty WebSocket query, invalid `PROJ-9999`, connection reuse, and ping/pong also passed.
- Public REST negative tests passed: empty, missing, wrong-type, over-2,000-character, and malformed-JSON bodies returned 422; unsupported GET `/api/query` returned 405; whitespace-only, invalid-format, and unknown-ticket requests returned sanitized application failures without tracebacks, internal paths, or credential patterns.
- External TCP probes found port 80 reachable and ports 5173, 8000, and 8001 closed or filtered. This proves the obsolete and internal/diagnostic ports were not reachable from this workstation, but does not replace direct inspection of the Security Group rule list.
- One explicit EC2 `docker compose down` followed by `up -d` completed successfully, all three services were running after seven seconds, and the Nginx `/api/health` response was healthy with MCP connected. Additional cycles and safe log review remain pending before concluding that no startup race is reproducible.
- Port 80 was allowed manually in the EC2 Security Group. Browser validation is now complete, so the prior public 5173 rule should be removed if it remains configured. Its exact Security Group rule state was not directly inspectable from the corporate workstation; no AWS resource was changed by Codex.

**Mock Jira demonstration boundary**:
- Jira data and Jira-oriented tools are intentionally mocked and read-only because organizational Jira access is unavailable.
- React, Zustand, Nginx, FastAPI, LangGraph, MCP client/server, Streamable HTTP, structured validation, and rendering are real application components.
- The canonical supported demonstration is `Help me understand PROJ-1002`.
- The deterministic tool path is `get_ticket(PROJ-1002)` followed by `find_similar_tickets(PROJ-1002)`; `PROJ-908` is the deterministic top historical match.
- Generic UI examples that do not contain a ticket ID remain outside Phase 11 scope.

**Known risks still requiring validation**:
- Docker `depends_on` provides start order but not readiness. Repeated cold starts must determine whether the MCP startup race is reproducible before any healthcheck/readiness change is considered.
- The frontend Node incompatibility is resolved and verified on EC2 with Node 22.22.2; the dependency audit still reports four existing vulnerabilities and must not be changed with `npm audit fix --force` as part of Phase 11.
- The configured Gemini provider/model and runtime key successfully produced the EC2 REST and WebSocket structured responses without exposing the key.
- CORS middleware does not enforce WebSocket origins; Phase 11 validates the supported same-origin Nginx route only.
- Host port 8000 remains published for existing diagnostics. MCP port 8001 must remain internal.
- The host-port-80 Compose mapping is deployed and browser/API/WebSocket-regression validated. Local Vite and direct-development CORS remain on `localhost:5173` and are intentionally unchanged. External probing found 5173 closed or filtered, but direct evidence that its Security Group rule was removed is still unavailable.
- Only one of the three required cold-start cycles has been performed. Two additional cycles, including readiness timing and post-start page/tools/REST/WebSocket checks, are required before ruling out the possible MCP startup race.
- Post-validation Docker logs have not been supplied or inspected. Crash/restart-loop/MCP-disconnect/5xx/traceback and secret-pattern log checks remain required on EC2.
- `README.md` still contains older architecture prose referring to subprocess/stdio MCP and Python 3.11. The deployed implementation and this handoff correctly describe Python 3.12 and Streamable HTTP; the README inconsistency is documentation debt for final documentation work and is not evidence of a runtime regression.

### Phase 11 EC2 Validation Record and Remaining Runbook

Use AWS Console Session Manager, Systems Manager Run Command, AWS CloudShell, or another authorized machine. Do not use `--no-verify-ssl`, do not widen security groups, and do not put secrets in Git or command arguments.

The original host-port-5173 forms of steps 1–9 were executed successfully against `f56299f`. The port-80 forms were subsequently executed successfully against `04a6086`, including public REST, public WebSocket, and real-browser regression checks. Safe EC2 log review in step 10 and cold-start cycles 2 and 3 in step 11 are still required.

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

APPROVED_COMMIT=04a6086dad9005b29b69ca84ff64b82a29b95095
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
curl -fsS http://localhost/api/health | python3 -m json.tool
curl -fsS http://localhost/api/tools | python3 -m json.tool
curl -fsSI http://localhost/
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
curl -fsS -X POST http://localhost/api/query \
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
    async with websockets.connect("ws://127.0.0.1/ws", open_timeout=10) as ws:
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

10. Inspect safe logs. Browser evidence collection has passed against the public port-80 URL:

```bash
docker compose logs --since 10m --no-color frontend knowledge-agent mcp-server
```

Review the output for crashes, restart loops, MCP connection failures, unhandled exceptions, unexpected 5xx responses, and credential patterns. Do not collect environment dumps or secrets.

11. Complete cold-start cycles 2 and 3 during an approved validation window. Cycle 1 passed:

```bash
docker compose --env-file "$RUNTIME_ENV" down
docker compose --env-file "$RUNTIME_ENV" up -d
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://localhost/api/health; then
    break
  fi
  sleep 3
done
docker compose ps
```

Repeat cold startup sufficiently to determine whether FastAPI can remain degraded after MCP starts. Do not add healthchecks/readiness unless this failure is actually reproduced.

### Phase 11 Acceptance Status at `04a6086`

- **PASS** — CORS policy is intentional, configurable, and tested for allowed/disallowed origins and preflight behavior.
- **PASS** — Frontend Node 22.22.2 production build and all 6 Vitest tests.
- **PASS** — Knowledge-agent 31-test suite and MCP 11-test suite.
- **PASS** — Full three-service Compose build/start and Nginx `/api/health` and `/api/tools` routing.
- **PASS** — Docker DNS/TCP connectivity to internal-only MCP port 8001, with no host binding.
- **PASS** — Real configured-LLM `PROJ-1002` REST and WebSocket flows through Nginx, all seven structured fields, and deterministic `PROJ-908` match.
- **PASS** — Runtime secret file remained outside Git with restrictive permissions and was not printed.
- **PASS** — Headless Chrome against `http://44.201.26.241/` confirmed a non-blank React UI, five tools, visible loading state, all seven sections including Sources, clean invalid-ticket handling, successful recovery, no runtime/console errors, safe browser storage, and desktop/mobile usability.
- **PASS** — Browser traffic used same-origin `/api` and `/ws`; it did not call ports 8000/8001, internal container names, Gemini, or OpenAI. High-confidence secret scans of public responses and built frontend assets were clean.
- **PARTIAL** — One `docker compose down`/`up -d` cold-start cycle returned to healthy MCP-backed service and the subsequently exercised public page/REST/WebSocket/browser flows passed. Required cycles 2 and 3, readiness timing, and per-cycle evidence remain outstanding.
- **PASS** — Standard HTTP mapping (`EC2 host 80` -> `frontend container 80`) is deployed; public page, `/api/health`, `/api/tools`, canonical REST, and `/ws` checks passed.
- **PARTIAL** — External probes show 80 open and 5173, 8000, and 8001 closed or filtered. Direct Security Group rule inspection is still needed to confirm the obsolete 5173 rule is absent.
- **NOT TESTABLE** — EC2 post-validation Docker log review cannot be performed from this workstation and no log output was supplied.

### Phase 11 Final Validation Matrix

| Area | Requirement / test | Result | Evidence / notes |
|---|---|---|---|
| Repository | Git baseline and synchronization | PASS | `main`, HEAD and `origin/main` are `04a6086dad9005b29b69ca84ff64b82a29b95095`; only this handoff evidence file is modified. |
| Repository | Knowledge-agent tests | PASS | Final workstation run: 31 passed, 2 existing Starlette deprecation warnings. |
| Repository | MCP tests | PASS | Final workstation run: 11 passed. |
| Repository | Frontend Vitest | PASS | EC2 Node 22.22.2 build stage: 3 files and 6 tests passed; the workstation command is not runnable because its incomplete Node 20 install has no `vitest`. |
| Repository | TypeScript and frontend production build | PASS | EC2 Node 22.22.2 Docker build compiled TypeScript and transformed 514 Vite modules successfully; workstation `tsc` is unavailable. |
| Architecture | Mock Jira is accessed only through MCP | PASS | Static search found no `MockJiraRepository` reference in `knowledge-agent`; live tool discovery and query flows used MCP. |
| Architecture | LangGraph and structured output | PASS | Static inspection shows `StateGraph` workflow and structured LLM output; tests and live responses validated all seven fields. |
| Architecture | MCP Streamable HTTP | PASS | Client uses `streamable_http_client`; server exposes its Streamable HTTP application at `/mcp`; live Docker DNS/TCP test passed. |
| Public browser | Nginx page, React UI, and five tools | PASS | Headless Chrome loaded the public port-80 URL with no blank page or runtime/console errors and displayed all five tools. |
| Public browser | Loading state and final rendering | PASS | `Calling MCP tools...` became visible and was removed after the final response. |
| Public browser | Seven sections and Sources | PASS | DOM inspection found Ticket Summary, What We Know, Similar Historical Tickets, Previous Resolution, Recommended Investigation, Missing Information, and visible `SOURCES:`. |
| Public browser | Invalid ticket and recovery | PASS | `PROJ-9999` produced a sanitized visible error; input remained usable and a subsequent `PROJ-1002` query succeeded. |
| Public browser | Desktop/mobile responsiveness | PASS | 1440x900 and 390x844 checks found visible controls and no horizontal document overflow; mobile sidebar behavior passed. |
| Public REST | Health and tools through public Nginx | PASS | Healthy, MCP connected, version present, and exactly five expected tools. |
| Public REST | Canonical `PROJ-1002` | PASS | Success true, all seven fields, useful content, and deterministic `PROJ-908`. |
| Public REST | Additional valid query | PASS | `PROJ-1001` succeeded through public Nginx. |
| Public REST | Negative input matrix | PASS | Empty/missing/type/length/malformed JSON returned 422; unsupported method returned 405; whitespace/invalid/unknown tickets returned clean application failures. |
| Public WebSocket | Public Nginx `/ws` happy path | PASS | Connection, thinking, final success, seven fields, and `PROJ-908` passed at `ws://44.201.26.241/ws`. |
| Public WebSocket | Error handling and connection reuse | PASS | Malformed JSON, empty query, invalid `PROJ-9999`, ping/pong, and valid-query recovery all passed without closing the connection. |
| Docker/EC2 | Compose build/start and port mappings | PASS | Build/force-recreate passed; frontend is host 80 -> container 80, backend retains diagnostic host 8000, and MCP has no host binding. |
| MCP security | Internal DNS/TCP and public isolation | PASS | `knowledge-agent` reached `mcp-server:8001`; `PortBindings` was `{}`; external port 8001 probe was closed or filtered. |
| Network security | Public port exposure | PASS | From the corporate workstation, 80 was open while 5173, 8000, and 8001 were closed or filtered. |
| Security Group | Exact rule-list inspection | NOT TESTABLE | Port 80 was manually enabled, but this workstation cannot inspect AWS; confirm the obsolete 5173 rule is removed and no unnecessary 8000/8001 rule exists. |
| Browser security | Route, console, storage, and frontend secret checks | PASS | Same-origin `/api` and `/ws`, no backend/MCP/LLM direct calls, no runtime/console error, empty browser storage/cookies, and clean response/asset pattern scans. Google Fonts is the only observed external application dependency. |
| Repository security | Tracked/untracked secret artifacts | PASS | No runtime `.env`, `runtime.env`, `cmdId`, or `b64` artifact; no high-confidence tracked key/private-key pattern; no frontend or MCP LLM credential reference. |
| Runtime secrets | EC2 runtime file handling | PASS | Previously verified outside Git, owned by `ubuntu`, mode 600, contents not printed; only the backend receives configured LLM variables. |
| CORS | Allowed/disallowed/preflight/credentials | PASS | Supported localhost:5173 origin allowed, legacy localhost:3000 not allowed, POST/Content-Type preflight passed, credentials disabled. |
| Cold start | Cycle 1 | PASS | Compose down/up succeeded; all services were running after approximately seven seconds and `/api/health` was healthy with MCP connected. |
| Cold start | Cycles 2 and 3 | NOT TESTABLE | Required EC2 operations were not supplied and cannot be initiated from this workstation. |
| Logs | Post-validation service log review | NOT TESTABLE | EC2 logs were not supplied; crashes, restart loops, MCP disconnects, unexpected 5xx, tracebacks, and credential patterns still require safe review. |
| Documentation | README architecture accuracy | PARTIAL | Quick-start port 80 is correct, but older architecture/tech-stack prose still says subprocess/stdio MCP and Python 3.11; implementation and handoff use Streamable HTTP and Python 3.12. |

**Phase 11 completion status**: **NOT COMPLETE**. No public application-path failure remains in the executed evidence. Completion is blocked only by cold-start cycles 2 and 3 with per-cycle page/tools/REST/WebSocket evidence, safe EC2 log review, and direct confirmation of the final Security Group rule set. Phase 12 must not start.

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
