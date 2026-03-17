"""Create vpn_alert_rules table"""

from alembic import op
import sqlalchemy as sa

revision = "xxxx_vpn_alert_rules"
down_revision = "xxxx_vpn_history"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vpn_alert_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(200), unique=True, index=True),
        sa.Column("enabled", sa.Boolean, default=True),
    )


def downgrade():
    op.drop_table("vpn_alert_rules")