from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

import httpx

from app.models import NotificationChannel
from app.settings import Settings


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    provider: str
    detail: str


def deliver_notification(
    *,
    channel: NotificationChannel,
    member: dict[str, Any],
    message_payload: dict[str, Any],
    settings: Settings,
) -> DeliveryResult:
    if channel == NotificationChannel.slack:
        return deliver_slack(member, message_payload, settings)
    if channel == NotificationChannel.email:
        return deliver_email(member, message_payload, settings)
    if channel == NotificationChannel.sms:
        return deliver_webhook("sms", settings.sms_webhook_url, member, message_payload)
    return deliver_webhook("webhook", settings.notification_webhook_url, member, message_payload)


def deliver_slack(member: dict[str, Any], message_payload: dict[str, Any], settings: Settings) -> DeliveryResult:
    if not settings.slack_webhook_url:
        return DeliveryResult(success=True, provider="mock-slack", detail="mock Slack delivery recorded")
    body = {
        "text": format_incident_message(message_payload),
        "incident_id": message_payload["incident_id"],
        "target": member.get("slack_id") or member.get("user_id"),
    }
    return post_json("slack", settings.slack_webhook_url, body)


def deliver_email(member: dict[str, Any], message_payload: dict[str, Any], settings: Settings) -> DeliveryResult:
    email = member.get("email")
    if not email:
        return DeliveryResult(success=False, provider="email", detail="target engineer has no email address")
    if not settings.smtp_host:
        return DeliveryResult(success=True, provider="mock-email", detail="mock email delivery recorded")

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message["Subject"] = f"Incident page: {message_payload.get('title') or message_payload['incident_id']}"
    message.set_content(format_incident_message(message_payload))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except OSError as exc:
        return DeliveryResult(success=False, provider="email", detail=str(exc))
    return DeliveryResult(success=True, provider="email", detail=f"sent email to {email}")


def deliver_webhook(
    provider: str,
    url: str | None,
    member: dict[str, Any],
    message_payload: dict[str, Any],
) -> DeliveryResult:
    if not url:
        return DeliveryResult(success=True, provider=f"mock-{provider}", detail=f"mock {provider} delivery recorded")
    body = {"target": member, "message": message_payload}
    return post_json(provider, url, body)


def post_json(provider: str, url: str, body: dict[str, Any]) -> DeliveryResult:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=body)
        if 200 <= response.status_code < 300:
            return DeliveryResult(success=True, provider=provider, detail=f"HTTP {response.status_code}")
        return DeliveryResult(success=False, provider=provider, detail=f"HTTP {response.status_code}: {response.text}")
    except httpx.HTTPError as exc:
        return DeliveryResult(success=False, provider=provider, detail=str(exc))


def format_incident_message(message_payload: dict[str, Any]) -> str:
    title = message_payload.get("title") or "Incident page"
    severity = message_payload.get("severity") or "unknown severity"
    service_name = message_payload.get("service_name") or "unknown service"
    incident_id = message_payload["incident_id"]
    return f"{severity} incident for {service_name}: {title} ({incident_id})"
