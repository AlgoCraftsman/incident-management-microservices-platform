from __future__ import annotations

from app.delivery import deliver_notification, format_incident_message
from app.models import NotificationChannel
from app.settings import Settings


def test_mock_slack_delivery_is_successful_without_webhook():
    result = deliver_notification(
        channel=NotificationChannel.slack,
        member={"user_id": "u1", "slack_id": "U123"},
        message_payload={
            "incident_id": "incident-1",
            "title": "Checkout failure",
            "severity": "P1",
            "service_name": "checkout",
        },
        settings=Settings(slack_webhook_url=None),
    )

    assert result.success is True
    assert result.provider == "mock-slack"


def test_email_delivery_fails_when_target_has_no_email():
    result = deliver_notification(
        channel=NotificationChannel.email,
        member={"user_id": "u1"},
        message_payload={
            "incident_id": "incident-1",
            "title": "Checkout failure",
            "severity": "P1",
            "service_name": "checkout",
        },
        settings=Settings(),
    )

    assert result.success is False
    assert "no email" in result.detail


def test_incident_message_includes_traceable_incident_details():
    message = format_incident_message(
        {
            "incident_id": "incident-1",
            "title": "Checkout failure",
            "severity": "P1",
            "service_name": "checkout",
        }
    )

    assert "P1" in message
    assert "checkout" in message
    assert "incident-1" in message
