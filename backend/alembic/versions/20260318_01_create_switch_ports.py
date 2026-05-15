from alembic import op
import sqlalchemy as sa

revision = "create_switch_ports"
down_revision = "create_switches"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "switch_ports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("switch_id", sa.String(), sa.ForeignKey("switches.id")),
        sa.Column("port_number", sa.Integer()),
        sa.Column("name", sa.String()),
        sa.Column("vlan", sa.Integer()),
        sa.Column("enabled", sa.Boolean()),
        sa.Column("poe", sa.Boolean()),
        sa.Column("speed", sa.String()),
        sa.Column("duplex", sa.String()),
        sa.Column("macs", sa.String()),
    )


def downgrade():
    op.drop_table("switch_ports")