from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE incident_severity AS ENUM ('p1', 'p2', 'p3', 'p4'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE incident_status AS ENUM ('open', 'acknowledged', 'resolved', 'closed'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    severity = postgresql.ENUM("p1", "p2", "p3", "p4", name="incident_severity", create_type=False)
    incident_status = postgresql.ENUM(
        "open",
        "acknowledged",
        "resolved",
        "closed",
        name="incident_status",
        create_type=False,
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", severity, nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=True),
        sa.Column("assignee_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_service_name", "incidents", ["service_name"], unique=False)
    op.create_index("ix_incidents_open_duplicate_lookup", "incidents", ["service_name", "status"], unique=False)

    op.create_table(
        "incident_timeline_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("actor", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_timeline_events_incident_id", "incident_timeline_events", ["incident_id"], unique=False)

    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_idempotency_records_resource_id", "idempotency_records", ["resource_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_resource_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_incident_timeline_events_incident_id", table_name="incident_timeline_events")
    op.drop_table("incident_timeline_events")
    op.drop_index("ix_incidents_open_duplicate_lookup", table_name="incidents")
    op.drop_index("ix_incidents_service_name", table_name="incidents")
    op.drop_table("incidents")
    postgresql.ENUM(name="incident_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="incident_severity").drop(op.get_bind(), checkfirst=True)
