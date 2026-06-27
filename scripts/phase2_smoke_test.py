from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_KEY = "dev-platform-key"
ALERTS_URL = "http://localhost:8002"
ONCALL_URL = "http://localhost:8003"
STATUS_PAGE_URL = "http://localhost:8004"


def request_json(method: str, url: str, payload: dict | None = None, *, idempotency_key: str | None = None) -> dict | list:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY, "X-Actor": "phase2-smoke-test"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc


def wait_for_health(url: str) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            request_json("GET", f"{url}/health")
            return
        except (HTTPError, URLError, TimeoutError):
            time.sleep(2)
    raise RuntimeError(f"{url} did not become healthy within 90 seconds")


def wait_for_notification(incident_id: str) -> dict:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        notifications = request_json("GET", f"{ONCALL_URL}/notifications?incident_id={incident_id}")
        if notifications:
            return notifications[0]
        time.sleep(2)
    raise RuntimeError(f"no notification created for incident {incident_id}")


def wait_for_component_status(component_name: str, expected_status: str) -> dict:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status_payload = request_json("GET", f"{STATUS_PAGE_URL}/status")
        for component in status_payload["components"]:
            if component["component_name"] == component_name and component["status"] == expected_status:
                return component
        time.sleep(2)
    raise RuntimeError(f"{component_name} did not reach status {expected_status}")


def main() -> int:
    wait_for_health(ALERTS_URL)
    wait_for_health(ONCALL_URL)
    wait_for_health(STATUS_PAGE_URL)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    service_name = f"checkout-{run_id}"

    request_json(
        "POST",
        f"{ONCALL_URL}/schedules",
        {
            "name": f"Backend On-Call {run_id}",
            "timezone": "UTC",
            "rotation_type": "daily",
            "members": [
                {
                    "user_id": "eng-1",
                    "name": "Demo Engineer",
                    "email": "demo.engineer@example.com",
                    "slack_id": "UDEMO1",
                }
            ],
        },
    )

    alert_payload = {
        "receiver": "platform",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighErrorRate",
                    "severity": "critical",
                    "source": "prometheus",
                    "service": service_name,
                },
                "annotations": {
                    "summary": "Checkout error rate is above threshold",
                    "description": "Synthetic Phase 2 smoke test alert",
                },
                "startsAt": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    result = request_json("POST", f"{ALERTS_URL}/alerts/webhook", alert_payload, idempotency_key=f"phase2-{run_id}")
    incident_id = result["alerts"][0]["incident_id"]
    if result["promoted"] != 1 or not incident_id:
        raise AssertionError(f"expected alert to promote to one incident, got {result}")

    notification = wait_for_notification(incident_id)
    if notification["channel"] != "slack" or notification["status"] != "sent":
        raise AssertionError(f"expected Slack notification record, got {notification}")

    component = wait_for_component_status(service_name, "major_outage")
    if component["incident_id"] != incident_id:
        raise AssertionError(f"expected status component to reference incident {incident_id}, got {component}")

    ack = request_json("POST", f"{ONCALL_URL}/notifications/{notification['id']}/acknowledge")
    if ack["notification"]["status"] != "acknowledged":
        raise AssertionError(f"expected notification acknowledgement, got {ack}")

    print(f"Phase 2 smoke test passed for incident {incident_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Phase 2 smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
