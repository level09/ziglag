"""Harden invoice operational lifecycle."""

import sqlalchemy as sa

from alembic import op

revision = "20260712_0002"
down_revision = "20260712_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "invoice", sa.Column("share_token_expires_at", sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_column("invoice", "share_token_expires_at")
