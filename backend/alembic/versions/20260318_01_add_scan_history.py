"""add scan_history table

Revision ID: add_scan_history
Revises: 
Create Date: 2026-03-18 12:00:00

"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = "add_scan_history"
down_revision = None  # or your previous revision ID if needed
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scan_history",
        sa.Column("id", sa.String(), primary_key=True, index=True),
        sa.Column("cidr", sa.String(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("speed_concurrency", sa.Integer(), nullable=False),
        sa.Column("speed_delay", sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table("scan_history")