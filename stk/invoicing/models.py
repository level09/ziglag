import dataclasses
import re
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal

from quart import g
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    select,
)
from sqlalchemy.orm import relationship

from stk.extensions import Base


@dataclasses.dataclass
class BusinessSettings(Base):
    __tablename__ = "business_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, unique=True)

    # business details
    business_name = Column(String(255), default="")
    business_number = Column(String(100), default="")
    business_number_label = Column(String(100), default="Business Number")
    tax_number = Column(String(100), default="")
    vat_id = Column(String(100), default="")
    owner_name = Column(String(255), default="")
    address_line1 = Column(String(255), default="")
    address_line2 = Column(String(255), default="")
    address_line3 = Column(String(255), default="")
    email = Column(String(255), default="")
    phone = Column(String(50), default="")
    mobile = Column(String(50), default="")
    website = Column(String(255), default="")
    logo_path = Column(String(500), nullable=True)

    # tax
    tax_type = Column(String(50), default="on_total")
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_label = Column(String(50), default="VAT")
    tax_inclusive = Column(Boolean, default=False)
    default_tax_treatment = Column(String(30), default="standard")
    default_invoice_template = Column(String(30), default="precision")

    # invoice numbering
    invoice_prefix = Column(String(20), default="INV")
    invoice_next_number = Column(Integer, default=1)

    # defaults
    default_invoice_notes = Column(Text, nullable=True)
    default_email_message = Column(Text, nullable=True)
    send_copy_to_self = Column(Boolean, default=False)

    # region
    locale = Column(String(10), default="en")
    currency_code = Column(String(3), default="USD")
    currency_symbol = Column(String(5), default="$")
    date_format = Column(String(20), default="YYYY-MM-DD")
    tax_year_begins = Column(Integer, default=1)

    # customization
    invoice_title = Column(String(100), default="Invoice")
    quantity_label = Column(String(50), default="Quantity")
    unit_cost_label = Column(String(50), default="Unit Cost")
    show_quantity_unit_cost = Column(Boolean, default=True)

    # payment methods
    payment_instructions = Column(Text, nullable=True)
    payment_paypal = Column(String(255), nullable=True)
    payment_other = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    async def get_or_create(cls, user_id):
        result = await g.db_session.execute(select(cls).where(cls.user_id == user_id))
        settings = result.scalar_one_or_none()
        if settings:
            return settings
        settings = cls(user_id=user_id)
        g.db_session.add(settings)
        await g.db_session.flush()
        return settings

    def generate_invoice_number(self):
        if not re.fullmatch(r"[A-Za-z0-9_-]{0,20}", self.invoice_prefix or ""):
            raise ValueError(
                "Invoice prefix may contain only letters, numbers, - and _"
            )
        number = f"{self.invoice_prefix}{self.invoice_next_number:04d}"
        self.invoice_next_number += 1
        return number

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "business_name": self.business_name,
            "business_number": self.business_number,
            "business_number_label": self.business_number_label,
            "tax_number": self.tax_number,
            "vat_id": self.vat_id,
            "owner_name": self.owner_name,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "address_line3": self.address_line3,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            "website": self.website,
            "logo_path": self.logo_path,
            "tax_type": self.tax_type,
            "tax_rate": str(self.tax_rate) if self.tax_rate else "0",
            "tax_label": self.tax_label,
            "tax_inclusive": self.tax_inclusive,
            "default_tax_treatment": self.default_tax_treatment,
            "default_invoice_template": self.default_invoice_template,
            "invoice_prefix": self.invoice_prefix,
            "invoice_next_number": self.invoice_next_number,
            "default_invoice_notes": self.default_invoice_notes,
            "default_email_message": self.default_email_message,
            "send_copy_to_self": self.send_copy_to_self,
            "locale": self.locale,
            "currency_code": self.currency_code,
            "currency_symbol": self.currency_symbol,
            "date_format": self.date_format,
            "tax_year_begins": self.tax_year_begins,
            "invoice_title": self.invoice_title,
            "quantity_label": self.quantity_label,
            "unit_cost_label": self.unit_cost_label,
            "show_quantity_unit_cost": self.show_quantity_unit_cost,
            "payment_instructions": self.payment_instructions,
            "payment_paypal": self.payment_paypal,
            "payment_other": self.payment_other,
        }

    def from_dict(self, data):
        fields = [
            "business_name",
            "business_number",
            "business_number_label",
            "tax_number",
            "vat_id",
            "owner_name",
            "address_line1",
            "address_line2",
            "address_line3",
            "email",
            "phone",
            "mobile",
            "website",
            "tax_type",
            "tax_label",
            "tax_inclusive",
            "default_tax_treatment",
            "default_invoice_template",
            "invoice_prefix",
            "invoice_next_number",
            "default_invoice_notes",
            "default_email_message",
            "send_copy_to_self",
            "locale",
            "currency_code",
            "currency_symbol",
            "date_format",
            "tax_year_begins",
            "invoice_title",
            "quantity_label",
            "unit_cost_label",
            "show_quantity_unit_cost",
            "payment_instructions",
            "payment_paypal",
            "payment_other",
        ]
        if "invoice_prefix" in data and not re.fullmatch(
            r"[A-Za-z0-9_-]{0,20}", data["invoice_prefix"] or ""
        ):
            raise ValueError(
                "Invoice prefix may contain only letters, numbers, - and _"
            )
        if "invoice_next_number" in data:
            try:
                data["invoice_next_number"] = int(data["invoice_next_number"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Next invoice number must be a positive integer"
                ) from exc
            if data["invoice_next_number"] < 1:
                raise ValueError("Next invoice number must be a positive integer")
        for f in fields:
            if f in data:
                setattr(self, f, data[f])
        if "tax_rate" in data:
            self.tax_rate = Decimal(str(data["tax_rate"]))
        return self


@dataclasses.dataclass
class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    address_line3 = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    fax = Column(String(50), nullable=True)
    vat_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    invoices = relationship("Invoice", back_populates="client", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "address_line3": self.address_line3,
            "phone": self.phone,
            "mobile": self.mobile,
            "fax": self.fax,
            "vat_id": self.vat_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_billed": str(self.total_billed),
            "invoice_count": len(self.invoices) if self.invoices else 0,
        }

    @property
    def total_billed(self):
        if not self.invoices:
            return Decimal("0")
        return sum(
            (inv.total or Decimal("0")) for inv in self.invoices if inv.status == "paid"
        )

    def from_dict(self, data):
        fields = [
            "name",
            "email",
            "address_line1",
            "address_line2",
            "address_line3",
            "phone",
            "mobile",
            "fax",
            "vat_id",
            "notes",
        ]
        for f in fields:
            if f in data:
                setattr(self, f, data[f])
        return self


@dataclasses.dataclass
class Invoice(Base):
    __tablename__ = "invoice"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("client.id"), nullable=True)
    invoice_number = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), default="draft")
    date = Column(Date, default=date.today)
    due_date = Column(Date, nullable=True)
    terms = Column(String(50), default="on_receipt")
    service_date_from = Column(Date, nullable=True)
    service_date_to = Column(Date, nullable=True)

    # totals
    subtotal = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    discount_type = Column(String(20), nullable=True)
    discount_value = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)
    amount_paid = Column(Numeric(12, 2), default=0)
    balance_due = Column(Numeric(12, 2), default=0)

    # currency snapshot
    currency_code = Column(String(3), default="USD")
    currency_symbol = Column(String(5), default="$")

    # tax snapshot
    tax_type = Column(String(50), default="on_total")
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_label = Column(String(50), default="VAT")
    tax_inclusive = Column(Boolean, default=False)
    tax_treatment = Column(String(30), default="standard")
    tax_exemption_reason = Column(Text, nullable=True)
    template_key = Column(String(30), default="precision")

    notes = Column(Text, nullable=True)
    share_token = Column(String(64), unique=True, nullable=True)
    share_token_expires_at = Column(DateTime, nullable=True)

    # business info snapshot
    from_name = Column(String(255), default="")
    from_email = Column(String(255), default="")
    from_address = Column(Text, default="")
    from_phone = Column(String(50), default="")
    from_business_number = Column(String(100), default="")
    from_tax_number = Column(String(100), default="")
    from_vat_id = Column(String(100), default="")
    client_vat_id = Column(String(100), default="")
    client_name_snapshot = Column(String(255), default="")
    client_email_snapshot = Column(String(255), default="")
    client_address_snapshot = Column(Text, default="")
    invoice_title_snapshot = Column(String(100), default="")
    payment_instructions_snapshot = Column(Text, default="")
    archived_pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    issued_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    client = relationship("Client", back_populates="invoices", lazy="selectin")
    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InvoiceItem.sort_order",
    )
    payments = relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Payment.payment_date.desc()",
    )

    def snapshot_business(self, settings):
        self.snapshot_supplier(settings)
        self.currency_code = settings.currency_code
        self.currency_symbol = settings.currency_symbol
        self.tax_type = settings.tax_type
        self.tax_rate = settings.tax_rate
        self.tax_label = settings.tax_label
        self.tax_inclusive = settings.tax_inclusive
        self.tax_treatment = settings.default_tax_treatment
        self.template_key = settings.default_invoice_template
        if self.client:
            self.client_vat_id = self.client.vat_id or ""

    def snapshot_supplier(self, settings):
        self.from_name = settings.business_name
        self.from_email = settings.email
        self.from_address = "\n".join(
            filter(
                None,
                [
                    settings.address_line1,
                    settings.address_line2,
                    settings.address_line3,
                ],
            )
        )
        self.from_phone = settings.phone
        self.from_business_number = settings.business_number
        self.from_tax_number = settings.tax_number
        self.from_vat_id = settings.vat_id

    @property
    def is_issued(self):
        return self.issued_at is not None

    def validate_for_issue(self):
        errors = []
        if not self.from_name or not self.from_address:
            errors.append("Your business name and address are required")
        if not self.from_tax_number and not self.from_vat_id:
            errors.append("Your Steuernummer or VAT ID is required")
        if not self.client or not self.client.name or not self.client.address_line1:
            errors.append("Customer name and address are required")
        if not self.items or any(not item.description for item in self.items):
            errors.append("Every line item needs a description")
        if not self.service_date_from:
            errors.append("Service date is required")
        elif self.service_date_to and self.service_date_to < self.service_date_from:
            errors.append("Service period end cannot precede its start")
        if self.tax_treatment == "reverse_charge":
            if not self.from_vat_id or not self.client_vat_id:
                errors.append(
                    "Reverse charge requires your business and customer VAT IDs"
                )
        elif self.tax_treatment == "exempt" and not self.tax_exemption_reason:
            errors.append("Tax exemption reason is required")
        elif self.tax_treatment not in ("standard", "reverse_charge", "exempt"):
            errors.append("Invalid tax treatment")
        if self.tax_treatment == "standard":
            if Decimal(str(self.tax_rate or 0)) < 0:
                errors.append("VAT rate cannot be negative")
            if self.tax_type == "none":
                errors.append("Standard VAT requires a tax calculation type")
        if self.template_key not in ("precision", "branded", "editorial"):
            errors.append("Invalid invoice template")
        return errors

    def recalculate(self):
        rate = Decimal(str(self.tax_rate or 0)) / Decimal("100")

        # subtotal from line items
        subtotal = Decimal("0")
        taxable_amount = Decimal("0")
        for item in self.items:
            item.amount = Decimal(str(item.quantity or 0)) * Decimal(
                str(item.unit_price or 0)
            )
            subtotal += item.amount
            if item.taxable:
                taxable_amount += item.amount

        self.subtotal = subtotal

        # discount
        discount = Decimal("0")
        if self.discount_type == "percentage" and self.discount_value:
            discount = subtotal * Decimal(str(self.discount_value)) / Decimal("100")
        elif self.discount_type == "fixed" and self.discount_value:
            discount = Decimal(str(self.discount_value))
        self.discount_amount = discount

        after_discount = subtotal - discount
        # scale taxable proportionally if discount applied
        if subtotal > 0 and discount > 0:
            taxable_amount = taxable_amount * after_discount / subtotal

        # tax
        if self.tax_treatment in ("reverse_charge", "exempt"):
            self.tax_amount = Decimal("0")
        elif self.tax_type == "none" or rate == 0:
            self.tax_amount = Decimal("0")
        elif self.tax_type == "per_line":
            if self.tax_inclusive:
                self.tax_amount = taxable_amount - (taxable_amount / (1 + rate))
            else:
                self.tax_amount = taxable_amount * rate
        else:  # on_total
            if self.tax_inclusive:
                self.tax_amount = after_discount - (after_discount / (1 + rate))
            else:
                self.tax_amount = after_discount * rate

        self.tax_amount = self.tax_amount.quantize(Decimal("0.01"))

        if self.tax_inclusive:
            self.total = after_discount
        else:
            self.total = after_discount + self.tax_amount

        # payments
        self.amount_paid = sum(Decimal(str(p.amount or 0)) for p in self.payments)
        self.balance_due = self.total - self.amount_paid

        # auto-status: only escalate, never override manual draft/cancelled
        if (
            self.amount_paid > 0
            and self.balance_due <= 0
            and self.status not in ("draft", "cancelled")
        ):
            self.status = "paid"
            if not self.paid_at:
                self.paid_at = datetime.now()

    def rotate_share_token(self, now=None, lifetime=timedelta(days=30)):
        now = now or datetime.now()
        self.share_token = secrets.token_urlsafe(32)
        self.share_token_expires_at = now + lifetime
        return self.share_token

    def ensure_share_token(self, now=None, lifetime=timedelta(days=30)):
        if not self.share_is_active(now):
            self.rotate_share_token(now, lifetime)
        return self.share_token

    def revoke_share_token(self):
        self.share_token = None
        self.share_token_expires_at = None

    def share_is_active(self, now=None):
        now = now or datetime.now()
        return bool(
            self.share_token
            and self.share_token_expires_at
            and now < self.share_token_expires_at
        )

    def _client_dict(self):
        c = self.client
        return {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "address_line1": c.address_line1,
            "address_line2": c.address_line2,
            "phone": c.phone,
        }

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "client": self._client_dict() if self.client else None,
            "invoice_number": self.invoice_number,
            "status": self.status,
            "date": self.date.isoformat() if self.date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "terms": self.terms,
            "service_date_from": self.service_date_from.isoformat()
            if self.service_date_from
            else None,
            "service_date_to": self.service_date_to.isoformat()
            if self.service_date_to
            else None,
            "subtotal": str(self.subtotal),
            "tax_amount": str(self.tax_amount),
            "discount_type": self.discount_type,
            "discount_value": str(self.discount_value) if self.discount_value else "0",
            "discount_amount": str(self.discount_amount),
            "total": str(self.total),
            "amount_paid": str(self.amount_paid),
            "balance_due": str(self.balance_due),
            "currency_code": self.currency_code,
            "currency_symbol": self.currency_symbol,
            "tax_type": self.tax_type,
            "tax_rate": str(self.tax_rate),
            "tax_label": self.tax_label,
            "tax_inclusive": self.tax_inclusive,
            "tax_treatment": self.tax_treatment,
            "tax_exemption_reason": self.tax_exemption_reason,
            "template_key": self.template_key,
            "notes": self.notes,
            "share_token": self.share_token,
            "share_token_expires_at": self.share_token_expires_at.isoformat()
            if self.share_token_expires_at
            else None,
            "from_name": self.from_name,
            "from_email": self.from_email,
            "from_address": self.from_address,
            "from_phone": self.from_phone,
            "from_business_number": self.from_business_number,
            "from_tax_number": self.from_tax_number,
            "from_vat_id": self.from_vat_id,
            "client_vat_id": self.client_vat_id,
            "client_name_snapshot": self.client_name_snapshot,
            "client_email_snapshot": self.client_email_snapshot,
            "client_address_snapshot": self.client_address_snapshot,
            "invoice_title_snapshot": self.invoice_title_snapshot,
            "payment_instructions_snapshot": self.payment_instructions_snapshot,
            "items": [item.to_dict() for item in self.items],
            "payments": [p.to_dict() for p in self.payments],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "cancelled_at": self.cancelled_at.isoformat()
            if self.cancelled_at
            else None,
        }

    def from_dict(self, data):
        simple_fields = [
            "client_id",
            "terms",
            "notes",
            "discount_type",
            "tax_type",
            "tax_label",
            "tax_inclusive",
            "currency_code",
            "currency_symbol",
            "from_name",
            "from_email",
            "from_address",
            "from_phone",
            "from_business_number",
            "from_tax_number",
            "from_vat_id",
            "client_vat_id",
            "tax_treatment",
            "tax_exemption_reason",
            "template_key",
        ]
        for f in simple_fields:
            if f in data:
                setattr(self, f, data[f])

        if data.get("invoice_number"):
            self.invoice_number = str(data["invoice_number"]).strip()
        if "date" in data and data["date"]:
            self.date = date.fromisoformat(data["date"])
        if "due_date" in data:
            self.due_date = (
                date.fromisoformat(data["due_date"]) if data["due_date"] else None
            )
        if "service_date_from" in data:
            self.service_date_from = (
                date.fromisoformat(data["service_date_from"])
                if data["service_date_from"]
                else None
            )
        if "service_date_to" in data:
            self.service_date_to = (
                date.fromisoformat(data["service_date_to"])
                if data["service_date_to"]
                else None
            )
        if "tax_rate" in data:
            self.tax_rate = Decimal(str(data["tax_rate"]))
        if "discount_value" in data:
            self.discount_value = Decimal(str(data["discount_value"]))
        return self


@dataclasses.dataclass
class InvoiceItem(Base):
    __tablename__ = "invoice_item"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(
        Integer, ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
    )
    description = Column(String(500), nullable=False, default="")
    detail = Column(Text, nullable=True)
    quantity = Column(Numeric(10, 2), default=1)
    unit_price = Column(Numeric(12, 2), default=0)
    amount = Column(Numeric(12, 2), default=0)
    taxable = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    invoice = relationship("Invoice", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "detail": self.detail,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount),
            "taxable": self.taxable,
            "sort_order": self.sort_order,
        }

    def from_dict(self, data):
        if "description" in data:
            self.description = data["description"]
        if "detail" in data:
            self.detail = data["detail"]
        if "quantity" in data:
            self.quantity = Decimal(str(data["quantity"]))
        if "unit_price" in data:
            self.unit_price = Decimal(str(data["unit_price"]))
        if "taxable" in data:
            self.taxable = data["taxable"]
        if "sort_order" in data:
            self.sort_order = data["sort_order"]
        return self


@dataclasses.dataclass
class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(
        Integer, ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
    )
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    payment_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.now)

    invoice = relationship("Invoice", back_populates="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "amount": str(self.amount),
            "method": self.method,
            "notes": self.notes,
            "payment_date": self.payment_date.isoformat()
            if self.payment_date
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def from_dict(self, data):
        if "amount" in data:
            self.amount = Decimal(str(data["amount"]))
        if "method" in data:
            self.method = data["method"]
        if "notes" in data:
            self.notes = data["notes"]
        if "payment_date" in data and data["payment_date"]:
            self.payment_date = date.fromisoformat(data["payment_date"])
        return self
