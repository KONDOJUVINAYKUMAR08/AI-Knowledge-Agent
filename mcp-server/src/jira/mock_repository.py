"""Deterministic operational Jira repository used until real Jira access is available."""

from __future__ import annotations

import re

from src.jira.models import (
    JiraComment,
    JiraHistoryEntry,
    JiraSearchCriteria,
    JiraTicket,
    JiraUser,
    SimilarTicketMatch,
)
from src.jira.repository import JiraTicketNotFoundError, normalize_ticket_key

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.-]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}

NOC_ENGINEER = JiraUser(account_id="ops-001", display_name="NOC Engineer")
PLATFORM_ENGINEER = JiraUser(account_id="ops-002", display_name="Platform Engineer")
DATABASE_ENGINEER = JiraUser(account_id="ops-003", display_name="Database Engineer")
MIDDLEWARE_ENGINEER = JiraUser(account_id="ops-004", display_name="Middleware Engineer")


def _comment(author: JiraUser, body: str, created: str) -> JiraComment:
    return JiraComment(author=author, body=body, created=created)


def _history(
    timestamp: str,
    author: JiraUser,
    field: str,
    from_value: str | None,
    to_value: str,
) -> JiraHistoryEntry:
    return JiraHistoryEntry(
        timestamp=timestamp,
        author=author,
        field=field,
        from_value=from_value,
        to_value=to_value,
    )


def _build_operational_tickets() -> tuple[JiraTicket, ...]:
    """Build a fixed operational dataset with stable timestamps and values."""

    return (
        JiraTicket(
            id="9001",
            key="PROJ-901",
            summary="API returned 503 errors when PostgreSQL connections queued",
            description=(
                "The production orders API returned intermittent 503 responses during a traffic "
                "increase. Application logs showed PostgreSQL connection acquisition timeouts."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="Critical",
            severity="SEV-1",
            reporter=NOC_ENGINEER,
            assignee=DATABASE_ENGINEER,
            created="2025-11-12T08:10:00Z",
            updated="2025-11-12T13:45:00Z",
            labels=("production", "database", "connection-pool", "api"),
            components=("Orders API", "PostgreSQL"),
            service="orders-api",
            environment="production",
            platform="PostgreSQL",
            cluster="prod-postgres-primary",
            region="us-east-1",
            symptoms=("HTTP 503 responses", "connection acquisition timeout", "queued requests"),
            comments=(
                _comment(
                    DATABASE_ENGINEER,
                    "Pool wait time rose before the 503 rate increased; no database CPU saturation was observed.",
                    "2025-11-12T09:05:00Z",
                ),
            ),
            history=(
                _history(
                    "2025-11-12T13:45:00Z",
                    DATABASE_ENGINEER,
                    "status",
                    "Investigating",
                    "Resolved",
                ),
            ),
            resolution=(
                "Raised the PgBouncer pool allocation for the orders API and added a five-second "
                "application connection-acquisition timeout."
            ),
            affected_version="orders-api-4.18.2",
            root_cause="The application pool could queue more requests than its PgBouncer allocation could serve.",
        ),
        JiraTicket(
            id="9002",
            key="PROJ-902",
            summary="EKS payment pods entered CrashLoopBackOff after memory limit change",
            description=(
                "Payment processor pods restarted continuously after a deployment reduced the "
                "container memory limit from 2Gi to 768Mi."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2025-12-03T14:20:00Z",
            updated="2025-12-03T16:05:00Z",
            labels=("eks", "kubernetes", "crashloopbackoff", "memory"),
            components=("Payment Processor", "Kubernetes Deployment"),
            service="payment-processor",
            environment="production",
            platform="Amazon EKS",
            cluster="eks-prod-payments",
            region="us-east-1",
            symptoms=("CrashLoopBackOff", "OOMKilled", "reduced payment processing capacity"),
            comments=(
                _comment(PLATFORM_ENGINEER, "Previous ReplicaSet remained healthy at a 2Gi limit.", "2025-12-03T14:42:00Z"),
            ),
            history=(
                _history("2025-12-03T15:12:00Z", PLATFORM_ENGINEER, "memory limit", "768Mi", "2Gi"),
            ),
            resolution="Restored the 2Gi memory limit and added a deployment policy check for resource reductions.",
            affected_version="payment-processor-7.4.0",
            root_cause="A deployment manifest override applied an insufficient container memory limit.",
        ),
        JiraTicket(
            id="9003",
            key="PROJ-903",
            summary="Kafka order-events consumer lag exceeded alert threshold",
            description=(
                "Consumer lag for the fulfillment group increased after one consumer instance "
                "stopped committing offsets while processing an oversized message."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=MIDDLEWARE_ENGINEER,
            created="2026-01-08T04:15:00Z",
            updated="2026-01-08T07:30:00Z",
            labels=("kafka", "consumer-lag", "production", "orders"),
            components=("Kafka", "Fulfillment Consumer"),
            service="fulfillment-consumer",
            environment="production",
            platform="Apache Kafka",
            cluster="kafka-prod-orders",
            region="us-east-1",
            symptoms=("consumer lag", "delayed fulfillment events", "offset commits stopped"),
            comments=(
                _comment(MIDDLEWARE_ENGINEER, "Lag was isolated to partition 18 of order-events.", "2026-01-08T04:43:00Z"),
            ),
            history=(
                _history("2026-01-08T07:30:00Z", MIDDLEWARE_ENGINEER, "status", "Mitigating", "Resolved"),
            ),
            resolution="Moved the oversized record to the dead-letter topic and restarted the affected consumer instance.",
            affected_version="fulfillment-consumer-3.9.1",
            root_cause="The consumer retry loop blocked offset commits for one partition after deserialization failed.",
        ),
        JiraTicket(
            id="9004",
            key="PROJ-904",
            summary="AKS network policy blocked inventory service egress",
            description=(
                "Inventory pods could not connect to the pricing API after a namespace network "
                "policy update removed the required egress selector."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-01-21T10:00:00Z",
            updated="2026-01-21T12:22:00Z",
            labels=("aks", "network-policy", "connectivity", "production"),
            components=("Inventory Service", "Kubernetes Networking"),
            service="inventory-service",
            environment="production",
            platform="Azure AKS",
            cluster="aks-prod-commerce",
            region="eastus2",
            symptoms=("connection timeout", "pricing API unreachable", "failed inventory requests"),
            comments=(
                _comment(PLATFORM_ENGINEER, "DNS resolution succeeded; TCP connections were denied by policy.", "2026-01-21T10:28:00Z"),
            ),
            history=(
                _history("2026-01-21T11:55:00Z", PLATFORM_ENGINEER, "network policy", "restricted", "restored egress"),
            ),
            resolution="Restored the pricing API namespace selector and added a policy connectivity test to deployment validation.",
            affected_version="inventory-service-5.7.3",
            root_cause="A network policy template omitted the pricing namespace from allowed egress destinations.",
        ),
        JiraTicket(
            id="9005",
            key="PROJ-905",
            summary="IBM DataPower gateway rejected client certificate after renewal",
            description=(
                "Partner payment requests failed TLS authentication after certificate renewal. "
                "The DataPower validation credential still referenced the previous signer chain."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="Critical",
            severity="SEV-1",
            reporter=NOC_ENGINEER,
            assignee=MIDDLEWARE_ENGINEER,
            created="2026-02-02T06:40:00Z",
            updated="2026-02-02T09:18:00Z",
            labels=("datapower", "certificate", "tls", "payments"),
            components=("IBM DataPower", "Partner Payments API"),
            service="partner-payments-gateway",
            environment="production",
            platform="IBM DataPower",
            cluster="datapower-prod-east",
            region="us-east-1",
            symptoms=("TLS handshake failure", "client certificate rejected", "partner API unavailable"),
            comments=(
                _comment(MIDDLEWARE_ENGINEER, "The new leaf certificate was valid but its intermediate CA was absent.", "2026-02-02T07:25:00Z"),
            ),
            history=(
                _history("2026-02-02T08:54:00Z", MIDDLEWARE_ENGINEER, "certificate chain", "old signer", "new signer"),
            ),
            resolution="Imported the new intermediate CA and updated the DataPower validation credential.",
            affected_version="partner-certificate-2026-02",
            root_cause="The certificate change omitted the new intermediate CA from the DataPower trust configuration.",
        ),
        JiraTicket(
            id="9006",
            key="PROJ-906",
            summary="Redis session cluster reached maxmemory and evicted active sessions",
            description=(
                "The production session cache reached its configured memory limit and began "
                "evicting active session keys during peak login traffic."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-02-18T17:05:00Z",
            updated="2026-02-18T19:42:00Z",
            labels=("redis", "memory-pressure", "sessions", "production"),
            components=("Redis", "Session Service"),
            service="session-cache",
            environment="production",
            platform="Redis",
            cluster="redis-prod-sessions",
            region="us-east-1",
            symptoms=("key eviction", "unexpected logout", "maxmemory reached"),
            comments=(
                _comment(PLATFORM_ENGINEER, "A new session attribute increased average value size by 38 percent.", "2026-02-18T17:40:00Z"),
            ),
            history=(
                _history("2026-02-18T19:10:00Z", PLATFORM_ENGINEER, "cache capacity", "6Gi", "10Gi"),
            ),
            resolution="Increased cache capacity and shortened retention for abandoned sessions.",
            affected_version="session-service-6.2.0",
            root_cause="Session payload growth exhausted the configured Redis maxmemory capacity.",
        ),
        JiraTicket(
            id="9007",
            key="PROJ-907",
            summary="Checkout API latency increased after downstream timeout change",
            description=(
                "Checkout p95 latency rose above four seconds after the tax service timeout was "
                "increased, allowing request workers to remain occupied longer."
            ),
            issue_type="Incident",
            status="Investigating",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-08-11T11:30:00Z",
            updated="2026-08-11T13:10:00Z",
            labels=("api", "latency", "checkout", "production"),
            components=("Checkout API", "Tax Service"),
            service="checkout-api",
            environment="production",
            platform="Amazon EKS",
            cluster="eks-prod-commerce",
            region="us-east-1",
            symptoms=("high p95 latency", "worker saturation", "downstream timeout"),
            comments=(
                _comment(PLATFORM_ENGINEER, "Trace samples show most waiting time in tax-service calls.", "2026-08-11T12:05:00Z"),
            ),
            history=(
                _history("2026-08-11T11:45:00Z", NOC_ENGINEER, "status", "Open", "Investigating"),
            ),
            resolution=None,
            affected_version="checkout-api-8.1.0",
            root_cause=None,
        ),
        JiraTicket(
            id="9008",
            key="PROJ-908",
            summary="PostgreSQL connection pool exhaustion during scheduled backup",
            description=(
                "The production PostgreSQL connection pool was exhausted while pg_dump backup "
                "sessions ran against the primary database. Applications reported acquisition timeouts."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="Critical",
            severity="SEV-1",
            reporter=NOC_ENGINEER,
            assignee=DATABASE_ENGINEER,
            created="2026-05-18T01:00:00Z",
            updated="2026-05-18T04:35:00Z",
            labels=("production", "database", "connection-pool", "postgresql", "incident"),
            components=("PostgreSQL", "Backend API", "Backup Service"),
            service="postgres-cluster",
            environment="production",
            platform="PostgreSQL",
            cluster="prod-postgres-primary",
            region="us-east-1",
            symptoms=("connection pool exhaustion", "connection timeout", "max connections reached"),
            comments=(
                _comment(DATABASE_ENGINEER, "Backup connections accounted for 34 of 100 server connections.", "2026-05-18T01:42:00Z"),
            ),
            history=(
                _history("2026-05-18T04:35:00Z", DATABASE_ENGINEER, "status", "Mitigating", "Resolved"),
            ),
            resolution=(
                "Separated backup traffic from the application pool, increased the approved pool "
                "allocation, and limited concurrent backup sessions."
            ),
            affected_version="postgresql-15.5-config-12",
            root_cause="Scheduled backup sessions consumed connections reserved for application traffic.",
        ),
        JiraTicket(
            id="9009",
            key="PROJ-909",
            summary="Kafka brokers rejected producers after TLS truststore rotation",
            description=(
                "Order producers could not authenticate to Kafka after a truststore deployment "
                "excluded the new broker intermediate certificate."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="Critical",
            severity="SEV-1",
            reporter=NOC_ENGINEER,
            assignee=MIDDLEWARE_ENGINEER,
            created="2026-03-09T03:20:00Z",
            updated="2026-03-09T06:15:00Z",
            labels=("kafka", "tls", "certificate", "connectivity"),
            components=("Kafka", "Order Producer"),
            service="order-event-producer",
            environment="production",
            platform="Apache Kafka",
            cluster="kafka-prod-orders",
            region="us-east-1",
            symptoms=("SSL handshake failure", "producer authentication failed", "events not published"),
            comments=(
                _comment(MIDDLEWARE_ENGINEER, "Broker certificates were valid; producer truststore content differed from approved bundle.", "2026-03-09T04:02:00Z"),
            ),
            history=(
                _history("2026-03-09T05:40:00Z", MIDDLEWARE_ENGINEER, "truststore", "incomplete", "approved bundle"),
            ),
            resolution="Deployed the approved CA bundle to producers and restarted affected workloads.",
            affected_version="order-producer-5.3.2",
            root_cause="The producer truststore rotation omitted the broker intermediate certificate.",
        ),
        JiraTicket(
            id="9010",
            key="PROJ-910",
            summary="Redis clients saw connection resets during failover",
            description=(
                "Cart service clients continued using the former Redis primary endpoint after an "
                "automatic failover and received connection reset errors."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-03-22T12:25:00Z",
            updated="2026-03-22T14:08:00Z",
            labels=("redis", "failover", "connectivity", "cart"),
            components=("Redis", "Cart Service"),
            service="cart-cache",
            environment="production",
            platform="Redis",
            cluster="redis-prod-cart",
            region="us-east-1",
            symptoms=("connection reset", "stale primary endpoint", "cart read failures"),
            comments=(
                _comment(PLATFORM_ENGINEER, "Clients had a ten-minute DNS cache despite the one-minute endpoint TTL.", "2026-03-22T13:00:00Z"),
            ),
            history=(
                _history("2026-03-22T14:08:00Z", PLATFORM_ENGINEER, "status", "Mitigating", "Resolved"),
            ),
            resolution="Reduced client DNS caching and enabled topology refresh after connection errors.",
            affected_version="cart-service-4.11.0",
            root_cause="Client-side DNS caching delayed discovery of the new Redis primary.",
        ),
        JiraTicket(
            id="10001",
            key="PROJ-1001",
            summary="EKS deployment failed readiness checks after configuration release",
            description=(
                "New account-service pods did not become ready because the configured dependency "
                "health path returned 404 after an application route change."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-04-06T15:10:00Z",
            updated="2026-04-06T17:40:00Z",
            labels=("eks", "deployment", "readiness", "configuration"),
            components=("Account Service", "Kubernetes Deployment"),
            service="account-service",
            environment="production",
            platform="Amazon EKS",
            cluster="eks-prod-identity",
            region="us-east-1",
            symptoms=("readiness probe failed", "HTTP 404", "deployment unavailable"),
            comments=(
                _comment(PLATFORM_ENGINEER, "The application exposes /health/ready in this release.", "2026-04-06T15:38:00Z"),
            ),
            history=(
                _history("2026-04-06T16:50:00Z", PLATFORM_ENGINEER, "readiness path", "/ready", "/health/ready"),
            ),
            resolution="Updated the readiness probe path and added route validation to the release pipeline.",
            affected_version="account-service-9.0.0",
            root_cause="Deployment configuration retained a readiness path removed by the application release.",
        ),
        JiraTicket(
            id="10002",
            key="PROJ-1002",
            summary="Database connection pool exhaustion under peak load",
            description=(
                "Production is experiencing PostgreSQL connection pool exhaustion during peak "
                "traffic above 5000 requests per minute. PostgreSQL max_connections is set to 100 "
                "and the limit is being reached, affecting approximately 15 percent of users."
            ),
            issue_type="Incident",
            status="Investigating",
            priority="Critical",
            severity="SEV-1",
            reporter=NOC_ENGINEER,
            assignee=DATABASE_ENGINEER,
            created="2026-08-12T06:00:00Z",
            updated="2026-08-12T11:30:00Z",
            labels=("production", "database", "connection-pool", "postgresql", "incident"),
            components=("PostgreSQL", "Backend API"),
            service="postgres-cluster",
            environment="production",
            platform="PostgreSQL",
            cluster="prod-postgres-primary",
            region="us-east-1",
            symptoms=("connection pool exhaustion", "connection timeout", "max connections reached"),
            comments=(
                _comment(NOC_ENGINEER, "Escalated to SEV-1 after user impact reached approximately 15 percent.", "2026-08-12T06:25:00Z"),
                _comment(DATABASE_ENGINEER, "Current server limit is 100; application pool configuration is not yet attached.", "2026-08-12T07:10:00Z"),
            ),
            history=(
                _history("2026-08-12T06:25:00Z", NOC_ENGINEER, "severity", "SEV-2", "SEV-1"),
                _history("2026-08-12T06:25:00Z", NOC_ENGINEER, "status", "Open", "Investigating"),
            ),
            resolution=None,
            affected_version="postgresql-15.5-config-18",
            root_cause=None,
        ),
        JiraTicket(
            id="10003",
            key="PROJ-1003",
            summary="AKS workloads failed DNS lookup for internal identity endpoint",
            description=(
                "Authentication pods intermittently failed to resolve the internal identity endpoint "
                "after CoreDNS pods were concentrated on one overloaded node pool."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-04-28T09:12:00Z",
            updated="2026-04-28T12:30:00Z",
            labels=("aks", "dns", "authentication", "coredns"),
            components=("Identity Service", "CoreDNS"),
            service="identity-service",
            environment="production",
            platform="Azure AKS",
            cluster="aks-prod-identity",
            region="eastus2",
            symptoms=("DNS lookup timeout", "authentication failure", "CoreDNS throttling"),
            comments=(
                _comment(PLATFORM_ENGINEER, "CoreDNS throttling correlated with the failed lookup window.", "2026-04-28T10:02:00Z"),
            ),
            history=(
                _history("2026-04-28T11:40:00Z", PLATFORM_ENGINEER, "CoreDNS replicas", "2", "4"),
            ),
            resolution="Spread CoreDNS across node pools, increased replicas, and added DNS saturation alerts.",
            affected_version="aks-platform-config-31",
            root_cause="CoreDNS replicas were colocated on an overloaded node pool and were CPU throttled.",
        ),
        JiraTicket(
            id="10004",
            key="PROJ-1004",
            summary="DataPower backend authentication header removed by policy update",
            description=(
                "A DataPower multi-protocol gateway policy update removed the Authorization header "
                "before forwarding requests to the customer-profile API."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="High",
            severity="SEV-2",
            reporter=NOC_ENGINEER,
            assignee=MIDDLEWARE_ENGINEER,
            created="2026-06-03T18:20:00Z",
            updated="2026-06-03T20:55:00Z",
            labels=("datapower", "authentication", "policy", "api"),
            components=("IBM DataPower", "Customer Profile API"),
            service="customer-profile-gateway",
            environment="production",
            platform="IBM DataPower",
            cluster="datapower-prod-east",
            region="us-east-1",
            symptoms=("HTTP 401 responses", "authorization header missing", "backend authentication failed"),
            comments=(
                _comment(MIDDLEWARE_ENGINEER, "Gateway ingress contained the header; backend capture did not.", "2026-06-03T18:58:00Z"),
            ),
            history=(
                _history("2026-06-03T20:10:00Z", MIDDLEWARE_ENGINEER, "gateway policy", "v42", "v43-fixed"),
            ),
            resolution="Restored the header propagation rule and added a policy regression assertion.",
            affected_version="datapower-policy-v43",
            root_cause="A policy refactor omitted the Authorization header from the backend request allowlist.",
        ),
        JiraTicket(
            id="10005",
            key="PROJ-1005",
            summary="Kubernetes configuration drift changed notification service endpoint",
            description=(
                "The production notification deployment referenced a staging message endpoint after "
                "a manual ConfigMap edit diverged from the Git-managed configuration."
            ),
            issue_type="Incident",
            status="Resolved",
            priority="Medium",
            severity="SEV-3",
            reporter=NOC_ENGINEER,
            assignee=PLATFORM_ENGINEER,
            created="2026-06-19T08:35:00Z",
            updated="2026-06-19T10:25:00Z",
            labels=("kubernetes", "configuration-drift", "deployment", "notification"),
            components=("Notification Service", "ConfigMap"),
            service="notification-service",
            environment="production",
            platform="Amazon EKS",
            cluster="eks-prod-shared",
            region="us-east-1",
            symptoms=("notifications not delivered", "incorrect endpoint", "configuration drift"),
            comments=(
                _comment(PLATFORM_ENGINEER, "The live ConfigMap hash did not match the GitOps revision.", "2026-06-19T09:02:00Z"),
            ),
            history=(
                _history("2026-06-19T09:50:00Z", PLATFORM_ENGINEER, "ConfigMap", "manual value", "Git-managed value"),
            ),
            resolution="Reconciled the ConfigMap from Git and removed manual write access from the deployment role.",
            affected_version="notification-config-2026.06.18",
            root_cause="A manual production ConfigMap edit bypassed the GitOps reconciliation workflow.",
        ),
    )


def _normalized(value: str | None) -> str:
    return (value or "").strip().casefold()


def _tokens(value: str | None) -> set[str]:
    tokens: set[str] = set()
    for token in _TOKEN_PATTERN.findall(_normalized(value)):
        if token in _STOP_WORDS or len(token) <= 1:
            continue
        tokens.add(token[:-1] if token.endswith("s") and len(token) > 4 else token)
    return tokens


def _ticket_search_text(ticket: JiraTicket) -> str:
    values = [
        ticket.key,
        ticket.summary,
        ticket.description,
        ticket.issue_type,
        ticket.status,
        ticket.priority,
        ticket.severity,
        ticket.service,
        ticket.environment,
        ticket.platform,
        ticket.cluster or "",
        ticket.region or "",
        ticket.resolution or "",
        ticket.root_cause or "",
        *ticket.labels,
        *ticket.components,
        *ticket.symptoms,
        *(comment.body for comment in ticket.comments),
    ]
    return " ".join(values).casefold()


class MockJiraRepository:
    """In-memory Jira implementation with deterministic operational data."""

    def __init__(self, tickets: tuple[JiraTicket, ...] | None = None) -> None:
        ticket_values = tickets if tickets is not None else _build_operational_tickets()
        self._tickets = {ticket.key: ticket for ticket in ticket_values}

    @property
    def provider_name(self) -> str:
        return "mock"

    async def get_ticket(self, ticket_key: str) -> JiraTicket:
        normalized = normalize_ticket_key(ticket_key)
        ticket = self._tickets.get(normalized)
        if ticket is None:
            raise JiraTicketNotFoundError(f"Jira ticket {normalized} was not found.")
        return ticket.model_copy(deep=True)

    async def search_tickets(self, criteria: JiraSearchCriteria) -> list[JiraTicket]:
        text_tokens = _tokens(criteria.text)
        requested_labels = {_normalized(value) for value in criteria.labels}
        requested_components = {_normalized(value) for value in criteria.components}

        matches: list[JiraTicket] = []
        for ticket in self._tickets.values():
            searchable = _ticket_search_text(ticket)
            if text_tokens and not all(token in searchable for token in text_tokens):
                continue
            if criteria.status and _normalized(ticket.status) != _normalized(criteria.status):
                continue
            if criteria.priority and _normalized(ticket.priority) != _normalized(criteria.priority):
                continue
            if criteria.issue_type and _normalized(ticket.issue_type) != _normalized(criteria.issue_type):
                continue
            if criteria.service and _normalized(ticket.service) != _normalized(criteria.service):
                continue
            if criteria.environment and _normalized(ticket.environment) != _normalized(criteria.environment):
                continue
            if criteria.platform and _normalized(ticket.platform) != _normalized(criteria.platform):
                continue
            if criteria.cluster and _normalized(ticket.cluster) != _normalized(criteria.cluster):
                continue

            ticket_labels = {_normalized(value) for value in ticket.labels}
            if requested_labels and not requested_labels.issubset(ticket_labels):
                continue

            ticket_components = {_normalized(value) for value in ticket.components}
            if requested_components and not requested_components.issubset(ticket_components):
                continue

            matches.append(ticket)

        matches.sort(key=lambda ticket: (ticket.updated, ticket.key), reverse=True)
        return [ticket.model_copy(deep=True) for ticket in matches[: criteria.limit]]

    async def find_similar_tickets(
        self, ticket_key: str, *, limit: int = 3
    ) -> list[SimilarTicketMatch]:
        normalized = normalize_ticket_key(ticket_key)
        target = self._tickets.get(normalized)
        if target is None:
            raise JiraTicketNotFoundError(f"Jira ticket {normalized} was not found.")
        if not 1 <= limit <= 10:
            raise ValueError("Similarity result limit must be between 1 and 10.")

        ranked: list[SimilarTicketMatch] = []
        for candidate in self._tickets.values():
            if candidate.key == target.key:
                continue

            historical_resolved = candidate.status.casefold() in {"resolved", "done", "closed"}
            if not historical_resolved:
                continue

            score, reasons = self._score_similarity(target, candidate)
            if score <= 0:
                continue

            if score >= 65:
                applicability = (
                    "High: the historical incident shares the core operational context. "
                    "Validate current evidence before applying its resolution."
                )
            elif score >= 40:
                applicability = (
                    "Moderate: several operational attributes match, but the prior resolution "
                    "requires environment-specific validation."
                )
            else:
                applicability = (
                    "Low: use this incident only as supporting context; important attributes differ."
                )

            ranked.append(
                SimilarTicketMatch(
                    ticket=candidate.model_copy(deep=True),
                    similarity_score=min(score, 100),
                    match_reasons=tuple(reasons),
                    historical_resolved=historical_resolved,
                    previous_resolution=candidate.resolution,
                    applicability=applicability,
                )
            )

        ranked.sort(key=lambda match: (-match.similarity_score, match.ticket.key))
        return ranked[:limit]

    @staticmethod
    def _score_similarity(target: JiraTicket, candidate: JiraTicket) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        if _normalized(target.service) == _normalized(candidate.service):
            score += 25
            reasons.append(f"Same service: {target.service}")
        if _normalized(target.platform) == _normalized(candidate.platform):
            score += 15
            reasons.append(f"Same platform: {target.platform}")
        if _normalized(target.environment) == _normalized(candidate.environment):
            score += 8
            reasons.append(f"Same environment: {target.environment}")
        if target.cluster and _normalized(target.cluster) == _normalized(candidate.cluster):
            score += 8
            reasons.append(f"Same cluster: {target.cluster}")
        if _normalized(target.issue_type) == _normalized(candidate.issue_type):
            score += 4
            reasons.append(f"Same issue type: {target.issue_type}")

        common_components = sorted(
            {_normalized(value) for value in target.components}
            & {_normalized(value) for value in candidate.components}
        )
        if common_components:
            score += min(len(common_components) * 6, 12)
            reasons.append(f"Shared components: {', '.join(common_components)}")

        common_labels = sorted(
            {_normalized(value) for value in target.labels}
            & {_normalized(value) for value in candidate.labels}
        )
        if common_labels:
            score += min(len(common_labels) * 3, 12)
            reasons.append(f"Shared labels: {', '.join(common_labels)}")

        common_symptoms = sorted(
            {_normalized(value) for value in target.symptoms}
            & {_normalized(value) for value in candidate.symptoms}
        )
        if common_symptoms:
            score += min(len(common_symptoms) * 6, 18)
            reasons.append(f"Shared symptoms: {', '.join(common_symptoms)}")

        summary_overlap = _tokens(target.summary) & _tokens(candidate.summary)
        if summary_overlap:
            score += min(len(summary_overlap) * 2, 8)
            reasons.append(f"Summary terms: {', '.join(sorted(summary_overlap))}")

        description_overlap = _tokens(target.description) & _tokens(candidate.description)
        if description_overlap:
            score += min(len(description_overlap), 5)

        return score, reasons


def build_mock_repository() -> MockJiraRepository:
    """Public factory used by tests and dependency construction."""

    return MockJiraRepository()
