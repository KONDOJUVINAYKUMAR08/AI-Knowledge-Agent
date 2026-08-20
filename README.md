# AI Knowledge Agent for Jira

An operational knowledge assistant that helps junior engineers understand and investigate Jira incidents. The current Jira source is a deterministic, realistic in-memory repository; the application boundary is designed so a future real Jira repository can replace it without changing the agent or frontend.

This repository is a production-oriented simulation, not a connection to organizational Jira. It does not directly inspect clusters, logs, metrics, databases, Kafka, Redis, DataPower, or cloud APIs.

## Architecture

```text
Browser
  -> React / Zustand
  -> Nginx (:80)
       -> /api/* -> FastAPI (:8000)
       -> /ws    -> FastAPI WebSocket (:8000)
  -> LangGraph Knowledge Agent
  -> MCP client
  -> Streamable HTTP
  -> MCP server (:8001, Docker-internal only)
  -> JiraRepository
  -> MockJiraRepository
```

The Knowledge Agent never imports or accesses `MockJiraRepository`. Jira data is available to it only through MCP.

## Supported capabilities

The production-facing MCP tool set contains exactly three operational tools:

- `get_ticket(ticket_key)` — retrieve a normalized Jira ticket.
- `search_tickets(...)` — search by text, status, priority, issue type, service, environment, platform, cluster, labels, and components.
- `find_similar_tickets(ticket_key)` — return deterministic resolved matches with scores, reasons, prior resolutions, and applicability guidance.

Example requests:

- `Get PROJ-1002`
- `Find critical Kafka incidents`
- `Find Redis incidents in production`
- `Find similar incidents to PROJ-1002`
- `Help me understand PROJ-1002`
- `What can you help me with?`

The canonical investigation remains `PROJ-1002`; `PROJ-908` is its deterministic top historical match.

## Structured investigation response

An investigation returns seven validated sections:

1. Ticket Summary
2. What We Know
3. Similar Historical Tickets
4. Previous Resolution
5. Recommended Investigation
6. Missing Information
7. Sources

The LLM receives only retrieved Jira evidence. Its cited ticket keys are checked against the retrieved current and historical tickets before a response is accepted.

## Components and ports

| Component | Responsibility | Published port |
|---|---|---:|
| `frontend/` | React UI and Nginx reverse proxy | `80` |
| `knowledge-agent/` | FastAPI, LangGraph, LLM abstraction, MCP client | `127.0.0.1:8000` diagnostics only |
| `mcp-server/` | Jira repository boundary and MCP tools | None (`8001` internal only) |

The Vite development server uses port `5173`. It is not the production Docker entry point.

## Docker quick start

Keep runtime credentials outside the repository in a permission-restricted environment file:

```text
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash
GOOGLE_API_KEY=<configured outside Git>
```

Then run:

```bash
docker compose --env-file /secure/path/runtime.env config -q
docker compose --env-file /secure/path/runtime.env build
docker compose --env-file /secure/path/runtime.env up -d
docker compose ps
```

Open `http://localhost/`. Verify:

```bash
curl -fsS http://localhost/api/health
curl -fsS http://localhost/api/tools
curl -fsS -X POST http://localhost/api/query \
  -H 'Content-Type: application/json' \
  --data '{"query":"Help me understand PROJ-1002"}'
```

See [docs/setup.md](docs/setup.md) for local development, WebSocket examples, tests, and configuration.

## LLM providers

Application logic is provider-neutral. Supported settings are:

```text
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash
GOOGLE_API_KEY=...
```

or:

```text
LLM_PROVIDER=openai
LLM_MODEL=<approved OpenAI model>
OPENAI_API_KEY=...
```

or:

```text
LLM_PROVIDER=groq
LLM_MODEL=<Groq chat model ID>
GROQ_API_KEY=...
```

Provider calls have explicit timeouts, application-managed retry/backoff, strict structured-output validation, and sanitized failure responses. Never place keys in frontend variables, source files, Git, or chat messages.

## Real Jira migration path

The provider-neutral contract is `mcp-server/src/jira/repository.py`. Real Jira integration should:

1. Implement `RealJiraRepository` with `get_ticket`, `search_tickets`, and `find_similar_tickets`.
2. Normalize Jira API/JQL results into the existing Jira domain models.
3. Select the implementation in `mcp-server/src/jira/factory.py` through configuration.
4. Configure Jira endpoint and credentials outside Git.

MCP tools, the Knowledge Agent, REST/WebSocket contracts, and frontend should not need redesign.

## Quality gates

```bash
# knowledge-agent
python -m pytest -q -p no:cacheprovider
ruff check --no-cache src tests

# mcp-server
python -m pytest -q -p no:cacheprovider
ruff check --no-cache src tests

# frontend (Node 22.22.2)
npm ci
npm test -- --run
npm run build

git diff --check
```

Current validation evidence and outstanding EC2 gates are maintained in [docs/PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md).

## Current limitations

- Jira data is deterministic mock data; real Jira access is not implemented.
- A configured provider credential is required for investigation responses.
- Authentication, TLS termination, and enterprise authorization are deployment responsibilities not implemented in this POC.
- Docker/frontend Node 22 validation must be completed for the current operational refactor before it can be declared production-ready.
- The remaining EC2 cold-start/log/Security Group evidence must not be inferred from local testing.
