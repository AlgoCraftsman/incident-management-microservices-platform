from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_processed_events"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("status_updates", sa.Column("source_event_id", sa.String(length=36), nullable=True))
    op.create_index("ix_status_updates_source_event_id", "status_updates", ["source_event_id"], unique=False)
    op.create_unique_constraint(
        "uq_status_updates_source_event_id",
        "status_updates",
        ["source_event_id"],
    )
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("stream_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_processed_events_event_type", "processed_events", ["event_type"], unique=False)
    op.create_index("ix_processed_events_stream_id", "processed_events", ["stream_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_processed_events_stream_id", table_name="processed_events")
    op.drop_index("ix_processed_events_event_type", table_name="processed_events")
    op.drop_table("processed_events")
    op.drop_constraint("uq_status_updates_source_event_id", "status_updates", type_="unique")
    op.drop_index("ix_status_updates_source_event_id", table_name="status_updates")
    op.drop_column("status_updates", "source_event_id")
