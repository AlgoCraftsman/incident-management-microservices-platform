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
        "DO $$ BEGIN CREATE TYPE rotation_type AS ENUM ('daily', 'weekly'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE notification_channel AS ENUM ('slack', 'email', 'sms', 'webhook'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed', 'acknowledged'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    rotation_type = postgresql.ENUM("daily", "weekly", name="rotation_type", create_type=False)
    channel = postgresql.ENUM("slack", "email", "sms", "webhook", name="notification_channel", create_type=False)
    notification_status = postgresql.ENUM(
        "pending",
        "sent",
        "failed",
        "acknowledged",
        name="notification_status",
        create_type=False,
    )

    op.create_table(
        "schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("rotation_type", rotation_type, nullable=False),
        sa.Column("members", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "schedule_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("schedule_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_overrides_schedule_id", "schedule_overrides", ["schedule_id"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("schedule_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("channel", channel, nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_incident_id", "notifications", ["incident_id"], unique=False)
    op.create_index("ix_notifications_schedule_id", "notifications", ["schedule_id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_schedule_id", table_name="notifications")
    op.drop_index("ix_notifications_incident_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_schedule_overrides_schedule_id", table_name="schedule_overrides")
    op.drop_table("schedule_overrides")
    op.drop_table("schedules")
    postgresql.ENUM(name="notification_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_channel").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="rotation_type").drop(op.get_bind(), checkfirst=True)
