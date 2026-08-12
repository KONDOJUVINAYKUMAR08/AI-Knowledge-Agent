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

## 10. Phase 7-14
Phase definition not recoverable from repository; must be recovered from project history/context before implementation.

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
