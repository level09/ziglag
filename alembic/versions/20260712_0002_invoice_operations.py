"""Harden invoice operational lifecycle."""

from datetime import datetime, timedelta

import sqlalchemy as sa

from alembic import op

revision = "20260712_0002"
down_revision = "20260712_0001"
branch_labels = None
depends_on = None


def upgrade():
    expires = datetime.now() + timedelta(days=30)
    with op.batch_alter_table("invoice") as batch_op:
        batch_op.alter_column(
            "invoice_number", existing_type=sa.String(50), nullable=True
        )
        batch_op.add_column(
            sa.Column("share_token_expires_at", sa.DateTime(), nullable=True)
        )
    op.execute(
        sa.text(
            "UPDATE invoice SET share_token_expires_at = :expires WHERE share_token IS NOT NULL"
        ).bindparams(expires=expires)
    )


def downgrade():
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id FROM invoice WHERE invoice_number IS NULL ORDER BY id")
    ).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE invoice SET invoice_number = :number WHERE id = :id"),
            {"number": f"LEGACY-DRAFT-{row.id}", "id": row.id},
        )
    with op.batch_alter_table("invoice") as batch_op:
        batch_op.drop_column("share_token_expires_at")
        batch_op.alter_column(
            "invoice_number", existing_type=sa.String(50), nullable=False
        )
