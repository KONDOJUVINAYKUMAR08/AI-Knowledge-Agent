# AI Knowledge Agent - Project Handoff

## 1. Project Identity
- **Repository name**: AI-Knowledge-Agent
- **GitHub remote**: https://github.com/KONDOJUVINAYKUMAR08/AI-Knowledge-Agent.git
- **Current branch**: main
- **Current HEAD commit**: bb7c9e4 feat(phase-7): refine MCP client integration and robust error handling
- **Current working tree status**: Clean
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
- **Current HEAD commit**: bb7c9e4 feat(phase-7): refine MCP client integration and robust error handling
- **Working tree is clean**: Yes
- **Origin/main synchronized**: Yes

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

## 7. Phase 9–14

- **Phase 9 — NEXT / NOT STARTED**: FastAPI backend integration (REST API schemas).
- **Phase 10 — NOT STARTED**: React frontend integration (connect UI to FastAPI, display structured response).
- **Phase 11 — NOT STARTED**: End-to-end application integration (CORS, network verification).
- **Phase 12 — NOT STARTED**: Security, validation, error handling, structured logging.
- **Phase 13 — NOT STARTED**: Testing and reliability (increase pytest/vitest coverage).
- **Phase 14 — NOT STARTED**: Final demo preparation and documentation ("Help me understand PROJ-1002" final validation).

## 8. Continuation Instructions for Future Agents
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

## 9. Phase Completion Protocol
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

## 10. Laptop-to-Laptop Continuation
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

## 11. Security
- `.env` must remain untracked.
- API keys must never be committed.
- AWS credentials must never be committed.
- `GOOGLE_API_KEY` must only exist in runtime environment.
- `OPENAI_API_KEY` must only exist in runtime environment when OpenAI is selected.
- Frontend must never receive LLM API keys.
- MCP server must not receive LLM API keys.
- Temporary SSM/debug files must not be committed.

## 12. Known Issues / Fixes
- **MCP stdio → Streamable HTTP**: Docker containerization required migrating to Streamable HTTP.
- **CallToolResult isError compatibility issue**: Addressed attribute names (`isError` vs `is_error`) dynamically.
- **EC2 Git/SSM permission synchronization issue**: Fixed by ensuring git commands execute via `sudo -u ubuntu`.
- **Docker bridge communication**: Fixed by referencing containers by service name.
- **Concurrent FastAPI connections**: Fixed by adding `asyncio.Lock()` to `MCPClient` lifecycle during Phase 7.

## 13. Important Engineering Constraints
- Jira data must be accessed through MCP.
- Knowledge Agent must not directly access MockJiraRepository.
- MCP communication uses Streamable HTTP.
- Similar-ticket retrieval is deterministic and does not use embeddings/vector DB unless explicitly introduced.
- Structured output must remain validated.
- Do not break completed phases while implementing later phases.
- Do not rewrite Git history unless explicitly approved.
