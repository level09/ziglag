from quart import Blueprint, g, render_template
from quart_security import auth_required, current_user
from sqlalchemy import func, select

from stk.invoicing.models import BusinessSettings, Client, Invoice

portal = Blueprint("portal", __name__, static_folder="../static")


@portal.before_request
@auth_required("session")
async def before_request():
    pass


@portal.after_request
async def add_header(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@portal.route("/dashboard/")
async def dashboard():
    uid = current_user.id

    # Invoice stats
    total_invoices = (
        await g.db_session.execute(
            select(func.count()).select_from(Invoice).where(Invoice.user_id == uid)
        )
    ).scalar()

    outstanding = (
        await g.db_session.execute(
            select(func.coalesce(func.sum(Invoice.balance_due), 0)).where(
                Invoice.user_id == uid,
                Invoice.status.in_(["draft", "sent", "viewed", "overdue"]),
            )
        )
    ).scalar()

    total_paid = (
        await g.db_session.execute(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.user_id == uid, Invoice.status == "paid"
            )
        )
    ).scalar()

    clients_count = (
        await g.db_session.execute(
            select(func.count()).select_from(Client).where(Client.user_id == uid)
        )
    ).scalar()

    settings = await BusinessSettings.get_or_create(uid)
    await g.db_session.commit()

    # Recent invoices
    result = await g.db_session.execute(
        select(Invoice)
        .where(Invoice.user_id == uid)
        .order_by(Invoice.date.desc())
        .limit(5)
    )
    recent = []
    for inv in result.scalars().all():
        recent.append(
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "client_name": inv.client.name if inv.client else "",
                "date": inv.date.isoformat() if inv.date else "",
                "total": str(inv.total),
                "status": inv.status,
            }
        )

    stats = {
        "total_invoices": total_invoices,
        "outstanding": str(outstanding),
        "total_paid": str(total_paid),
        "clients": clients_count,
        "currency_symbol": settings.currency_symbol,
    }
    return await render_template("dashboard.html", stats=stats, recent=recent)
