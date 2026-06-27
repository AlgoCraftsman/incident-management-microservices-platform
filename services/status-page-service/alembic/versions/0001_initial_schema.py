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
        "DO $$ BEGIN CREATE TYPE component_status AS ENUM "
        "('operational', 'degraded', 'partial_outage', 'major_outage'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    component_status = postgresql.ENUM(
        "operational",
        "degraded",
        "partial_outage",
        "major_outage",
        name="component_status",
        create_type=False,
    )

    op.create_table(
        "components",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("component_name", sa.String(length=100), nullable=False),
        sa.Column("status", component_status, nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("component_name"),
    )
    op.create_index("ix_components_component_name", "components", ["component_name"], unique=True)
    op.create_index("ix_components_incident_id", "components", ["incident_id"], unique=False)

    op.create_table(
        "status_updates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("component_name", sa.String(length=100), nullable=False),
        sa.Column("status", component_status, nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("posted_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_status_updates_component_name", "status_updates", ["component_name"], unique=False)
    op.create_index("ix_status_updates_incident_id", "status_updates", ["incident_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_status_updates_incident_id", table_name="status_updates")
    op.drop_index("ix_status_updates_component_name", table_name="status_updates")
    op.drop_table("status_updates")
    op.drop_index("ix_components_incident_id", table_name="components")
    op.drop_index("ix_components_component_name", table_name="components")
    op.drop_table("components")
    postgresql.ENUM(name="component_status").drop(op.get_bind(), checkfirst=True)
