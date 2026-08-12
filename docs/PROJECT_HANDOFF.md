# AI Knowledge Agent - Project Handoff

## 1. Project Identity
- **Repository name**: AI-Knowledge-Agent
- **GitHub remote**: https://github.com/KONDOJUVINAYKUMAR08/AI-Knowledge-Agent.git
- **Current branch**: main
- **Current HEAD commit**: 91e39d8 chore: remove temporary debugging artifacts
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

## 4. Phase 1-6 Status

| Phase | Status | What was implemented | Important files | Verification |
|---|---|---|---|---|
| 1 | Completed | Initial project structure and mock JIRA repository | `mcp-server/src/tools/mock_jira_tools.py`, `shared/models/ticket.py` | Verified mock ticket retrieval |
| 2 | Completed | MCP Server implementation | `mcp-server/src/server/main.py` | Verified tool exposure via MCP |
| 3 | Completed | FastAPI Backend & MCP Client | `knowledge-agent/src/api/main.py`, `knowledge-agent/src/mcp_client/client.py` | Verified MCP client connection |
| 4 | Completed | Dockerization & Streamable HTTP | `docker-compose.yml`, `knowledge-agent/Dockerfile`, `mcp-server/Dockerfile` | Verified bridge network communication |
| 5 | Completed | LangGraph Workflow & Tool Integration | `knowledge-agent/src/agent/agent.py` | Verified LangGraph state transitions |
| 6 | Completed | LLM Integration & E2E Validation | `knowledge-agent/src/agent/llm_factory.py`, `src/core/config.py` | Verified PROJ-1002 end-to-end response |

**Phase 6 Details (Verified):**
- Gemini/OpenAI provider abstraction
- Gemini as current default provider
- gemini-3.5-flash as current configured model
- langchain-google-genai
- LangGraph
- LangChain
- MCP Streamable HTTP
- `get_ticket`
- `search_tickets`
- `find_similar_tickets`
- deterministic similar-ticket algorithm
- structured Pydantic response
- CallToolResult compatibility fix (isError vs is_error fallback)
- successful PROJ-1002 end-to-end verification
- successful Gemini LLM invocation
- Phase 6 cleanup
- Phase 6 commits

## 5. Current LLM Configuration

- **Default provider**: Gemini
- **Default model**: gemini-3.5-flash
- **Environment variable**: GOOGLE_API_KEY

**OpenAI remains supported as an alternative:**
- OPENAI_API_KEY
- gpt-4o-mini

Secrets are runtime configuration only and are not committed. The `.env` files must be managed locally or securely injected into the deployment environment.

## 6. Current MCP Architecture
- **MCP server**: Runs as an isolated microservice (`mcp-server`) that provides the tools.
- **MCP client**: Integrated into the Knowledge Agent to invoke tools.
- **Streamable HTTP**: Used as the transport layer.
- **MCP endpoint**: `POST http://mcp-server:8001/mcp`
- **Docker networking**: Containers communicate internally over the `ai-knowledge-agent_default` bridge network.
- **Available tools**: `get_ticket`, `search_tickets`, `find_similar_tickets`, `hello`, `current_time`.
- **Data Access**: The Knowledge Agent accesses Jira data exclusively by invoking MCP tools.
- **Constraint Confirmation**: The Knowledge Agent must not directly access the MockJiraRepository.

## 7. Current Docker Architecture

**Services:**
1. `mcp-server`
   - **Responsibility**: Hosts MCP tools and data.
   - **Port**: 8001 (Internal)
   - **Network**: default bridge
   - **Environment Variables**: LOG_LEVEL, LOG_FORMAT
   - **Receives LLM credentials**: No

2. `knowledge-agent`
   - **Responsibility**: FastAPI backend and LangGraph agent.
   - **Port**: 8000 (Mapped to 8000)
   - **Network**: default bridge
   - **Dependencies**: `mcp-server`
   - **Environment Variables**: API_HOST, API_PORT, LOG_LEVEL, LOG_FORMAT, LLM_PROVIDER, LLM_MODEL, OPENAI_API_KEY, GOOGLE_API_KEY
   - **Receives LLM credentials**: Yes (via `.env` interpolation).

3. `frontend`
   - **Responsibility**: React UI.
   - **Port**: 80 (Mapped to 5173)
   - **Dependencies**: `knowledge-agent`
   - **Receives LLM credentials**: No

## 8. AWS / EC2 Environment
- **EC2 role/purpose**: Cloud hosting environment for testing and verifying the Knowledge Agent POC.
- **SSM usage**: AWS Systems Manager (SSM) is used to securely run deployment commands and retrieve logs without opening SSH ports.
- **Deployment method**: Pull changes via git (`git fetch` and `git reset --hard FETCH_HEAD`), followed by `docker compose up --build -d`.
- **Docker deployment**: Multi-container Docker Compose.
- **Repository location**: `/home/ubuntu/AI-Knowledge-Agent`
- **Required AWS services**: EC2, SSM.
- **Relevant instance configuration**: Linux instance running Docker, AWS SSM Agent. (Operated primarily as the `ubuntu` user).

## 9. Git State
- **Current branch**: main
- **Current HEAD**: 91e39d8 chore: remove temporary debugging artifacts
- **Recent important commits**:
  - `91e39d8 chore: remove temporary debugging artifacts`
  - `7770c8f fix: CallToolResult is_error attribute fallback`
  - `002982e feat: LLM provider abstraction for Gemini and OpenAI`
- **Remote repository**: https://github.com/KONDOJUVINAYKUMAR08/AI-Knowledge-Agent.git
- **State**: Clean

## 10. Phase 7-14 Execution Plan

### Recovered Roadmap

The following is the planned roadmap recovered from the original project definition:

#### Phase 7: Knowledge Agent/MCP integration refinement and verification.
1. **Phase number**: 7
2. **Phase name**: Knowledge Agent/MCP integration refinement and verification
3. **Exact objective**: Refine and harden the communication between the Knowledge Agent and the MCP Server.
4. **Features/tasks to implement**: Ensure robust error handling when tools fail, validate MCP transport stability, and optimize the deterministic prompt usage.
5. **Files/components expected to change**: `knowledge-agent/src/agent/agent.py`, `knowledge-agent/src/mcp_client/client.py`.
6. **AWS resources involved**: EC2 instance, SSM (for testing).
7. **Docker/Kubernetes requirements**: Docker Compose only (no Kubernetes/EKS).
8. **Testing requirements**: Verify error handling with Mock Jira.
9. **Acceptance criteria**: Agent successfully handles MCP disconnects or tool errors gracefully without crashing.
10. **Dependencies on previous phases**: Requires Phase 6 complete.
11. **Decisions or constraints**: Must use Streamable HTTP over Docker bridge network. 

#### Phase 8: Historical/similar-ticket retrieval refinement.
1. **Phase number**: 8
2. **Phase name**: Historical/similar-ticket retrieval refinement
3. **Exact objective**: Improve the Mock Jira deterministic retrieval logic for finding related issues.
4. **Features/tasks to implement**: Expand the keywords, summary, and component-based matching algorithm in the Mock Jira dataset.
5. **Files/components expected to change**: `mcp-server/src/tools/mock_jira_tools.py`, Mock dataset files.
6. **AWS resources involved**: EC2 instance, SSM.
7. **Docker/Kubernetes requirements**: Docker Compose only.
8. **Testing requirements**: Unit tests for the deterministic algorithm matching.
9. **Acceptance criteria**: `find_similar_tickets` returns highly relevant Mock Jira tickets deterministically.
10. **Dependencies on previous phases**: Requires Phase 7 complete.
11. **Decisions or constraints**: Similar-ticket retrieval is deterministic and does NOT use embeddings/vector DB unless explicitly approved.

#### Phase 9: FastAPI backend integration.
1. **Phase number**: 9
2. **Phase name**: FastAPI backend integration
3. **Exact objective**: Expose the LangGraph Knowledge Agent functionality via a stable REST API.
4. **Features/tasks to implement**: Define FastAPI routes (e.g., `/query`), request/response Pydantic schemas, and integrate the agent invocation.
5. **Files/components expected to change**: `knowledge-agent/src/api/main.py`, `knowledge-agent/src/api/routers/`.
6. **AWS resources involved**: EC2 instance, SSM.
7. **Docker/Kubernetes requirements**: Docker Compose (knowledge-agent container port 8000).
8. **Testing requirements**: API endpoint tests (e.g., pytest with FastAPI TestClient).
9. **Acceptance criteria**: The API successfully receives a query and returns the structured LLM response.
10. **Dependencies on previous phases**: Requires Phase 8 complete.
11. **Decisions or constraints**: The backend must safely manage the runtime API keys without exposing them.

#### Phase 10: React frontend integration.
1. **Phase number**: 10
2. **Phase name**: React frontend integration
3. **Exact objective**: Connect the React chat UI to the FastAPI backend.
4. **Features/tasks to implement**: Implement API service calls in React, handle loading states, and display the structured output (Summary, Previous Resolution, Guidance).
5. **Files/components expected to change**: `frontend/src/` (components, services, Zustand store).
6. **AWS resources involved**: EC2 instance, SSM.
7. **Docker/Kubernetes requirements**: Docker Compose (frontend container port 80).
8. **Testing requirements**: Frontend unit tests / rendering tests.
9. **Acceptance criteria**: User can type a query in the UI and see the agent's response formatted correctly.
10. **Dependencies on previous phases**: Requires Phase 9 complete.
11. **Decisions or constraints**: Frontend must NEVER receive LLM API keys.

#### Phase 11: End-to-end application integration.
1. **Phase number**: 11
2. **Phase name**: End-to-end application integration
3. **Exact objective**: Verify the complete pipeline from React UI to FastAPI to LangGraph to MCP to Mock Jira to LLM and back.
4. **Features/tasks to implement**: System integration testing, CORS configuration, and network routing verification.
5. **Files/components expected to change**: `docker-compose.yml`, frontend API config, FastAPI CORS middleware.
6. **AWS resources involved**: EC2 instance, SSM.
7. **Docker/Kubernetes requirements**: Complete Docker Compose orchestration.
8. **Testing requirements**: End-to-end manual and automated integration testing.
9. **Acceptance criteria**: Seamless data flow across all 3 containers without network or CORS errors.
10. **Dependencies on previous phases**: Requires Phase 10 complete.
11. **Decisions or constraints**: No Kubernetes, standard Docker Compose bridge networking.

#### Phase 12: Security, validation, error handling and observability.
1. **Phase number**: 12
2. **Phase name**: Security, validation, error handling and observability
3. **Exact objective**: Ensure the application is "production-grade" for a POC (clean architecture, safe handling).
4. **Features/tasks to implement**: Structured JSON logging (structlog), input validation, safe error messages to the frontend.
5. **Files/components expected to change**: Middleware, logging configurations across all containers.
6. **AWS resources involved**: EC2 instance, SSM.
7. **Docker/Kubernetes requirements**: Docker Compose logs.
8. **Testing requirements**: Ensure errors do not leak stack traces or secrets to the UI.
9. **Acceptance criteria**: Clean structured logs, no sensitive data leakage.
10. **Dependencies on previous phases**: Requires Phase 11 complete.
11. **Decisions or constraints**: Do not add technologies merely to make the project look complicated (no Kafka, etc.).

#### Phase 13: Testing and reliability.
1. **Phase number**: 13
2. **Phase name**: Testing and reliability
3. **Exact objective**: Stabilize the application for the final demo.
4. **Features/tasks to implement**: Increase test coverage (pytest, vitest), ensure reliable container restartability.
5. **Files/components expected to change**: `tests/` directories across frontend, backend, and mcp-server.
6. **AWS resources involved**: EC2 instance.
7. **Docker/Kubernetes requirements**: `restart: always` or `unless-stopped` in Docker Compose.
8. **Testing requirements**: Run full test suites.
9. **Acceptance criteria**: Tests pass reliably, containers restart correctly on failure.
10. **Dependencies on previous phases**: Requires Phase 12 complete.
11. **Decisions or constraints**: Keep it simple and reliable.

#### Phase 14: Final demo preparation and documentation.
1. **Phase number**: 14
2. **Phase name**: Final demo preparation and documentation
3. **Exact objective**: Prepare the POC for the manager-approved demonstration.
4. **Features/tasks to implement**: Finalize `README.md`, record demo steps, ensure the "Help me understand PROJ-1002" scenario is flawless.
5. **Files/components expected to change**: `docs/`, `README.md`.
6. **AWS resources involved**: EC2 instance.
7. **Docker/Kubernetes requirements**: Final Docker Compose build.
8. **Testing requirements**: Rehearse demo scenario.
9. **Acceptance criteria**: Demo successfully executes the exact expected workflow for PROJ-1002.
10. **Dependencies on previous phases**: Requires Phase 13 complete.
11. **Decisions or constraints**: Must demonstrate AI Agent + MCP + Jira integration keeping Jira READ-ONLY.

---

### Current State Summary (End of Phase 6)
- Phase 1-6 are complete.
- MCP Server uses Streamable HTTP.
- MCP endpoint is `/mcp`.
- Knowledge Agent communicates with MCP through Docker networking.
- Mock Jira data is accessed through MCP.
- Similar-ticket retrieval is deterministic.
- LangGraph is used for the Knowledge Agent workflow.
- LLM provider abstraction supports Gemini and OpenAI.
- Gemini is currently the default provider.
- Current configured Gemini model is `gemini-3.5-flash`.
- `GOOGLE_API_KEY` is provided only to knowledge-agent at runtime.
- API keys are not committed.
- `.env` is ignored.
- Frontend does not receive the LLM API key.
- Phase 6 was successfully tested end-to-end with PROJ-1002.
- Phase 6 changes were committed and pushed.
- Repository cleanup was completed.
- Working tree is clean.

## 11. Important Engineering Constraints
- Jira data must be accessed through MCP.
- Knowledge Agent must not directly access MockJiraRepository.
- MCP communication uses Streamable HTTP.
- Similar-ticket retrieval is deterministic and does not use embeddings/vector DB unless a later approved phase explicitly introduces them.
- Structured output must remain validated.
- Secrets must never be committed.
- Frontend must never receive LLM API keys.
- MCP server must not receive LLM API keys.
- Do not break completed phases while implementing later phases.
- Do not rewrite Git history unless explicitly approved.

## 12. Known Issues / Fixes
- **MCP stdio → Streamable HTTP**: Initially configured for stdio, but Docker containerization required migrating to Streamable HTTP to allow cross-container communication.
- **CallToolResult isError compatibility issue**: Addressed differing attribute names (`isError` vs `is_error`) across MCP SDK versions by using `getattr(result, "isError", getattr(result, "is_error", False))`.
- **EC2 Git/SSM permission synchronization issue**: SSM runs as `root`, causing `git pull` in the `/home/ubuntu/...` directory to fail due to dubious ownership. Fixed by ensuring git commands execute via `sudo -u ubuntu`.
- **Docker bridge communication**: Fixed by referencing containers by service name (`mcp-server`) instead of `localhost`.

## 13. Continuation Rules
The next AI agent must:
1. Inspect the repository before changing anything.
2. Read this handoff document.
3. Inspect git history.
4. Verify the current application state.
5. Never assume a previous phase is incomplete without evidence.
6. Never repeat completed work unnecessarily.
7. Never delete working functionality.
8. Never expose secrets.
9. Never commit .env.
10. Never push automatically unless explicitly instructed.
11. Complete phases sequentially.
12. Stop at the end of each phase for review unless explicitly instructed to continue.
13. Use the repository as the source of truth if chat history is unavailable.
14. If a phase requirement is unclear, inspect existing project artifacts before making assumptions.

## 14. Exact Starting Point
Phase 1-6 are completed. The next work starts at Phase 7.
Current HEAD commit: 91e39d8
