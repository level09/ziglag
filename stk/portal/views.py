from datetime import date

from quart import Blueprint, g, render_template
from quart_security import auth_required, current_user
from sqlalchemy import func, select

from stk.invoicing.models import Invoice
from stk.invoicing.queries import invoice_conditions

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

    today = date.today()

    async def count(status):
        return await g.db_session.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(*invoice_conditions(uid, status, today))
        )

    balances = await g.db_session.execute(
        select(
            Invoice.currency_code,
            func.sum(Invoice.balance_due).label("amount"),
            func.count().label("count"),
        )
        .where(*invoice_conditions(uid, "outstanding", today))
        .group_by(Invoice.currency_code)
        .order_by(Invoice.currency_code)
    )
    stats = {
        "draft_count": await count("draft"),
        "overdue_count": await count("overdue"),
        "outstanding_by_currency": [
            {
                "currency_code": row.currency_code,
                "amount": str(row.amount),
                "count": row.count,
            }
            for row in balances
        ],
    }
    recent = (
        await g.db_session.scalars(
            select(Invoice)
            .where(Invoice.user_id == uid)
            .order_by(Invoice.date.desc(), Invoice.id.desc())
            .limit(5)
        )
    ).all()
    return await render_template("dashboard.html", stats=stats, recent=recent)
