"""Add automatic ticket analysis state.

Revision ID: 20261006_0004
Revises: 20260930_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261006_0004"
down_revision: str | None = "20260930_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.add_column(sa.Column("workflow_thread_id", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "analysis_status",
                sa.String(30),
                nullable=False,
                server_default="not_started",
            )
        )
        batch_op.add_column(sa.Column("analysis_error", sa.String(100), nullable=True))
        batch_op.create_index("ix_tickets_workflow_thread_id", ["workflow_thread_id"], unique=True)
        batch_op.create_index("ix_tickets_analysis_status", ["analysis_status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.drop_index("ix_tickets_analysis_status")
        batch_op.drop_index("ix_tickets_workflow_thread_id")
        batch_op.drop_column("analysis_error")
        batch_op.drop_column("analysis_status")
        batch_op.drop_column("workflow_thread_id")
