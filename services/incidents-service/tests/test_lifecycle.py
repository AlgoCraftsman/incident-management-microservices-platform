import pytest
from fastapi import HTTPException

from app.models import Incident, IncidentStatus, Severity
from app.services import transition_status


def test_incident_cannot_close_before_resolved():
    incident = Incident(title="Checkout failure", severity=Severity.p1, status=IncidentStatus.open)

    with pytest.raises(HTTPException) as exc:
        transition_status(incident, IncidentStatus.closed)

    assert exc.value.status_code == 409


def test_resolving_sets_resolved_timestamp():
    incident = Incident(title="Checkout failure", severity=Severity.p1, status=IncidentStatus.acknowledged)

    transition_status(incident, IncidentStatus.resolved)

    assert incident.status == IncidentStatus.resolved
    assert incident.resolved_at is not None

