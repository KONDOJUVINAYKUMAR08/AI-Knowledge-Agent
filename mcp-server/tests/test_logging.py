"""Safety tests for MCP structured-log redaction."""

from src.core.logging import redact_sensitive_values


def test_redacts_sensitive_keys_recursively():
    event = {
        "event": "jira.request",
        "credentials": {"token": "sensitive-value"},
        "tool": "get_ticket",
    }

    assert redact_sensitive_values(None, "info", event) == {
        "event": "jira.request",
        "credentials": "[REDACTED]",
        "tool": "get_ticket",
    }
