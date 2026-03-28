from datetime import datetime

from quart import Blueprint, Response, g, render_template
from sqlalchemy import select

from stk.invoicing.models import BusinessSettings, Invoice

public_invoice = Blueprint("public_invoice", __name__, static_folder="../static")


@public_invoice.route("/i/<token>")
async def view_invoice(token):
    result = await g.db_session.execute(
        select(Invoice).where(Invoice.share_token == token)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        return "Invoice not found", 404

    # Mark as viewed on first access
    if invoice.status == "sent" and not invoice.viewed_at:
        invoice.viewed_at = datetime.now()
        invoice.status = "viewed"
        await g.db_session.commit()

    settings = await BusinessSettings.get_or_create(invoice.user_id)
    await g.db_session.commit()

    return await render_template(
        "invoicing/public_invoice.html", invoice=invoice, settings=settings
    )


@public_invoice.route("/i/<token>/pdf")
async def public_pdf(token):
    result = await g.db_session.execute(
        select(Invoice).where(Invoice.share_token == token)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        return "Invoice not found", 404

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
