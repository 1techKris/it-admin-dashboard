"""Create vpn_history table"""

from alembic import op
import sqlalchemy as sa

revision = "xxxx_vpn_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vpn_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(200), index=True),
        sa.Column("ipv4", sa.String(100)),
        sa.Column("connected_from", sa.String(200)),
        sa.Column("geo_country", sa.String(100)),
        sa.Column("geo_city", sa.String(100)),
        sa.Column("geo_isp", sa.String(200)),
        sa.Column("geo_org", sa.String(200)),
        sa.Column("start_time", sa.DateTime),
        sa.Column("end_time", sa.DateTime),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("timestamp_logged", sa.DateTime),
        sa.Column("raw_json", sa.Text),
    )


def downgrade():
    op.drop_table("vpn_history")