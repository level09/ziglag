from datetime import date, timedelta
from decimal import Decimal

from quart import Blueprint, g, render_template
from quart_security import auth_required, current_user
from sqlalchemy import case, func, select

from stk.invoicing.models import BusinessSettings, Invoice
from stk.invoicing.queries import invoice_conditions
from stk.invoicing.views import business_profile_missing

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
    month_start = today.replace(day=1)
    previous_start = (month_start - timedelta(days=1)).replace(day=1)
    paid_totals = await g.db_session.execute(
        select(
            Invoice.currency_code,
            func.sum(case((Invoice.date >= month_start, Invoice.total), else_=0)).label(
                "current"
            ),
            func.sum(case((Invoice.date < month_start, Invoice.total), else_=0)).label(
                "previous"
            ),
        )
        .where(
            *invoice_conditions(uid, "paid", today),
            Invoice.date >= previous_start,
            Invoice.date <= today,
        )
        .group_by(Invoice.currency_code)
        .order_by(Invoice.currency_code)
    )
    paid_comparison = [
        {
            "currency_code": row.currency_code,
            "current": str(row.current),
            "previous": str(row.previous),
            "change": f"{(row.current - row.previous) / row.previous * Decimal('100'):+.1f}%"
            if row.previous
            else None,
        }
        for row in paid_totals
    ]

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
        "paid_comparison": paid_comparison,
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
    settings = await BusinessSettings.get_or_create(uid)
    await g.db_session.commit()
    return await render_template(
        "dashboard.html",
        stats=stats,
        recent=recent,
        profile_missing=business_profile_missing(settings),
    )
