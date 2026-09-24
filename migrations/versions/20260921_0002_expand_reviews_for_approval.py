"""Expand reviews for generated-response approval workflows.

Revision ID: 20260921_0002
Revises: 20260910_0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260921_0002"
down_revision: str | None = "20260910_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column("decision", new_column_name="status")
        batch_op.alter_column("feedback", new_column_name="reviewer_comments")
        batch_op.add_column(sa.Column("workflow_thread_id", sa.String(100)))
        batch_op.add_column(sa.Column("generated_subject", sa.String(200)))
        batch_op.add_column(sa.Column("generated_response", sa.Text()))
        batch_op.add_column(sa.Column("edited_subject", sa.String(200)))
        batch_op.add_column(sa.Column("edited_response", sa.Text()))
        batch_op.add_column(sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_index(op.f("ix_reviews_status"), "reviews", ["status"])
    op.create_index(
        op.f("ix_reviews_workflow_thread_id"),
        "reviews",
        ["workflow_thread_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reviews_workflow_thread_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_status"), table_name="reviews")
    with op.batch_alter_table("reviews") as batch_op:
        for column in ("reviewed_at", "updated_at", "version", "edited_response", "edited_subject", "generated_response", "generated_subject", "workflow_thread_id"):
            batch_op.drop_column(column)
        batch_op.alter_column("reviewer_comments", new_column_name="feedback")
        batch_op.alter_column("status", new_column_name="decision")
