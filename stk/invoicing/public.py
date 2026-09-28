from datetime import datetime
from pathlib import Path

from quart import Blueprint, Response, current_app, g, render_template, send_file
from sqlalchemy import select

from stk.invoicing.models import BusinessSettings, Invoice
from stk.invoicing.presentation import service_period, tax_statement
from stk.invoicing.views import resolve_invoice_archive

public_invoice = Blueprint("public_invoice", __name__, static_folder="../static")


@public_invoice.route("/i/<token>")
async def view_invoice(token):
    result = await g.db_session.execute(
        select(Invoice).where(Invoice.share_token == token)
    )
    invoice = result.scalar_one_or_none()
    if not invoice or not invoice.share_is_active():
        return await render_template(
            "invoicing/invoice_unavailable.html", pdf_missing=False
        ), 404

    # Mark as viewed on first access
    if invoice.status == "sent" and not invoice.viewed_at:
        invoice.viewed_at = datetime.now()
        invoice.status = "viewed"
        await g.db_session.commit()

    settings = await BusinessSettings.get_or_create(invoice.user_id)
    await g.db_session.commit()

    bill_to = None
    if invoice.is_issued:
        bill_to = {
            "name": invoice.client_name_snapshot,
            "email": invoice.client_email_snapshot,
            "address": invoice.client_address_snapshot,
        }
    elif invoice.client:
        bill_to = {
            "name": invoice.client.name,
            "email": invoice.client.email,
            "address": "\n".join(
                filter(
                    None,
                    [
                        invoice.client.address_line1,
                        invoice.client.address_line2,
                        invoice.client.address_line3,
                    ],
                )
            ),
        }

    return await render_template(
        "invoicing/public_invoice.html",
        invoice=invoice,
        settings=settings,
        service_period=service_period(invoice),
        tax_statement=tax_statement(invoice),
        bill_to=bill_to,
    )


@public_invoice.route("/i/<token>/pdf")
async def public_pdf(token):
    result = await g.db_session.execute(
        select(Invoice).where(Invoice.share_token == token)
    )
    invoice = result.scalar_one_or_none()
    if not invoice or not invoice.share_is_active():
        return await render_template(
            "invoicing/invoice_unavailable.html", pdf_missing=False
        ), 404

    if invoice.is_issued:
        path = None
        if invoice.archived_pdf_path:
            try:
                path = resolve_invoice_archive(
                    current_app.instance_path, invoice.archived_pdf_path
                )
            except ValueError:
                current_app.logger.error(
                    "Invalid archived PDF path for invoice %s", invoice.id
                )
        if path is None or not Path(path).is_file():
            return await render_template(
                "invoicing/invoice_unavailable.html", pdf_missing=True
            ), 503
        return await send_file(
            path,
            mimetype="application/pdf",
            as_attachment=False,
            attachment_filename=f"{invoice.invoice_number}.pdf",
        )

    settings = await BusinessSettings.get_or_create(invoice.user_id)
    await g.db_session.commit()

    from stk.invoicing.pdf import generate_invoice_pdf

    pdf_bytes = await generate_invoice_pdf(invoice, settings)
    return Response(
        pdf_bytes,
        content_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'
        },
    )
