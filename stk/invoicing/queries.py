"""Invoice selection rules shared by workspace summaries and lists."""

from datetime import date

from sqlalchemy.sql.elements import ColumnElement

from stk.invoicing.models import Invoice


def invoice_conditions(
    user_id: int, status: str, today: date
) -> list[ColumnElement[bool]]:
    conditions = [Invoice.user_id == user_id]
    if status == "all":
        return conditions
    if status == "cancelled":
        return conditions + [Invoice.status == "cancelled"]
    conditions.append(Invoice.status != "cancelled")
    if status == "draft":
        return conditions + [Invoice.issued_at.is_(None)]
    conditions.append(Invoice.issued_at.is_not(None))
    if status == "paid":
        return conditions + [Invoice.status == "paid", Invoice.balance_due <= 0]
    if status not in ("outstanding", "overdue"):
        raise ValueError("Invalid invoice filter")
    conditions.append(Invoice.balance_due > 0)
    if status == "overdue":
        conditions.append(Invoice.due_date < today)
    return conditions
