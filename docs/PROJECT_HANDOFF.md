# AI Knowledge Agent — Project Handoff

## 1. Repository state

- **Repository:** `AI-Knowledge-Agent`
- **Remote:** `https://github.com/KONDOJUVINAYKUMAR08/AI-Knowledge-Agent.git`
- **Branch:** `main`
- **Operational-refactor base:** `d7f4d037714a1fc14a81e396932d2e84a4734598` (`docs: update Phase 11 handoff`)
- **Base synchronization:** `HEAD == origin/main` before the refactor began
- **Current checkpoint:** the operational-Jira refactor and this handoff are committed together in the current `main` HEAD (`feat: operationalize Jira knowledge workflows`)
- **Git safety:** the checkpoint was committed and pushed only after explicit user authorization; no branch creation, reset, force-push, amend, or history rewrite was performed

EC2 remains deployed at the earlier `d7f4d03` baseline. The current operational checkpoint has not yet been deployed or validated on EC2.

## 2. Product objective and boundary

The system is an internal-style operational Jira Knowledge Agent intended to help junior engineers understand incidents involving platforms such as EKS, AKS, Kubernetes, Kafka, Redis, IBM DataPower, APIs, microservices, databases, networking, authentication, certificates, and deployment configuration.

It should explain:

- what happened;
- affected service, environment, platform, cluster, region, and severity;
- verified symptoms and known facts;
- relevant resolved historical incidents and their recorded resolutions;
- recommended investigation steps, clearly separated from facts;
- missing evidence; and
- the Jira issue keys used as sources.

Jira remains a deterministic simulation because organizational Jira access is unavailable. The application must not imply that it inspected live infrastructure, logs, metrics, cloud APIs, or a real Jira instance.

## 3. Intended current architecture

```text
Browser
  -> React / Zustand
  -> Nginx (container 80, host 80)
       -> /api/* -> FastAPI (container 8000)
       -> /ws    -> FastAPI WebSocket (container 8000)
  -> LangGraph Knowledge Agent
  -> MCP client
  -> Streamable HTTP
  -> MCP server (container 8001, no host publication)
  -> JiraRepository
  -> MockJiraRepository
```

Docker Compose retains host diagnostics for FastAPI only on `127.0.0.1:8000`. MCP port 8001 has no `ports` mapping.

## 4. Provider-neutral Jira boundary

The current operational checkpoint introduces:

- `JiraRepository`, a provider-neutral protocol for `get_ticket`, `search_tickets`, and `find_similar_tickets`;
- normalized Pydantic domain models for Jira users, comments, history, tickets, search criteria, and explainable similarity matches;
- `MockJiraRepository`, selected by `JIRA_PROVIDER=mock` through a repository factory; and
- dependency injection from the MCP server into the Jira tool registration layer.

The Knowledge Agent has no import of or direct access to `MockJiraRepository`. Future real Jira integration should add a `RealJiraRepository` and factory configuration; the MCP tools, agent, REST/WebSocket contracts, and frontend should remain unchanged.

## 5. Operational mock dataset

The new deterministic dataset contains 15 representative operational tickets. It covers:

- PostgreSQL connection-pool exhaustion;
- EKS readiness, deployment, and pod crash-loop failures;
- AKS DNS/networking failures;
- Kafka consumer lag and TLS/connectivity failures;
- Redis memory pressure and failover connectivity;
- IBM DataPower gateway policy/certificate failures;
- API latency and service-to-service timeouts; and
- authentication and configuration drift.

Normalized fields include key, summary, description, issue type, status, priority, severity, reporter, assignee, created/updated timestamps, labels, components, service, environment, platform, cluster, region, symptoms, comments, history, resolution, affected version, and root cause.

All dataset timestamps are fixed. No import-time `datetime.now()` or random ordering is used. `PROJ-1002` remains the canonical open PostgreSQL pool-exhaustion incident and `PROJ-908` remains its deterministic top resolved match.

## 6. Production-facing MCP tools

The current operational checkpoint exposes exactly three tools:

1. `get_ticket(ticket_key)`
2. `search_tickets(...)`
3. `find_similar_tickets(ticket_key, limit=3)`

The generic `hello` and `current_time` demonstration tools have been removed from registration, health output, UI, tests, and current documentation.

Tool behavior includes Jira-key normalization/validation, structured success/error envelopes, clean not-found handling, operational search filters, bounded limits, stable ordering, and deterministic explainable similarity. Similarity returns scores, match reasons, resolved-history status, recorded previous resolution, and applicability guidance.

## 7. Agent and knowledge workflow

Deterministic intent classification now routes supported natural-language requests through MCP:

- ticket retrieval -> `get_ticket`;
- operational incident search -> `search_tickets`;
- historical similarity -> `find_similar_tickets`;
- ticket investigation -> `get_ticket`, then `find_similar_tickets`, then grounded LLM analysis; and
- capability questions -> a truthful static description without claiming unsupported integrations.

The LangGraph workflow is `understand_request -> execute_tools -> generate_response`. The canonical `Help me understand PROJ-1002` path retrieves the current issue, retrieves historical matches, supplies that evidence to the LLM, and validates the seven-section output.

The grounding prompt separates known facts, recommendations, and missing information. An accepted investigation must cite the current ticket and top historical match, may cite only retrieved Jira keys, and may not mention an un-retrieved Jira key.

## 8. LLM abstraction

- **Default provider/model:** Gemini / `gemini-3.5-flash`
- **Alternative provider:** OpenAI through existing `ChatOpenAI` integration
- **Configuration:** `LLM_PROVIDER`, `LLM_MODEL`, and the selected backend-only API key
- **Controls:** explicit per-attempt timeout, application-managed retry/backoff, overall query timeout, strict structured validation, grounding validation, and sanitized provider errors

Provider SDK retries are disabled so retry behavior is controlled by the application. No key is logged or sent to the frontend or MCP server.

## 9. REST, WebSocket, UI, and observability changes

### REST

- `GET /health` actively probes MCP and reports exactly the live tool set plus safe LLM provider/model/configured status.
- `GET /tools` returns live MCP schemas.
- `POST /query` enforces trimmed non-empty input, a 2,000-character maximum, typed responses, categorized status codes, and request IDs.
- Validation and global exception responses do not echo request bodies or raw exception text.
- Full natural-language queries are not logged.

### WebSocket

- Same-origin or explicitly configured origins are accepted; cross-site browser origins are rejected.
- Ping/pong, query, thinking, response, malformed-message, error, repeated-query, and unavailable-agent paths are covered.
- Backend/provider exception text is not sent to the browser.

### Frontend

- Example prompts describe only implemented Jira capabilities.
- Demo tools and Confluence claims are removed.
- WebSocket handlers survive reconnects; intentional shutdown cancels reconnects. An in-flight startup disconnect now invalidates its pending connection without allowing a delayed stale close event to replace or duplicate the next connection; a frontend regression test covers this path but remains pending execution on Node 22.22.2.
- Connection status, handler/interval cleanup, request correlation, bounded timeout recovery, REST fallback, repeated requests, and recovery after failure are implemented.
- Input is capped at 2,000 characters.
- The seven-section renderer remains the canonical investigation view.
- External Google Font requests were removed; the UI uses local system font stacks.

### Logging

- REST and WebSocket work is correlated by request ID.
- Tool logs record argument names, not unrestricted values.
- Error logs contain categories/types rather than exception messages or tracebacks.
- A recursive structured-log processor redacts key, token, authorization, password, credential, and secret fields.

## 10. Container and proxy changes in the operational checkpoint

- Frontend remains host `80` -> container `80`.
- Backend diagnostic publication is narrowed to `127.0.0.1:8000` -> container `8000`.
- MCP remains internal-only on container port 8001.
- Python application containers run as UID 10001 with all Linux capabilities dropped.
- Services use `no-new-privileges`.
- Base image references use the digests previously observed in the validated EC2 build.
- Frontend uses `npm ci` and the checked-in lockfile.
- Docker contexts exclude environments, virtual environments, caches, tests, and build output as appropriate.
- Nginx keeps the existing `/api/` rewrite and `/ws` upgrade routes, adds bounded proxy timeouts, a request-ID header pass-through, request-size limit, and standard browser security headers.
- No readiness/healthcheck was added because no startup race has been reproduced by the current local work.

## 11. Current validation evidence

### PASS

- Knowledge Agent: **52 tests passed**.
- Knowledge Agent Ruff: **all checks passed**.
- MCP server: **25 tests passed**.
- MCP server Ruff: **all checks passed**.
- Focused rerun: **18 agent/LLM tests passed**, covering all supported routing, grounded investigation, configurable Gemini/OpenAI construction, safe provider failure, malformed output, retry recovery, and timeout handling.
- Focused rerun: **8 MCP tool-contract tests passed**, covering the exact three-tool registration, retrieval, operational search, explainable similarity, input errors, and provider-factory rejection.
- `git diff --check`: passed at the latest checkpoint.
- Compose YAML parsed successfully and statically asserted frontend `80:80`, backend loopback `8000:8000`, and no MCP host publication.
- Frontend `package.json` dependency roots match `package-lock.json`; obsolete `date-fns` code/dependency was removed consistently.
- A real local two-process integration started the MCP Streamable HTTP server and FastAPI, then passed:
  - active health with exactly three tools;
  - live `/tools` schemas;
  - REST ticket retrieval, Kafka search, Redis production search, EKS failed-deployment search, similarity, business-language capabilities, whitespace validation, and clean unknown-ticket handling;
  - request-ID header/body correlation;
  - same-origin public-contract WebSocket connection, malformed-message, ping/pong, repeated thinking/response queries, and `PROJ-908` checks; and
  - safe pattern-based review of both service logs.
- Static searches confirm the Knowledge Agent does not reference `MockJiraRepository` and the MCP server has no import-time nondeterministic ticket generation.

### BLOCKED / NOT VALIDATED FOR THE CURRENT CHECKPOINT

- The system-installed runtime remains Node `20.18.3`, but an official portable Node `22.22.2` archive was downloaded to the system temporary directory, structurally validated, extracted with `tar.exe`, and executed successfully without changing the system installation.
- Under portable Node `22.22.2` and npm `10.9.7`, online `npm ci` and `npm ci --no-audit` both ended with npm's internal `Exit handler never called!` failure after the registry connection stalled/reset. No TLS bypass or alternate registry was used.
- `npm ci --offline --no-audit` reported uncached `zwitch@2.0.4`; no Vitest, TypeScript, or Vite executable was produced. Current frontend Vitest, TypeScript, and Vite production-build results are therefore **pending**.
- Docker is unavailable on this workstation. The modified Dockerfiles, Nginx configuration, and Compose runtime have not been built or started.
- The current investigation flow has not been executed against a real configured LLM after this refactor. Unit tests use controlled LLM doubles; non-LLM intents used the real local MCP/FastAPI transport.
- No current working-tree code has been deployed to EC2.

## 12. Previously deployed baseline evidence

The deployed baseline at `04a6086`/`d7f4d03` previously passed public port-80 page, REST, WebSocket, browser loading/error/recovery, and `PROJ-1002 -> PROJ-908` checks. That evidence applies only to the deployed baseline, not to the current operational checkpoint.

The following original EC2 Phase 11 evidence gates remain pending and must not be inferred:

- cold-start cycle 2;
- cold-start cycle 3;
- safe Docker log review;
- direct Security Group rule inspection; and
- final public browser regression when the current refactor is eventually approved and deployed.

Port 80 should be allowed from the approved source. Public rules for 5173 and 8001 should be absent; 8000 should not be unnecessarily public. Codex made no AWS changes.

## 13. Required next validation

Before any production-ready or deployment-ready claim:

1. On Node 22.22.2, run `npm ci`, `npm test -- --run`, and `npm run build` in `frontend/`.
2. Run `docker compose config -q` with the approved external runtime environment.
3. Build and start all three containers.
4. Verify non-root Python users, capability drops, frontend security headers, host port mappings, and internal MCP DNS/TCP connectivity.
5. Run all three MCP tools through `/api` and `/ws`.
6. With the approved runtime key, run `Help me understand PROJ-1002`; require success, all seven sections, grounded content, and `PROJ-908` first.
7. Exercise browser loading, invalid-ticket recovery, reconnect, repeated queries, desktop/mobile rendering, browser network routes, storage, console, and credential-pattern checks.
8. Perform at least two current-code local cold starts if Docker is available.
9. When EC2 access is approved, collect the five remaining EC2 Phase 11 evidence items above without bypassing TLS.

Do not add readiness logic unless a startup failure is actually reproduced.

## 14. Real Jira readiness and remaining work

The architectural seam is ready for a future Jira implementation, but actual Jira integration still requires:

- approved Jira endpoint and authentication method;
- issue-field mapping and custom-field IDs;
- JQL/search behavior and pagination;
- comments/history permissions and normalization;
- rate-limit, timeout, retry, and audit requirements; and
- enterprise authorization and data-classification decisions.

Do not invent these values and do not integrate real Jira until access and requirements are supplied.

## 15. Security constraints

- Never commit `.env`, `runtime.env`, credentials, API keys, AWS data, SSM artifacts, or debug dumps.
- The frontend must not receive LLM or future Jira credentials.
- The MCP server must not receive LLM credentials.
- MCP port 8001 must remain un-published.
- Do not disable TLS verification.
- Do not force-push, rewrite history, reset, or discard the current operational checkpoint.

## 16. Continuation protocol

1. Read this file and `README.md`.
2. Run `git status`, `git branch --show-current`, `git rev-parse HEAD`, and `git log --oneline -15`.
3. Preserve the current operational checkpoint; do not reset it.
4. Continue from the validation list in section 13.
5. Do not claim AWS, Docker, frontend Node 22, real-LLM, or browser behavior without direct evidence for the current code.
6. Before any eventual commit, show `git status`, `git diff --stat`, `git diff --check`, and a safe tracked/untracked secret scan.
7. Do not commit or push until explicitly authorized by the user.

## 17. Status

- **Operational Jira refactor implementation checkpoint:** COMMITTED TO `main`; external validation remains in progress.
- **Local Python/MCP/API validation:** PASS for the evidence listed above.
- **Frontend Node 22 validation:** PENDING.
- **Docker validation for current code:** PENDING.
- **Real configured-LLM validation for current code:** PENDING.
- **EC2 Phase 11 completion evidence:** PENDING.
- **Production-ready:** NO.
