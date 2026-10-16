"""Explicit initial schema; future model changes do not alter migration history."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
    )
    op.create_index("ix_visits_owner", "visits", ["owner"])
    op.create_table(
        "operations",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("visits.id"), primary_key=True),
        sa.Column("request_id", sa.String(36), primary_key=True),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("lease", sa.String(36), nullable=False),
        sa.Column("started", sa.Integer(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("operations")
    op.drop_index("ix_visits_owner", "visits")
    op.drop_table("visits")
