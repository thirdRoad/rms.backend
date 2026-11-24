"""add checks and check_products

Revision ID: a3c91f27d4b5
Revises: 8e38db3435b8
Create Date: 2026-11-23 20:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3c91f27d4b5"
down_revision = "8e38db3435b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "PAID", "CANCELLED", name="checkstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total", sa.Float(), nullable=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["tables.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("checks", schema=None) as batch_op:
        batch_op.create_index(
            "uq_checks_open_table_id",
            ["table_id"],
            unique=True,
            postgresql_where=sa.text("status = 'OPEN'"),
            sqlite_where=sa.text("status = 'OPEN'"),
        )

    op.create_table(
        "check_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("CHECK", "ORDER", name="checkproductsource"),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("check_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("check_products")
    with op.batch_alter_table("checks", schema=None) as batch_op:
        batch_op.drop_index("uq_checks_open_table_id")

    op.drop_table("checks")
    sa.Enum(name="checkproductsource").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="checkstatus").drop(op.get_bind(), checkfirst=True)
