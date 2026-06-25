from app.services import compute_fingerprint


def test_fingerprint_is_stable_for_sorted_labels():
    labels_a = {"severity": "critical", "service": "checkout", "alertname": "HighErrorRate"}
    labels_b = {"alertname": "HighErrorRate", "service": "checkout", "severity": "critical"}

    assert compute_fingerprint("HighErrorRate", labels_a) == compute_fingerprint("HighErrorRate", labels_b)


def test_fingerprint_changes_when_service_changes():
    base = {"severity": "critical", "service": "checkout", "alertname": "HighErrorRate"}
    changed = {"severity": "critical", "service": "billing", "alertname": "HighErrorRate"}

    assert compute_fingerprint("HighErrorRate", base) != compute_fingerprint("HighErrorRate", changed)

