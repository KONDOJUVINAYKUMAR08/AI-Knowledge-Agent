# Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- pip or uv

## 1. MCP Server Setup

```powershell
cd mcp-server
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

Run:
```powershell
python -m src.server.main
```

Test (direct stdio):
```powershell
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m src.server.main
```

Run tests:
```powershell
pytest tests/ -v
```

## 2. Knowledge Agent Setup

```powershell
cd knowledge-agent
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

Run:
```powershell
uvicorn src.api.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Test:
```powershell
# Health check
curl http://localhost:8000/health

# Query the agent
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{"query": "Show me PROJ-1001"}'

# List tools
curl http://localhost:8000/tools
```

Run tests:
```powershell
pytest tests/ -v
```

## 3. Frontend Setup

```powershell
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open: http://localhost:5173

## Environment Variables

### MCP Server (mcp-server/.env)
| Variable | Default | Description |
|---|---|---|
| MCP_SERVER_NAME | knowledge-agent-mcp-server | Server identity |
| LOG_LEVEL | INFO | Logging level |
| LOG_FORMAT | json | json or console |

### Knowledge Agent (knowledge-agent/.env)
| Variable | Default | Description |
|---|---|---|
| API_PORT | 8000 | FastAPI listen port |
| MCP_SERVER_SCRIPT_PATH | ../mcp-server/src/server/main.py | Path to MCP server |
| MCP_SERVER_PYTHON | python | Python executable |
| LOG_FORMAT | console | json or console |

## Replacing Mock Tools with Real Jira

When Jira credentials are available:

1. Create `mcp-server/src/tools/jira_tools.py`
2. Add Jira SDK: `pip install jira`
3. In `mcp-server/src/server/main.py`, replace:
   ```python
   from src.tools.mock_jira_tools import register_mock_jira_tools
   # with:
   from src.tools.jira_tools import register_jira_tools
   ```
4. That's it. Zero changes to the Knowledge Agent or Frontend.
