"""Safety tests for structured-log redaction."""

from src.core.logging import redact_sensitive_values


def test_redacts_nested_credentials_without_changing_safe_fields():
    event = {
        "event": "provider.request",
        "provider": "gemini",
        "GOOGLE_API_KEY": "sensitive-value",
        "headers": {"Authorization": "Bearer sensitive-value", "Content-Type": "json"},
        "items": [{"access_token": "sensitive-value", "status": "ok"}],
        "message": "Provider rejected Bearer sensitive-value",
    }

    redacted = redact_sensitive_values(None, "info", event)

    assert redacted == {
        "event": "provider.request",
        "provider": "gemini",
        "GOOGLE_API_KEY": "[REDACTED]",
        "headers": {"Authorization": "[REDACTED]", "Content-Type": "json"},
        "items": [{"access_token": "[REDACTED]", "status": "ok"}],
        "message": "[REDACTED]",
    }
