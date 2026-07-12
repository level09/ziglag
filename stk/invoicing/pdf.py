import asyncio
import os
from math import ceil

from quart import current_app

from stk.invoicing.presentation import TEMPLATES, service_period, tax_statement


def _unicode_font_path():
    candidates = [
        os.environ.get("INVOICE_FONT_PATH"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    raise RuntimeError(
        "No Unicode invoice font found. Set INVOICE_FONT_PATH to a Unicode TTF file."
    )


async def generate_invoice_pdf(invoice, settings):
    """Render invoice to PDF bytes using fpdf2. Pure Python, no system deps."""
    logo_path = None
    if settings.logo_path:
        candidate = os.path.join(current_app.static_folder, settings.logo_path)
        if os.path.exists(candidate):
            logo_path = candidate

    # Serialize ORM objects to dicts before passing to thread
    inv = {
        "from_name": invoice.from_name or "",
        "from_email": invoice.from_email or "",
        "from_address": invoice.from_address or "",
        "from_phone": invoice.from_phone or "",
        "from_business_number": invoice.from_business_number or "",
        "from_tax_number": invoice.from_tax_number or "",
        "from_vat_id": invoice.from_vat_id or "",
        "client_vat_id": invoice.client_vat_id or "",
        "invoice_number": invoice.invoice_number or "",
        "date": str(invoice.date) if invoice.date else "",
        "due_date": str(invoice.due_date) if invoice.due_date else "",
        "terms": invoice.terms or "",
        "currency_symbol": invoice.currency_symbol or "$",
        "subtotal": float(invoice.subtotal or 0),
        "tax_amount": float(invoice.tax_amount or 0),
        "tax_label": invoice.tax_label or "VAT",
        "tax_rate": float(invoice.tax_rate or 0),
        "discount_amount": float(invoice.discount_amount or 0),
        "total": float(invoice.total or 0),
        "amount_paid": float(invoice.amount_paid or 0),
        "balance_due": float(invoice.balance_due or 0),
        "notes": invoice.notes or "",
        "tax_treatment": invoice.tax_treatment or "standard",
        "tax_statement": tax_statement(invoice),
        "service_period": service_period(invoice),
        "template_key": invoice.template_key or "precision",
        "client": None,
        "items": [],
    }

    if invoice.client:
        inv["client"] = {
            "name": invoice.client_name_snapshot or invoice.client.name,
            "email": invoice.client_email_snapshot or invoice.client.email,
            "address_line1": invoice.client_address_snapshot
            or invoice.client.address_line1,
            "address_line2": ""
            if invoice.client_address_snapshot
            else invoice.client.address_line2,
            "address_line3": ""
            if invoice.client_address_snapshot
            else invoice.client.address_line3,
            "phone": invoice.client.phone,
        }

    for item in invoice.items:
        inv["items"].append(
            {
                "description": item.description or "",
                "detail": item.detail or "",
                "unit_price": float(item.unit_price or 0),
                "quantity": float(item.quantity or 0),
                "amount": float(item.amount or 0),
            }
        )

    stg = {
        "invoice_title": invoice.invoice_title_snapshot
        or settings.invoice_title
        or "Invoice",
        "unit_cost_label": settings.unit_cost_label or "Rate",
        "quantity_label": settings.quantity_label or "Qty",
        "payment_instructions": invoice.payment_instructions_snapshot
        or settings.payment_instructions
        or "",
    }

    def _render():
        return _build_pdf(inv, stg, logo_path)

    return await asyncio.to_thread(_render)


def _build_pdf(inv, stg, logo_path):
    from fpdf import FPDF

    pdf = FPDF()
    font_path = _unicode_font_path()
    pdf.add_font("InvoiceSans", style="", fname=font_path)
    pdf.add_font("InvoiceSans", style="B", fname=font_path)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Colors
    template = TEMPLATES.get(inv["template_key"], TEMPLATES["precision"])
    primary = template["primary"]
    dark = (27, 28, 28)
    muted = (70, 70, 83)
    light_bg = (246, 243, 242)
    pdf.set_fill_color(*template["paper"])
    pdf.rect(0, 0, 210, 297, "F")
    if inv["template_key"] == "branded":
        pdf.set_fill_color(*primary)
        pdf.rect(0, 0, 210, 72, "F")
    header_dark = (255, 255, 255) if inv["template_key"] == "branded" else dark
    header_muted = (255, 255, 255) if inv["template_key"] == "branded" else muted
    title_font = "InvoiceSans"

    sym = inv["currency_symbol"]

    # Header
    if logo_path:
        try:
            pdf.image(logo_path, x=10, y=10, h=15)
        except Exception:
            pass

    pdf.set_font("InvoiceSans", "B", 14)
    pdf.set_text_color(*header_dark)
    pdf.set_xy(10, 28)
    pdf.cell(100, 7, inv["from_name"], new_x="LMARGIN")

    pdf.set_font(title_font, "B", 24)
    pdf.set_text_color(*(header_dark if inv["template_key"] == "branded" else primary))
    pdf.set_xy(120, 10)
    pdf.cell(80, 12, stg["invoice_title"].upper(), align="R")

    pdf.set_font("InvoiceSans", "", 9)
    pdf.set_text_color(*header_muted)
    y = 24
    pdf.set_xy(120, y)
    pdf.cell(80, 5, inv["invoice_number"], align="R", new_x="LMARGIN", new_y="NEXT")
    y += 5
    pdf.set_xy(120, y)
    pdf.cell(80, 5, f"Date: {inv['date']}", align="R", new_x="LMARGIN", new_y="NEXT")
    if inv["due_date"]:
        y += 5
        pdf.set_xy(120, y)
        pdf.cell(
            80, 5, f"Due: {inv['due_date']}", align="R", new_x="LMARGIN", new_y="NEXT"
        )
    if inv["terms"]:
        y += 5
        pdf.set_xy(120, y)
        pdf.cell(
            80,
            5,
            f"Terms: {inv['terms'].replace('_', ' ').title()}",
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # Business address
    pdf.set_font("InvoiceSans", "", 9)
    pdf.set_text_color(*header_muted)
    pdf.set_xy(10, 36)
    if inv["from_address"]:
        for line in inv["from_address"].split("\n"):
            pdf.cell(100, 4.5, line.strip(), new_x="LMARGIN", new_y="NEXT")
    if inv["from_phone"]:
        pdf.cell(100, 4.5, inv["from_phone"], new_x="LMARGIN", new_y="NEXT")
    if inv["from_email"]:
        pdf.cell(100, 4.5, inv["from_email"], new_x="LMARGIN", new_y="NEXT")
    if inv["from_business_number"]:
        pdf.cell(100, 4.5, inv["from_business_number"], new_x="LMARGIN", new_y="NEXT")
    if inv["from_tax_number"]:
        pdf.cell(
            100,
            4.5,
            f"Steuernummer: {inv['from_tax_number']}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    if inv["from_vat_id"]:
        pdf.cell(
            100, 4.5, f"USt-IdNr.: {inv['from_vat_id']}", new_x="LMARGIN", new_y="NEXT"
        )

    # Accent line
    pdf.set_y(max(pdf.get_y(), 72 if inv["template_key"] == "branded" else 55) + 4)
    pdf.set_draw_color(*primary)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 6)

    # Bill To
    client = inv.get("client")
    if client:
        y_start = pdf.get_y()
        address_lines = []
        for value in (
            client.get("address_line1"),
            client.get("address_line2"),
            client.get("address_line3"),
        ):
            if value:
                address_lines.extend(line for line in str(value).splitlines() if line)
        detail_lines = address_lines + [
            value for value in (client.get("email"), client.get("phone")) if value
        ]
        if inv["client_vat_id"]:
            detail_lines.append(f"VAT ID: {inv['client_vat_id']}")
        box_height = max(28, 14 + len(detail_lines) * 4.5)
        pdf.set_fill_color(*light_bg)
        pdf.rect(10, y_start, 190, box_height, "F")

        pdf.set_xy(14, y_start + 3)
        pdf.set_font("InvoiceSans", "", 7)
        pdf.set_text_color(*muted)
        pdf.cell(40, 4, "BILL TO", new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(14, y_start + 8)
        pdf.set_font("InvoiceSans", "B", 11)
        pdf.set_text_color(*dark)
        pdf.cell(80, 5, client["name"] or "", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("InvoiceSans", "", 9)
        pdf.set_text_color(*muted)
        for detail in detail_lines:
            pdf.set_x(14)
            pdf.cell(170, 4.5, detail, new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(y_start + box_height + 4)

    # Line items table
    col_desc, col_rate, col_qty, col_amt = 90, 30, 25, 35
    row_h = 7

    pdf.set_font("InvoiceSans", "B", 7.5)
    pdf.set_text_color(*muted)
    pdf.set_xy(10, pdf.get_y())
    pdf.cell(col_desc, row_h, "DESCRIPTION")
    pdf.cell(col_rate, row_h, stg["unit_cost_label"].upper(), align="R")
    pdf.cell(col_qty, row_h, stg["quantity_label"].upper(), align="R")
    pdf.cell(col_amt, row_h, "AMOUNT", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(228, 226, 225)
    pdf.set_line_width(0.4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 2)

    pdf.set_font("InvoiceSans", "", 9)
    pdf.set_text_color(*dark)

    for item in inv["items"]:
        y = pdf.get_y()
        if y > 260:
            pdf.add_page()
            y = pdf.get_y()

        pdf.set_xy(10, y)
        pdf.cell(col_desc, row_h, str(item["description"])[:60])
        pdf.cell(col_rate, row_h, f"{sym}{item['unit_price']:.2f}", align="R")
        pdf.cell(col_qty, row_h, str(item["quantity"]), align="R")
        pdf.cell(
            col_amt,
            row_h,
            f"{sym}{item['amount']:.2f}",
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        if item["detail"]:
            pdf.set_font("InvoiceSans", "", 7.5)
            pdf.set_text_color(*muted)
            pdf.set_x(10)
            pdf.cell(
                col_desc, 5, str(item["detail"])[:80], new_x="LMARGIN", new_y="NEXT"
            )
            pdf.set_font("InvoiceSans", "", 9)
            pdf.set_text_color(*dark)

        pdf.set_draw_color(*light_bg)
        pdf.set_line_width(0.2)
        pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
        pdf.set_y(pdf.get_y() + 3)

    pdf.set_y(pdf.get_y() + 4)

    def wrapped_lines(value, width=95):
        if not value:
            return 0
        return sum(max(1, ceil(len(line) / width)) for line in value.splitlines())

    summary_rows = 2
    summary_rows += int(inv["discount_amount"] > 0)
    summary_rows += int(inv["tax_amount"] > 0)
    summary_rows += 2 if inv["amount_paid"] > 0 else 0
    required_height = summary_rows * 6 + 10
    required_height += 5 if inv["service_period"] else 0
    required_height += 12 + wrapped_lines(inv["notes"]) * 4 if inv["notes"] else 0
    required_height += (
        6 + wrapped_lines(inv["tax_statement"]) * 4 if inv["tax_statement"] else 0
    )
    required_height += (
        10 + wrapped_lines(stg["payment_instructions"]) * 4
        if stg["payment_instructions"]
        else 0
    )
    if pdf.get_y() + required_height > 267:
        pdf.add_page()

    if inv["service_period"]:
        pdf.set_font("InvoiceSans", "", 8)
        pdf.set_text_color(*muted)
        pdf.cell(
            0,
            5,
            f"Service date / period: {inv['service_period']}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # Summary
    def summary_line(label, value, bold=False):
        pdf.set_font("InvoiceSans", "B" if bold else "", 10 if bold else 9)
        pdf.set_x(130)
        pdf.cell(35, 6, label, align="R")
        pdf.cell(35, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(*dark)
    summary_line("Subtotal", f"{sym}{inv['subtotal']:.2f}")

    if inv["discount_amount"] > 0:
        summary_line("Discount", f"-{sym}{inv['discount_amount']:.2f}")

    if inv["tax_amount"] > 0:
        summary_line(
            f"{inv['tax_label']} ({inv['tax_rate']}%)", f"{sym}{inv['tax_amount']:.2f}"
        )

    pdf.set_draw_color(*primary)
    pdf.set_line_width(0.6)
    pdf.line(130, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_text_color(*primary)
    summary_line("Total", f"{sym}{inv['total']:.2f}", bold=True)

    if inv["amount_paid"] > 0:
        pdf.set_text_color(*dark)
        summary_line("Paid", f"-{sym}{inv['amount_paid']:.2f}")
        summary_line("Balance Due", f"{sym}{inv['balance_due']:.2f}", bold=True)

    # Notes
    if inv["notes"]:
        pdf.set_y(pdf.get_y() + 8)
        pdf.set_font("InvoiceSans", "B", 7)
        pdf.set_text_color(*muted)
        pdf.set_x(10)
        pdf.cell(40, 4, "NOTES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("InvoiceSans", "", 8.5)
        pdf.set_x(10)
        pdf.multi_cell(180, 4, inv["notes"], new_x="LMARGIN", new_y="NEXT")

    if inv["tax_statement"]:
        pdf.set_y(pdf.get_y() + 4)
        pdf.set_font("InvoiceSans", "B", 8)
        pdf.set_text_color(*dark)
        pdf.set_x(10)
        pdf.multi_cell(180, 4, inv["tax_statement"], new_x="LMARGIN", new_y="NEXT")

    # Payment instructions
    if stg["payment_instructions"]:
        pdf.set_y(pdf.get_y() + 4)
        pdf.set_font("InvoiceSans", "B", 7)
        pdf.set_text_color(*muted)
        pdf.set_x(10)
        pdf.cell(40, 4, "PAYMENT INSTRUCTIONS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("InvoiceSans", "", 8.5)
        pdf.set_x(10)
        pdf.multi_cell(
            180, 4, stg["payment_instructions"], new_x="LMARGIN", new_y="NEXT"
        )

    # Footer
    pdf.set_y(-25)
    pdf.set_font("InvoiceSans", "", 7)
    pdf.set_text_color(*muted)
    footer = inv["from_name"]
    if inv["from_email"]:
        footer += f"  |  {inv['from_email']}"
    pdf.cell(0, 5, footer, align="C")

    return pdf.output()
