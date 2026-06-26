from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_KEY = "dev-platform-key"
ALERTS_URL = "http://localhost:8002"
INCIDENTS_URL = "http://localhost:8001"


def request_json(method: str, url: str, payload: dict | None = None, *, idempotency_key: str | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "X-Actor": "phase1-smoke-test",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(url: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            request_json("GET", f"{url}/health")
            return
        except (HTTPError, URLError, TimeoutError):
            time.sleep(2)
    raise RuntimeError(f"{url} did not become healthy within 60 seconds")


def main() -> int:
    wait_for_health(INCIDENTS_URL)
    wait_for_health(ALERTS_URL)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    payload = {
        "receiver": "platform",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighErrorRate",
                    "severity": "critical",
                    "source": "prometheus",
                    "service": f"checkout-{run_id}",
                },
                "annotations": {
                    "summary": "Checkout error rate is above threshold",
                    "description": "Synthetic Phase 1 smoke test alert",
                },
                "startsAt": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    first = request_json("POST", f"{ALERTS_URL}/alerts/webhook", payload, idempotency_key=f"smoke-{run_id}")
    alert = first["alerts"][0]
    incident_id = alert["incident_id"]

    if first["accepted"] != 1 or first["promoted"] != 1 or not incident_id:
        raise AssertionError(f"expected first alert to promote to one incident, got {first}")

    second = request_json("POST", f"{ALERTS_URL}/alerts/webhook", payload, idempotency_key=f"smoke-{run_id}")
    if second["deduplicated"] != 1 or second["promoted"] != 0 or second["alerts"][0]["incident_id"] != incident_id:
        raise AssertionError(f"expected duplicate alert to reuse incident, got {second}")

    incident = request_json("GET", f"{INCIDENTS_URL}/incidents/{incident_id}")
    if incident["severity"] != "P1" or incident["status"] != "open":
        raise AssertionError(f"unexpected incident shape: {incident}")

    resolved = request_json("POST", f"{INCIDENTS_URL}/incidents/{incident_id}/resolve")
    if resolved["status"] != "resolved":
        raise AssertionError(f"expected resolved incident, got {resolved}")

    timeline = request_json("GET", f"{INCIDENTS_URL}/incidents/{incident_id}/timeline")
    event_types = {event["event_type"] for event in timeline}
    if not {"incident.created", "incident.resolved"}.issubset(event_types):
        raise AssertionError(f"expected lifecycle timeline events, got {timeline}")

    print(f"Phase 1 smoke test passed for incident {incident_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Phase 1 smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
