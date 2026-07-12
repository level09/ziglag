"""Add German invoice fields and template snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "20260712_0001"
down_revision = "cfa8efad03ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("business_settings") as batch_op:
        batch_op.add_column(sa.Column("tax_number", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("vat_id", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "default_tax_treatment",
                sa.String(30),
                nullable=False,
                server_default="standard",
            )
        )
        batch_op.add_column(
            sa.Column(
                "default_invoice_template",
                sa.String(30),
                nullable=False,
                server_default="precision",
            )
        )
    with op.batch_alter_table("client") as batch_op:
        batch_op.add_column(sa.Column("vat_id", sa.String(100), nullable=True))
    with op.batch_alter_table("invoice") as batch_op:
        batch_op.add_column(sa.Column("service_date_from", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("service_date_to", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "tax_treatment",
                sa.String(30),
                nullable=False,
                server_default="standard",
            )
        )
        batch_op.add_column(sa.Column("tax_exemption_reason", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "template_key",
                sa.String(30),
                nullable=False,
                server_default="precision",
            )
        )
        batch_op.add_column(sa.Column("from_tax_number", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("from_vat_id", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("client_vat_id", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column("client_name_snapshot", sa.String(255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("client_email_snapshot", sa.String(255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("client_address_snapshot", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("invoice_title_snapshot", sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("payment_instructions_snapshot", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("archived_pdf_path", sa.String(500), nullable=True)
        )
        batch_op.add_column(sa.Column("issued_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("invoice") as batch_op:
        for name in (
            "cancelled_at",
            "payment_instructions_snapshot",
            "invoice_title_snapshot",
            "client_address_snapshot",
            "client_email_snapshot",
            "client_name_snapshot",
            "issued_at",
            "archived_pdf_path",
            "client_vat_id",
            "from_vat_id",
            "from_tax_number",
            "template_key",
            "tax_exemption_reason",
            "tax_treatment",
            "service_date_to",
            "service_date_from",
        ):
            batch_op.drop_column(name)
    with op.batch_alter_table("client") as batch_op:
        batch_op.drop_column("vat_id")
    with op.batch_alter_table("business_settings") as batch_op:
        batch_op.drop_column("default_invoice_template")
        batch_op.drop_column("default_tax_treatment")
        batch_op.drop_column("vat_id")
        batch_op.drop_column("tax_number")
