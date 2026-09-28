import asyncio
import logging
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import orjson as json
from quart import (
    Blueprint,
    Response,
    current_app,
    g,
    render_template,
    request,
    send_file,
)
from quart_security import auth_required, current_user
from sqlalchemy import case, extract, func, or_, select
from sqlalchemy.exc import IntegrityError

from stk.invoicing.models import (
    BusinessSettings,
    Client,
    Invoice,
    InvoiceItem,
    Payment,
)
from stk.invoicing.queries import invoice_conditions
from stk.user.models import Activity

log = logging.getLogger(__name__)

invoicing = Blueprint("invoicing", __name__, static_folder="../static")

PER_PAGE = 25


def business_profile_missing(settings):
    missing = []
    if not settings.business_name:
        missing.append("business name")
    if not any(
        (settings.address_line1, settings.address_line2, settings.address_line3)
    ):
        missing.append("business address")
    if not settings.tax_number and not settings.vat_id:
        missing.append("Steuernummer or VAT ID")
    return missing


def invoice_archive_relative_path(user_id, invoice_id):
    return Path("invoices", str(user_id), str(invoice_id), f"invoice-{invoice_id}.pdf")


def invoice_archive_path(instance_path, user_id, invoice_id):
    path = Path(instance_path) / invoice_archive_relative_path(user_id, invoice_id)
    return str(path.parent), str(path)


def resolve_invoice_archive(instance_path, stored_path):
    root = (Path(instance_path) / "invoices").resolve()
    candidate = Path(stored_path)
    candidate = (
        candidate.resolve()
        if candidate.is_absolute()
        else (Path(instance_path) / candidate).resolve()
    )
    if not candidate.is_relative_to(root):
        raise ValueError("Invoice archive path is outside invoice archive")
    return candidate


async def next_free_invoice_number(settings):
    while True:
        number = settings.generate_invoice_number()
        exists = await g.db_session.scalar(
            select(Invoice.id).where(Invoice.invoice_number == number)
        )
        if not exists:
            return number


async def _issue_invoice(invoice, status="sent"):
    if invoice.is_issued:
        return None
    settings = await BusinessSettings.get_or_create(current_user.id)
    invoice.snapshot_supplier(settings)
    if invoice.client:
        invoice.client_vat_id = invoice.client.vat_id or invoice.client_vat_id or ""
        invoice.client_name_snapshot = invoice.client.name or ""
        invoice.client_email_snapshot = invoice.client.email or ""
        invoice.client_address_snapshot = "\n".join(
            filter(
                None,
                [
                    invoice.client.address_line1,
                    invoice.client.address_line2,
                    invoice.client.address_line3,
                ],
            )
        )
    errors = invoice.validate_for_issue()
    if errors:
        return errors
    from stk.invoicing.pdf import generate_invoice_pdf

    invoice.invoice_title_snapshot = settings.invoice_title or "Invoice"
    invoice.payment_instructions_snapshot = settings.payment_instructions or ""
    pdf_bytes = bytes(await generate_invoice_pdf(invoice, settings))
    relative_archive = invoice_archive_relative_path(current_user.id, invoice.id)
    archive_path = Path(current_app.instance_path) / relative_archive
    os.makedirs(archive_path.parent, exist_ok=True)
    if os.path.exists(archive_path):
        return ["Issued invoice archive already exists"]
    created_archive = False
    try:
        with open(archive_path, "xb") as archive:
            archive.write(pdf_bytes)
        created_archive = True
        invoice.archived_pdf_path = relative_archive.as_posix()
        invoice.issued_at = datetime.now()
        if status in ("sent", "viewed"):
            invoice.sent_at = invoice.sent_at or invoice.issued_at
        invoice.status = status
        await Activity.register(
            current_user.id, "Invoice Issue", {"number": invoice.invoice_number}
        )
        await g.db_session.commit()
    except FileExistsError:
        await g.db_session.rollback()
        return ["Invoice issuance is already in progress"]
    except Exception:
        await g.db_session.rollback()
        if created_archive and os.path.exists(archive_path):
            os.unlink(archive_path)
        raise
    return None


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
        profile_missing=business_profile_missing(settings),
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
        profile_missing=business_profile_missing(settings),
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
    return Response(
        json.dumps(
            {
                **settings.to_dict(),
                "profile_missing": business_profile_missing(settings),
            }
        ),
        content_type="application/json",
    )


@invoicing.post("/api/settings")
async def api_settings_update():
    settings = await BusinessSettings.get_or_create(current_user.id)
    data = await request.json
    try:
        settings.from_dict(data)
        await g.db_session.commit()
        return {
            "message": "Settings saved",
            "settings": settings.to_dict(),
            "profile_missing": business_profile_missing(settings),
        }
    except ValueError as exc:
        await g.db_session.rollback()
        return {"message": str(exc)}, 400
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

    if page < 1 or per_page < 1 or per_page > 100:
        return {"message": "Invalid pagination"}, 400

    query = select(Client).where(Client.user_id == current_user.id)
    count_query = (
        select(func.count())
        .select_from(Client)
        .where(Client.user_id == current_user.id)
    )

    if search:
        query = query.where(Client.name.icontains(search, autoescape=True))
        count_query = count_query.where(Client.name.icontains(search, autoescape=True))

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
            "vat_id": c.vat_id,
        }
        for c in result.scalars().all()
    ]
    return Response(json.dumps(items), content_type="application/json")


@invoicing.post("/api/client/")
async def api_client_create():
    data = await request.json
    client_data = data.get("item", {})
    if not (client_data.get("name") or "").strip():
        return {
            "message": "Customer name is required",
            "field_errors": {"name": "Enter a customer name"},
        }, 400
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
    if not (client_data.get("name") or "").strip():
        return {
            "message": "Customer name is required",
            "field_errors": {"name": "Enter a customer name"},
        }, 400
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

    if page < 1 or per_page < 1 or per_page > 100:
        return {"message": "Invalid pagination"}, 400
    try:
        conditions = invoice_conditions(current_user.id, status, date.today())
    except ValueError as error:
        return {"message": str(error)}, 400
    query = select(Invoice).outerjoin(Client)
    count_query = select(func.count()).select_from(Invoice).outerjoin(Client)
    if search:
        customer_name = case(
            (Invoice.issued_at.is_not(None), Invoice.client_name_snapshot),
            else_=Client.name,
        )
        conditions.append(
            or_(
                Invoice.invoice_number.icontains(search, autoescape=True),
                customer_name.icontains(search, autoescape=True),
            )
        )
    query = query.where(*conditions)
    count_query = count_query.where(*conditions)

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
                "client_name": inv.client_name_snapshot
                if inv.is_issued
                else (inv.client.name if inv.client else ""),
                "date": inv.date.isoformat() if inv.date else "",
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
                "total": str(inv.total),
                "balance_due": str(inv.balance_due),
                "status": inv.status,
                "currency_symbol": inv.currency_symbol,
                "currency_code": inv.currency_code,
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
    invoice.snapshot_business(settings)
    invoice.from_dict(data)
    if invoice.client_id:
        client = await g.db_session.get(Client, invoice.client_id)
        if not client or client.user_id != current_user.id:
            return {"message": "Customer not found"}, 400
        invoice.client = client
        invoice.client_vat_id = client.vat_id or invoice.client_vat_id or ""

    # line items
    for i, item_data in enumerate(data.get("items", [])):
        item = InvoiceItem(sort_order=i)
        item.from_dict(item_data)
        invoice.items.append(item)

    if not invoice.invoice_number:
        invoice.invoice_number = await next_free_invoice_number(settings)

    invoice.recalculate()
    g.db_session.add(invoice)
    try:
        await g.db_session.flush()
        await Activity.register(
            current_user.id, "Invoice Create", {"number": invoice.invoice_number}
        )
        await g.db_session.refresh(invoice)
        response = {
            "message": "Invoice created",
            "id": invoice.id,
            "invoice": invoice.to_dict(),
            "issue_errors": invoice.validate_for_issue(),
        }
        await g.db_session.commit()
        return response
    except IntegrityError:
        await g.db_session.rollback()
        return {"message": "Invoice number already in use"}, 409
    except Exception:
        await g.db_session.rollback()
        log.exception("Error creating invoice")
        return {"message": "Error creating invoice"}, 412


@invoicing.post("/api/invoice/<int:id>")
async def api_invoice_update(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    if invoice.is_issued:
        return {"message": "Issued invoices cannot be edited"}, 409

    data = await request.json
    invoice.from_dict(data)
    if invoice.client_id:
        client = await g.db_session.get(Client, invoice.client_id)
        if not client or client.user_id != current_user.id:
            return {"message": "Customer not found"}, 400
        invoice.client = client
        invoice.client_vat_id = client.vat_id or invoice.client_vat_id or ""
    else:
        invoice.client = None

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
        await g.db_session.flush()
        await g.db_session.refresh(invoice)
        response = {
            "message": "Invoice updated",
            "invoice": invoice.to_dict(),
            "issue_errors": invoice.validate_for_issue(),
        }
        await g.db_session.commit()
        return response
    except IntegrityError:
        await g.db_session.rollback()
        return {"message": "Invoice number already in use"}, 409
    except Exception:
        await g.db_session.rollback()
        log.exception("Error updating invoice")
        return {"message": "Error updating invoice"}, 412


@invoicing.route("/api/invoice/<int:id>", methods=["DELETE"])
async def api_invoice_delete(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    if invoice.is_issued:
        return {"message": "Issued invoices cannot be deleted"}, 409
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
            return {"message": "The archived invoice PDF is unavailable"}, 503
        return await send_file(
            path,
            mimetype="application/pdf",
            as_attachment=False,
            attachment_filename=f"{invoice.invoice_number}.pdf",
        )
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
    if invoice.status == "cancelled":
        return {"message": "Cancelled invoices cannot accept payments"}, 409
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
    if invoice.status == "cancelled":
        return {"message": "Cancelled invoices cannot change payments"}, 409
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
    if invoice.status == "cancelled":
        return {"message": "Cancelled invoices cannot change status"}, 409
    if new_status == "cancelled":
        return {"message": "Use the cancellation action"}, 400
    if invoice.is_issued and new_status == "draft":
        return {"message": "Issued invoices cannot be reopened"}, 409
    if new_status != "draft" and not invoice.is_issued:
        if errors := await _issue_invoice(invoice, status=new_status):
            return {"message": "; ".join(errors)}, 400
    else:
        invoice.status = new_status
    if new_status == "draft":
        invoice.paid_at = None
    elif new_status == "sent":
        from datetime import datetime

        if not invoice.sent_at:
            invoice.sent_at = datetime.now()
    try:
        await g.db_session.commit()
        return {"message": f"Status updated to {new_status}"}
    except Exception:
        await g.db_session.rollback()
        return {"message": "Error updating status"}, 412


@invoicing.post("/api/invoice/<int:id>/issue")
async def api_invoice_issue(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    if errors := await _issue_invoice(invoice):
        return {"message": "; ".join(errors)}, 400
    await g.db_session.commit()
    return {"message": "Invoice issued"}


@invoicing.post("/api/invoice/<int:id>/cancel")
async def api_invoice_cancel(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    if not invoice.is_issued:
        return {"message": "Only issued invoices can be cancelled"}, 409
    if invoice.status == "cancelled":
        return {"message": "Invoice is already cancelled"}, 409
    invoice.status = "cancelled"
    invoice.cancelled_at = datetime.now()
    await Activity.register(
        current_user.id, "Invoice Cancel", {"number": invoice.invoice_number}
    )
    await g.db_session.commit()
    return {"message": "Invoice cancelled"}


@invoicing.post("/api/invoice/<int:id>/share")
async def api_invoice_share(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    if not invoice.is_issued:
        return {"message": "Only issued invoices can be shared"}, 409
    token = invoice.ensure_share_token()
    await g.db_session.commit()
    return {
        "token": token,
        "url": f"/i/{token}",
        "expires_at": invoice.share_token_expires_at.isoformat(),
    }


@invoicing.delete("/api/invoice/<int:id>/share")
async def api_invoice_share_revoke(id):
    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404
    invoice.revoke_share_token()
    await g.db_session.commit()
    return {"message": "Share link revoked"}


@invoicing.post("/api/invoice/<int:id>/send")
async def api_invoice_send(id):
    from aiosmtplib.errors import SMTPException, SMTPTimeoutError

    invoice = await g.db_session.get(Invoice, id)
    if not invoice or invoice.user_id != current_user.id:
        return {"message": "Not found"}, 404

    if not invoice.client or not invoice.client.email:
        return {"message": "Customer has no email address"}, 400
    if invoice.status == "cancelled":
        return {"message": "Cancelled invoices cannot be sent"}, 409

    if not invoice.is_issued:
        if errors := await _issue_invoice(invoice):
            return {"message": "; ".join(errors)}, 400

    settings = await BusinessSettings.get_or_create(current_user.id)
    if not invoice.archived_pdf_path:
        return {"message": "Issued invoice archive is missing"}, 500
    with open(
        resolve_invoice_archive(current_app.instance_path, invoice.archived_pdf_path),
        "rb",
    ) as archive:
        pdf_bytes = archive.read()

    # Build share link
    token = invoice.ensure_share_token()
    share_url = request.host_url.rstrip("/") + f"/i/{token}"

    invoice_title = invoice.invoice_title_snapshot or "Invoice"
    subject = f"{invoice_title} {invoice.invoice_number} from {invoice.from_name}"
    introduction = (
        settings.default_email_message
        or f"Please find attached {invoice_title} {invoice.invoice_number}."
    )
    body = f"{introduction}\n\nView online: {share_url}"

    html_body = await render_template(
        "invoicing/email_invoice.html",
        invoice=invoice,
        settings=settings,
        share_url=share_url,
        introduction=introduction,
    )

    recipient = invoice.client.email
    recipients = [recipient]
    if (
        settings.send_copy_to_self
        and current_user.email.casefold() != recipient.casefold()
    ):
        recipients.append(current_user.email)
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
        return await aiosmtplib.send(
            msg,
            recipients=recipients,
            hostname=app.config.get("MAIL_SERVER", "localhost"),
            port=app.config.get("MAIL_PORT", 465),
            username=app.config.get("MAIL_USERNAME"),
            password=app.config.get("MAIL_PASSWORD"),
            use_tls=app.config.get("MAIL_USE_SSL", False),
            start_tls=app.config.get("MAIL_USE_TLS", False),
        )

    # Persist the share link before handing it to an external mail server.
    await g.db_session.commit()
    try:
        refused, _ = await asyncio.wait_for(_send(), timeout=30)
    except (TimeoutError, SMTPTimeoutError, OSError):
        log.warning("Invoice email outcome unknown", exc_info=True)
        return {
            "message": "Email status could not be confirmed. Check before sending again."
        }, 504
    except SMTPException:
        log.warning("Invoice email rejected", exc_info=True)
        return {
            "message": "The mail server could not accept this email. Check email settings and try again."
        }, 502
    if recipient.casefold() in {address.casefold() for address in refused}:
        return {
            "message": "The mail server rejected the customer email. Your private copy was accepted. Check the customer address before trying again."
        }, 502
    if refused:
        return {
            "message": "Customer email accepted by the mail server, but your private copy was rejected. Do not resend the customer email for this."
        }
    return {"message": "Email accepted by the mail server"}


# ── Reports API ──


@invoicing.route("/api/reports/monthly")
async def api_reports_monthly():
    year = request.args.get("year", date.today().year, type=int)
    if not 1 <= year <= 9999:
        return {"message": "Invalid year"}, 400
    settings = await BusinessSettings.get_or_create(current_user.id)
    await g.db_session.commit()
    conditions = invoice_conditions(current_user.id, "paid", date.today())
    conditions.append(extract("year", Invoice.date) == year)
    currencies = list(
        (
            await g.db_session.scalars(
                select(Invoice.currency_code)
                .where(*conditions)
                .distinct()
                .order_by(Invoice.currency_code)
            )
        ).all()
    )
    currency = request.args.get("currency")
    if currency not in currencies:
        currency = (
            settings.currency_code
            if settings.currency_code in currencies or not currencies
            else currencies[0]
        )
    result = await g.db_session.execute(
        select(
            extract("month", Invoice.date).label("month"),
            func.count(func.distinct(Invoice.client_id)).label("clients"),
            func.count(Invoice.id).label("invoices"),
            func.coalesce(func.sum(Invoice.total), 0).label("total"),
        )
        .where(*conditions, Invoice.currency_code == currency)
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
    months = [
        {
            "month": month,
            **monthly.get(month, {"clients": 0, "invoices": 0, "total": "0.00"}),
        }
        for month in range(1, 13)
    ]
    return {
        "year": year,
        "months": months,
        "currencies": currencies,
        "currency_code": currency,
        "yearly_total": str(
            sum((Decimal(row["total"]) for row in months), Decimal("0.00"))
        ),
        "yearly_invoices": sum(row["invoices"] for row in months),
    }
