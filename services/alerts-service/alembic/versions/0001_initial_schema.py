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
        "DO $$ BEGIN CREATE TYPE alert_status AS ENUM ('firing', 'resolved', 'suppressed'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    alert_status = postgresql.ENUM("firing", "resolved", "suppressed", name="alert_status", create_type=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("alert_name", sa.String(length=255), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("annotations", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", alert_status, nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("suppression_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suppression_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_fingerprint", "alerts", ["fingerprint"], unique=True)
    op.create_index("ix_alerts_incident_id", "alerts", ["incident_id"], unique=False)
    op.create_index("ix_alerts_severity", "alerts", ["severity"], unique=False)
    op.create_index("ix_alerts_source", "alerts", ["source"], unique=False)
    op.create_index("ix_alerts_status_severity", "alerts", ["status", "severity"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alerts_status_severity", table_name="alerts")
    op.drop_index("ix_alerts_source", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_incident_id", table_name="alerts")
    op.drop_index("ix_alerts_fingerprint", table_name="alerts")
    op.drop_table("alerts")
    postgresql.ENUM(name="alert_status").drop(op.get_bind(), checkfirst=True)
