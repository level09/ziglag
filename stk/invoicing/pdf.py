import asyncio
import os

from quart import current_app


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
        "client": None,
        "items": [],
    }

    if invoice.client:
        inv["client"] = {
            "name": invoice.client.name,
            "email": invoice.client.email,
            "address_line1": invoice.client.address_line1,
            "address_line2": invoice.client.address_line2,
            "address_line3": invoice.client.address_line3,
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
        "invoice_title": settings.invoice_title or "Invoice",
        "unit_cost_label": settings.unit_cost_label or "Rate",
        "quantity_label": settings.quantity_label or "Qty",
        "payment_instructions": settings.payment_instructions or "",
    }

    def _render():
        return _build_pdf(inv, stg, logo_path)

    return await asyncio.to_thread(_render)


def _build_pdf(inv, stg, logo_path):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Colors
    primary = (53, 58, 175)
    dark = (27, 28, 28)
    muted = (70, 70, 83)
    light_bg = (246, 243, 242)

    sym = inv["currency_symbol"]

    # Header
    if logo_path:
        try:
            pdf.image(logo_path, x=10, y=10, h=15)
        except Exception:
            pass

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*dark)
    pdf.set_xy(10, 28)
    pdf.cell(100, 7, inv["from_name"], new_x="LMARGIN")

    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*primary)
    pdf.set_xy(120, 10)
    pdf.cell(80, 12, stg["invoice_title"].upper(), align="R")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*muted)
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
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*muted)
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

    # Accent line
    pdf.set_y(max(pdf.get_y(), 55) + 4)
    pdf.set_draw_color(*primary)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 6)

    # Bill To
    client = inv.get("client")
    if client:
        y_start = pdf.get_y()
        pdf.set_fill_color(*light_bg)
        pdf.rect(10, y_start, 190, 28, "F")

        pdf.set_xy(14, y_start + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.cell(40, 4, "BILL TO", new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(14, y_start + 8)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*dark)
        pdf.cell(80, 5, client["name"] or "", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*muted)
        pdf.set_x(14)
        details = [
            v
            for v in [
                client.get("address_line1"),
                client.get("address_line2"),
                client.get("email"),
                client.get("phone"),
            ]
            if v
        ]
        pdf.cell(170, 4.5, " | ".join(details[:3]), new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(y_start + 32)

    # Line items table
    col_desc, col_rate, col_qty, col_amt = 90, 30, 25, 35
    row_h = 7

    pdf.set_font("Helvetica", "B", 7.5)
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

    pdf.set_font("Helvetica", "", 9)
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
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*muted)
            pdf.set_x(10)
            pdf.cell(
                col_desc, 5, str(item["detail"])[:80], new_x="LMARGIN", new_y="NEXT"
            )
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*dark)

        pdf.set_draw_color(*light_bg)
        pdf.set_line_width(0.2)
        pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
        pdf.set_y(pdf.get_y() + 3)

    pdf.set_y(pdf.get_y() + 4)

    # Summary
    def summary_line(label, value, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 10 if bold else 9)
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
        pdf.set_y(pdf.get_y() + 10)
        pdf.set_fill_color(*light_bg)
        y_start = pdf.get_y()
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.set_xy(14, y_start + 3)
        pdf.cell(40, 4, "NOTES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_x(14)
        pdf.multi_cell(175, 4.5, inv["notes"], new_x="LMARGIN", new_y="NEXT")
        box_h = pdf.get_y() - y_start + 4
        pdf.rect(10, y_start, 190, box_h, "F")
        pdf.set_xy(14, y_start + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.cell(40, 4, "NOTES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_x(14)
        pdf.multi_cell(175, 4.5, inv["notes"], new_x="LMARGIN", new_y="NEXT")

    # Payment instructions
    if stg["payment_instructions"]:
        pdf.set_y(pdf.get_y() + 6)
        y_start = pdf.get_y()
        pdf.set_fill_color(*light_bg)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.set_xy(14, y_start + 3)
        pdf.cell(40, 4, "PAYMENT INSTRUCTIONS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_x(14)
        pdf.multi_cell(
            175, 4.5, stg["payment_instructions"], new_x="LMARGIN", new_y="NEXT"
        )
        box_h = pdf.get_y() - y_start + 4
        pdf.rect(10, y_start, 190, box_h, "F")
        pdf.set_xy(14, y_start + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.cell(40, 4, "PAYMENT INSTRUCTIONS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_x(14)
        pdf.multi_cell(
            175, 4.5, stg["payment_instructions"], new_x="LMARGIN", new_y="NEXT"
        )

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*muted)
    footer = inv["from_name"]
    if inv["from_email"]:
        footer += f"  |  {inv['from_email']}"
    pdf.cell(0, 5, footer, align="C")

    return pdf.output()
