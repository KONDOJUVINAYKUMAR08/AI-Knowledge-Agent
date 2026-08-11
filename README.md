# AI Knowledge Agent for Jira

> A production-grade AI Knowledge Agent using the Model Context Protocol (MCP) to communicate with external tools. Initially powered by mock tools, designed for drop-in replacement with real Jira and Confluence integrations.

## Architecture

```
[React Frontend]  ←→  [Knowledge Agent API]  ←→  [MCP Client]  ←→  [MCP Server]  ←→  [Tools]
                            (FastAPI)              (subprocess)      (stdio)         ├── hello()
                                                                                     ├── current_time()
                                                                                     └── get_mock_ticket()
```

## Components

| Component | Description | Port |
|---|---|---|
| `frontend/` | React + TypeScript chat UI | 5173 |
| `knowledge-agent/` | FastAPI backend + MCP Client | 8000 |
| `mcp-server/` | MCP Server with mock tools | stdio |

## Quick Start

```bash
# 1. MCP Server
cd mcp-server
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e .
python -m src.server.main

# 2. Knowledge Agent
cd knowledge-agent
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env
uvicorn src.api.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Replacing Mock Tools with Real Jira

When Jira credentials are available, only `mcp-server/src/tools/jira_tools.py` needs to change. The Knowledge Agent, MCP Client, and Frontend remain untouched.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, WebSockets, `mcp` SDK
- **Frontend**: React 18, TypeScript, Vite, Zustand
- **Protocol**: Model Context Protocol (MCP) over stdio transport
- **Config**: python-dotenv, `.env` files per component
- **Logging**: structlog (JSON structured)
- **Testing**: pytest, pytest-asyncio, vitest

## Project Structure

```
knowledge-agent-poc/
├── knowledge-agent/    # FastAPI AI Agent + MCP Client
├── mcp-server/         # MCP Server + Tools
├── frontend/           # React Chat UI
├── shared/             # Shared Pydantic models
├── docs/               # Architecture & setup docs
└── docker-compose.yml
```
