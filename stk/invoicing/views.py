import logging
import os

import orjson as json
from quart import Blueprint, Response, current_app, g, render_template, request
from quart_security import auth_required, current_user
from sqlalchemy import extract, func, select

from stk.invoicing.models import (
    BusinessSettings,
    Client,
    Invoice,
    InvoiceItem,
    Payment,
)
from stk.user.models import Activity

log = logging.getLogger(__name__)

invoicing = Blueprint("invoicing", __name__, static_folder="../static")

PER_PAGE = 25


@invoicing.before_request
@auth_required("session")
async def before_request():
    pass


@invoicing.after_request
async def add_header(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


# ── Page Routes ──


@invoicing.route("/invoices/")
async def invoices():
    return await render_template("invoicing/invoices.html")


@invoicing.route("/invoices/new")
async def invoice_new():
    settings = await BusinessSettings.get_or_create(current_user.id)
    return await render_template(
        "invoicing/invoice_edit.html",
        invoice_data=None,
        settings_data=settings.to_dict(),
    )


@invoicing.route("/invoices/<int:id>")
async def invoice_detail(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    settings = await BusinessSettings.get_or_create(current_user.id)
    return await render_template(
        "invoicing/invoice_edit.html",
        invoice_data=invoice.to_dict(),
        settings_data=settings.to_dict(),
    )


@invoicing.route("/clients/")
async def clients():
    return await render_template("invoicing/clients.html")


@invoicing.route("/reports/")
async def reports():
    return await render_template("invoicing/reports.html")


@invoicing.route("/settings/business/")
async def settings_page():
    return await render_template("invoicing/settings.html")


# ── Settings API ──


@invoicing.route("/api/settings")
async def api_settings_get():
    settings = await BusinessSettings.get_or_create(current_user.id)
    await g.db_session.commit()
    return Response(json.dumps(settings.to_dict()), content_type="application/json")


@invoicing.post("/api/settings")
async def api_settings_update():
    settings = await BusinessSettings.get_or_create(current_user.id)
    data = await request.json
    try:
        settings.from_dict(data)
        await g.db_session.commit()
        return {"message": "Settings saved"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error saving settings")
        return {"message": "Error saving settings"}, 412


@invoicing.post("/api/settings/logo")
async def api_settings_logo():
    files = await request.files
    logo = files.get("logo")
    if not logo:
        return {"message": "No file provided"}, 400

    upload_dir = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(logo.filename)[1].lower()
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
    if ext not in allowed:
        return {"message": "Invalid file type"}, 400

    filename = f"logo_{current_user.id}{ext}"
    filepath = os.path.join(upload_dir, filename)
    await logo.save(filepath)

    settings = await BusinessSettings.get_or_create(current_user.id)
    settings.logo_path = f"uploads/{filename}"
    await g.db_session.commit()
    return {"message": "Logo uploaded", "logo_path": settings.logo_path}


@invoicing.post("/api/settings/logo/remove")
async def api_settings_logo_remove():
    settings = await BusinessSettings.get_or_create(current_user.id)
    if settings.logo_path:
        filepath = os.path.join(current_app.static_folder, settings.logo_path)
        if os.path.exists(filepath):
            os.remove(filepath)
        settings.logo_path = None
        await g.db_session.commit()
    return {"message": "Logo removed"}


# ── Client API ──


@invoicing.route("/api/clients")
async def api_clients():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", PER_PAGE, type=int)
    search = request.args.get("search", "").strip()

    query = select(Client).where(Client.user_id == current_user.id)
    count_query = (
        select(func.count())
        .select_from(Client)
        .where(Client.user_id == current_user.id)
    )

    if search:
        query = query.where(Client.name.ilike(f"%{search}%"))
        count_query = count_query.where(Client.name.ilike(f"%{search}%"))

    total = (await g.db_session.execute(count_query)).scalar()
    result = await g.db_session.execute(
        query.order_by(Client.name).offset((page - 1) * per_page).limit(per_page)
    )
    items = [c.to_dict() for c in result.scalars().all()]
    return Response(
        json.dumps({"items": items, "total": total, "perPage": per_page}),
        content_type="application/json",
    )


@invoicing.route("/api/client/search")
async def api_client_search():
    q = request.args.get("q", "").strip()
    query = select(Client).where(Client.user_id == current_user.id)
    if q:
        query = query.where(Client.name.ilike(f"%{q}%"))
    result = await g.db_session.execute(query.order_by(Client.name).limit(20))
    items = [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "address_line1": c.address_line1,
            "address_line2": c.address_line2,
            "phone": c.phone,
        }
        for c in result.scalars().all()
    ]
    return Response(json.dumps(items), content_type="application/json")


@invoicing.post("/api/client/")
async def api_client_create():
    data = await request.json
    client_data = data.get("item", {})
    client = Client(user_id=current_user.id)
    client.from_dict(client_data)
    g.db_session.add(client)
    try:
        await g.db_session.flush()
        await Activity.register(
            current_user.id, "Client Create", {"id": client.id, "name": client.name}
        )
        await g.db_session.commit()
        return {"message": "Client created", "id": client.id}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error creating client")
        return {"message": "Error creating client"}, 412


@invoicing.post("/api/client/<int:id>")
async def api_client_update(id):
    client = await g.db_session.get(Client, id)
    if not client or client.user_id != current_user.id:
        return {"message": "Not found"}, 404
    data = await request.json
    client_data = data.get("item", {})
    try:
        client.from_dict(client_data)
        await g.db_session.commit()
        return {"message": "Client updated"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error updating client")
        return {"message": "Error updating client"}, 412


@invoicing.route("/api/client/<int:id>", methods=["DELETE"])
async def api_client_delete(id):
    client = await g.db_session.get(Client, id)
    if not client or client.user_id != current_user.id:
        return {"message": "Not found"}, 404
    try:
        await g.db_session.delete(client)
        await Activity.register(current_user.id, "Client Delete", {"name": client.name})
        await g.db_session.commit()
        return {"message": "Client deleted"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error deleting client")
        return {"message": "Error deleting client"}, 412


# ── Invoice API ──


@invoicing.route("/api/invoices")
async def api_invoices():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", PER_PAGE, type=int)
    status = request.args.get("status", "all")
    search = request.args.get("search", "").strip()

    query = select(Invoice).where(Invoice.user_id == current_user.id)
    count_query = (
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.user_id == current_user.id)
    )

    if status == "outstanding":
        query = query.where(Invoice.status.in_(["draft", "sent", "viewed", "overdue"]))
        count_query = count_query.where(
            Invoice.status.in_(["draft", "sent", "viewed", "overdue"])
        )
    elif status == "paid":
        query = query.where(Invoice.status == "paid")
        count_query = count_query.where(Invoice.status == "paid")

    if search:
        query = query.join(Client).where(Client.name.ilike(f"%{search}%"))
        count_query = count_query.join(Client).where(Client.name.ilike(f"%{search}%"))

    total = (await g.db_session.execute(count_query)).scalar()
    result = await g.db_session.execute(
        query.order_by(Invoice.date.desc(), Invoice.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = []
    for inv in result.scalars().all():
        items.append(
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "client_name": inv.client.name if inv.client else "",
                "date": inv.date.isoformat() if inv.date else "",
                "total": str(inv.total),
                "balance_due": str(inv.balance_due),
                "status": inv.status,
                "currency_symbol": inv.currency_symbol,
            }
        )

    return Response(
        json.dumps({"items": items, "total": total, "perPage": per_page}),
        content_type="application/json",
    )


@invoicing.post("/api/invoice/")
async def api_invoice_create():
    data = await request.json
    settings = await BusinessSettings.get_or_create(current_user.id)
    invoice = Invoice(user_id=current_user.id)
    invoice.invoice_number = settings.generate_invoice_number()
    invoice.from_dict(data)
    invoice.snapshot_business(settings)

    # line items
    for i, item_data in enumerate(data.get("items", [])):
        item = InvoiceItem(sort_order=i)
        item.from_dict(item_data)
        invoice.items.append(item)

    invoice.recalculate()
    g.db_session.add(invoice)
    try:
        await g.db_session.flush()
        await Activity.register(
            current_user.id, "Invoice Create", {"number": invoice.invoice_number}
        )
        await g.db_session.commit()
        return {"message": "Invoice created", "id": invoice.id}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error creating invoice")
        return {"message": "Error creating invoice"}, 412


@invoicing.post("/api/invoice/<int:id>")
async def api_invoice_update(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404

    data = await request.json
    invoice.from_dict(data)

    # replace line items
    if "items" in data:
        invoice.items.clear()
        await g.db_session.flush()
        for i, item_data in enumerate(data["items"]):
            item = InvoiceItem(sort_order=i)
            item.from_dict(item_data)
            invoice.items.append(item)

    invoice.recalculate()
    try:
        await g.db_session.commit()
        return {"message": "Invoice updated"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error updating invoice")
        return {"message": "Error updating invoice"}, 412


@invoicing.route("/api/invoice/<int:id>", methods=["DELETE"])
async def api_invoice_delete(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    number = invoice.invoice_number
    try:
        await g.db_session.delete(invoice)
        await Activity.register(current_user.id, "Invoice Delete", {"number": number})
        await g.db_session.commit()
        return {"message": "Invoice deleted"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error deleting invoice")
        return {"message": "Error deleting invoice"}, 412


@invoicing.route("/api/invoice/<int:id>")
async def api_invoice_get(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    return Response(json.dumps(invoice.to_dict()), content_type="application/json")


@invoicing.route("/api/invoice/<int:id>/pdf")
async def api_invoice_pdf(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    settings = await BusinessSettings.get_or_create(current_user.id)
    from stk.invoicing.pdf import generate_invoice_pdf

    pdf_data = await generate_invoice_pdf(invoice, settings)
    return Response(
        bytes(pdf_data),
        content_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'
        },
    )


@invoicing.post("/api/invoice/<int:id>/payment")
async def api_invoice_payment_add(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    data = await request.json
    payment = Payment(invoice_id=invoice.id)
    payment.from_dict(data)
    g.db_session.add(payment)
    await g.db_session.flush()
    await g.db_session.refresh(invoice, ["payments"])
    invoice.recalculate()
    try:
        await g.db_session.commit()
        return {"message": "Payment recorded"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error recording payment")
        return {"message": "Error recording payment"}, 412


@invoicing.route("/api/invoice/<int:id>/payment/<int:pid>", methods=["DELETE"])
async def api_invoice_payment_delete(id, pid):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    payment = await g.db_session.get(Payment, pid)
    if not payment or payment.invoice_id != invoice.id:
        return {"message": "Payment not found"}, 404
    try:
        await g.db_session.delete(payment)
        await g.db_session.flush()
        await g.db_session.refresh(invoice, ["payments"])
        invoice.recalculate()
        await g.db_session.commit()
        return {"message": "Payment removed"}
    except Exception:
        await g.db_session.rollback()
        log.exception("Error removing payment")
        return {"message": "Error removing payment"}, 412


@invoicing.post("/api/invoice/<int:id>/status")
async def api_invoice_status(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    data = await request.json
    new_status = data.get("status")
    if new_status not in ("draft", "sent", "viewed", "paid", "overdue", "cancelled"):
        return {"message": "Invalid status"}, 400
    invoice.status = new_status
    try:
        await g.db_session.commit()
        return {"message": f"Status updated to {new_status}"}
    except Exception:
        await g.db_session.rollback()
        return {"message": "Error updating status"}, 412


@invoicing.post("/api/invoice/<int:id>/share")
async def api_invoice_share(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    token = invoice.generate_share_token()
    await g.db_session.commit()
    return {"token": token, "url": f"/i/{token}"}


@invoicing.post("/api/invoice/<int:id>/send")
async def api_invoice_send(id):
    from datetime import datetime

    from stk.invoicing.pdf import generate_invoice_pdf
    from stk.tasks import run_in_background

    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404

    if not invoice.client or not invoice.client.email:
        return {"message": "Client has no email address"}, 400

    settings = await BusinessSettings.get_or_create(current_user.id)
    pdf_bytes = await generate_invoice_pdf(invoice, settings)

    # Build share link
    token = invoice.generate_share_token()
    share_url = request.host_url.rstrip("/") + f"/i/{token}"

    subject = f"{settings.invoice_title or 'Invoice'} {invoice.invoice_number} from {settings.business_name}"
    body = f"Please find attached {settings.invoice_title or 'Invoice'} {invoice.invoice_number}.\n\nView online: {share_url}"

    html_body = await render_template(
        "invoicing/email_invoice.html",
        invoice=invoice,
        settings=settings,
        share_url=share_url,
    )

    recipient = invoice.client.email
    sender = settings.email or None

    async def _send():
        from email.message import EmailMessage as EM

        import aiosmtplib

        app = current_app._get_current_object()
        msg = EM()
        msg["Subject"] = subject
        msg["From"] = sender or app.config.get(
            "SECURITY_EMAIL_SENDER", "noreply@localhost"
        )
        msg["To"] = recipient
        msg.set_content(body)
        msg.add_alternative(html_body, subtype="html")
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"{invoice.invoice_number}.pdf",
        )
        await aiosmtplib.send(
            msg,
            hostname=app.config.get("MAIL_SERVER", "localhost"),
            port=app.config.get("MAIL_PORT", 465),
            username=app.config.get("MAIL_USERNAME"),
            password=app.config.get("MAIL_PASSWORD"),
            use_tls=app.config.get("MAIL_USE_SSL", False),
            start_tls=app.config.get("MAIL_USE_TLS", False),
        )

    await run_in_background(_send())

    invoice.status = "sent"
    invoice.sent_at = datetime.now()
    await g.db_session.commit()
    return {"message": f"Invoice sent to {recipient}"}


# ── Reports API ──


@invoicing.route("/api/reports/monthly")
async def api_reports_monthly():
    year = request.args.get("year", None, type=int)
    if not year:
        from datetime import date

        year = date.today().year

    settings = await BusinessSettings.get_or_create(current_user.id)
    await g.db_session.commit()

    result = await g.db_session.execute(
        select(
            extract("month", Invoice.date).label("month"),
            func.count(func.distinct(Invoice.client_id)).label("clients"),
            func.count(Invoice.id).label("invoices"),
            func.coalesce(func.sum(Invoice.total), 0).label("total"),
        )
        .where(Invoice.user_id == current_user.id)
        .where(Invoice.status == "paid")
        .where(extract("year", Invoice.date) == year)
        .group_by(extract("month", Invoice.date))
    )

    monthly = {
        int(r.month): {
            "clients": r.clients,
            "invoices": r.invoices,
            "total": str(r.total),
        }
        for r in result.all()
    }

    months = []
    for m in range(1, 13):
        data = monthly.get(m, {"clients": 0, "invoices": 0, "total": "0"})
        months.append({"month": m, **data})

    # yearly totals
    yearly_total = sum(float(monthly.get(m, {}).get("total", 0)) for m in range(1, 13))
    yearly_invoices = sum(monthly.get(m, {}).get("invoices", 0) for m in range(1, 13))

    return Response(
        json.dumps(
            {
                "year": year,
                "months": months,
                "currency_symbol": settings.currency_symbol,
                "yearly_total": str(yearly_total),
                "yearly_invoices": yearly_invoices,
            }
        ),
        content_type="application/json",
    )
