# Setup Guide

## Prerequisites

- Python 3.12 recommended (projects support Python 3.11+)
- Node.js 22.22.2 for the frontend
- npm 10+
- Docker Engine with Docker Compose for the production-shaped stack

Never commit `.env`, `runtime.env`, Jira credentials, LLM API keys, or AWS credentials.

## Local MCP server

PowerShell:

```powershell
cd mcp-server
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m src.server.main
```

The MCP Streamable HTTP endpoint is `http://localhost:8001/mcp` when run directly. The only tools are `get_ticket`, `search_tickets`, and `find_similar_tickets`.

Run its tests and static checks:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\ruff.exe check --no-cache src tests
```

## Local knowledge-agent API

Create `knowledge-agent/.env` locally from `.env.example`, set an approved LLM credential, and point MCP to the locally running server:

```text
MCP_SERVER_URL=http://localhost:8001/mcp
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash
GOOGLE_API_KEY=<local secret>
```

Then:

```powershell
cd knowledge-agent
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000
```

API documentation is at `http://localhost:8000/docs`.

```powershell
curl.exe -fsS http://localhost:8000/health
curl.exe -fsS http://localhost:8000/tools
curl.exe -fsS -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  --data '{"query":"Find critical Kafka incidents"}'
```

Run its tests and static checks:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\ruff.exe check --no-cache src tests
```

## Local frontend

The frontend uses same-origin `/api` and `/ws` URLs. No frontend environment file or LLM credential is required.

```powershell
cd frontend
node --version  # must satisfy >=22.22.2 <23
npm ci
npm test -- --run
npm run build
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/ws` to the local FastAPI service on port 8000.

## Docker Compose

Use an environment file outside the repository:

```bash
RUNTIME_ENV=/secure/path/runtime.env
docker compose --env-file "$RUNTIME_ENV" config -q
docker compose --env-file "$RUNTIME_ENV" build
docker compose --env-file "$RUNTIME_ENV" up -d
docker compose ps
```

Expected publications:

```text
frontend         0.0.0.0:80->80/tcp
knowledge-agent  127.0.0.1:8000->8000/tcp
mcp-server       8001/tcp (no host binding)
```

Nginx serves the React application at `http://localhost/`, strips `/api/` before proxying to FastAPI, and upgrades `/ws` for WebSocket traffic.

## API contracts

### `GET /health`

Actively checks MCP and reports application status, the three current tools, and configured LLM provider/model status without credentials.

### `GET /tools`

Returns the live MCP tool names, descriptions, and input schemas.

### `POST /query`

Accepts:

```json
{"query": "Help me understand PROJ-1002"}
```

Queries are trimmed, must be non-empty, and have a maximum length of 2,000 characters. Responses include a request ID and either a validated seven-section response or a sanitized error category.

### `GET /ws` upgrade

WebSocket messages use:

```json
{"type":"ping","payload":{"request_id":"request-123"}}
{"type":"query","payload":{"query":"Get PROJ-1002","request_id":"request-124"}}
```

The server emits `pong`, `thinking`, `response`, and sanitized `error` events. Browser origins must be same-origin or explicitly configured in `API_CORS_ORIGINS`.

## Configuration

### MCP server

| Variable | Default | Purpose |
|---|---|---|
| `JIRA_PROVIDER` | `mock` | Repository selected by the Jira factory; only `mock` exists today |
| `MCP_SERVER_NAME` | `knowledge-agent-mcp-server` | MCP server identity |
| `MCP_SERVER_VERSION` | `0.1.0` | MCP server version |
| `LOG_LEVEL` | `INFO` | Log threshold |
| `LOG_FORMAT` | `json` | `json` or `console` |

### Knowledge Agent

| Variable | Default | Purpose |
|---|---|---|
| `MCP_SERVER_URL` | `http://mcp-server:8001/mcp` | MCP Streamable HTTP endpoint |
| `LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `LLM_MODEL` | `gemini-3.5-flash` | Provider model name |
| `GOOGLE_API_KEY` | unset | Gemini credential, backend only |
| `OPENAI_API_KEY` | unset | OpenAI credential, backend only |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-provider-attempt timeout |
| `LLM_MAX_RETRIES` | `2` | Application-managed provider retries |
| `LLM_RETRY_BACKOFF_SECONDS` | `0.5` | Initial exponential-backoff delay |
| `AGENT_TOOL_TIMEOUT_SECONDS` | `30` | MCP operation timeout |
| `AGENT_QUERY_TIMEOUT_SECONDS` | `90` | Overall agent request timeout |
| `API_CORS_ORIGINS` | `["http://localhost:5173"]` | Direct-development browser origins |
| `LOG_LEVEL` | `INFO` | Log threshold |
| `LOG_FORMAT` | `console` | `json` or `console` |

## Real Jira migration

Implement `JiraRepository` in a new `RealJiraRepository`, normalize Jira issue/search/comment/history data into the existing domain models, and add the configured implementation to the repository factory. Do not place Jira-specific access logic in the Knowledge Agent or frontend.

## Troubleshooting

- **Health is degraded:** confirm the MCP server is reachable and the selected LLM credential is configured.
- **No tools are listed:** check `MCP_SERVER_URL` and MCP logs; the expected set is exactly three Jira tools.
- **Frontend is reconnecting:** confirm both `/api/health` and `/ws` reach FastAPI through the same Nginx/Vite origin.
- **Node engine warnings:** use Node 22.22.2; do not force incompatible dependency changes.
- **MCP must remain private:** do not add a Compose `ports` mapping or Security Group rule for 8001.
