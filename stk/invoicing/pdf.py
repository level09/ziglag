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

    def _render():
        return _build_pdf(invoice, settings, logo_path)

    return await asyncio.to_thread(_render)


def _build_pdf(invoice, settings, logo_path):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Colors
    primary = (53, 58, 175)  # #353aaf
    dark = (27, 28, 28)  # #1b1c1c
    muted = (70, 70, 83)  # #464653
    light_bg = (246, 243, 242)  # #f6f3f2
    border_color = (228, 226, 225)  # #e4e2e1

    # ── Header ──
    if logo_path:
        try:
            pdf.image(logo_path, x=10, y=10, h=15)
        except Exception:
            pass

    # Business name (left)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*dark)
    pdf.set_xy(10, 28)
    pdf.cell(100, 7, invoice.from_name or "", new_x="LMARGIN")

    # Invoice title (right)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*primary)
    pdf.set_xy(120, 10)
    pdf.cell(80, 12, (settings.invoice_title or "Invoice").upper(), align="R")

    # Invoice meta (right)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*muted)
    pdf.set_xy(120, 24)
    pdf.cell(80, 5, invoice.invoice_number, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(120, 29)
    pdf.cell(80, 5, f"Date: {invoice.date}", align="R", new_x="LMARGIN", new_y="NEXT")
    if invoice.due_date:
        pdf.set_xy(120, 34)
        pdf.cell(
            80, 5, f"Due: {invoice.due_date}", align="R", new_x="LMARGIN", new_y="NEXT"
        )
    if invoice.terms:
        y = 34 if not invoice.due_date else 39
        pdf.set_xy(120, y)
        label = invoice.terms.replace("_", " ").title()
        pdf.cell(80, 5, f"Terms: {label}", align="R", new_x="LMARGIN", new_y="NEXT")

    # Business address (left, below name)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*muted)
    pdf.set_xy(10, 36)
    if invoice.from_address:
        for line in invoice.from_address.split("\n"):
            pdf.cell(100, 4.5, line.strip(), new_x="LMARGIN", new_y="NEXT")
    if invoice.from_phone:
        pdf.cell(100, 4.5, invoice.from_phone, new_x="LMARGIN", new_y="NEXT")
    if invoice.from_email:
        pdf.cell(100, 4.5, invoice.from_email, new_x="LMARGIN", new_y="NEXT")
    if invoice.from_business_number:
        pdf.cell(100, 4.5, invoice.from_business_number, new_x="LMARGIN", new_y="NEXT")

    # Accent line
    pdf.set_y(max(pdf.get_y(), 55) + 4)
    pdf.set_draw_color(*primary)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 6)

    # ── Bill To ──
    if invoice.client:
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
        pdf.cell(80, 5, invoice.client.name, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*muted)
        pdf.set_x(14)
        details = []
        for attr in ["address_line1", "address_line2", "address_line3"]:
            v = getattr(invoice.client, attr, None)
            if v:
                details.append(v)
        if invoice.client.email:
            details.append(invoice.client.email)
        if invoice.client.phone:
            details.append(invoice.client.phone)
        pdf.cell(170, 4.5, " | ".join(details[:3]), new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(y_start + 32)

    # ── Line Items Table ──
    col_desc = 90
    col_rate = 30
    col_qty = 25
    col_amt = 35
    row_h = 7

    # Header row
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*muted)
    y = pdf.get_y()
    pdf.set_xy(10, y)
    pdf.cell(col_desc, row_h, "DESCRIPTION")
    pdf.cell(col_rate, row_h, settings.unit_cost_label or "RATE", align="R")
    pdf.cell(col_qty, row_h, settings.quantity_label or "QTY", align="R")
    pdf.cell(col_amt, row_h, "AMOUNT", align="R", new_x="LMARGIN", new_y="NEXT")

    # Header underline
    pdf.set_draw_color(*border_color)
    pdf.set_line_width(0.4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 2)

    # Items
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*dark)
    sym = invoice.currency_symbol or ""

    for item in invoice.items:
        y = pdf.get_y()
        if y > 260:
            pdf.add_page()
            y = pdf.get_y()

        pdf.set_xy(10, y)
        pdf.cell(col_desc, row_h, str(item.description or "")[:60])
        pdf.cell(col_rate, row_h, f"{sym}{float(item.unit_price or 0):.2f}", align="R")
        pdf.cell(col_qty, row_h, str(item.quantity or 0), align="R")
        pdf.cell(
            col_amt,
            row_h,
            f"{sym}{float(item.amount or 0):.2f}",
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        if item.detail:
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*muted)
            pdf.set_x(10)
            pdf.cell(col_desc, 5, str(item.detail)[:80], new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*dark)

        # Light separator
        pdf.set_draw_color(*light_bg)
        pdf.set_line_width(0.2)
        pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
        pdf.set_y(pdf.get_y() + 3)

    pdf.set_y(pdf.get_y() + 4)

    # ── Summary ──
    def summary_line(label, value, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 10 if bold else 9)
        pdf.set_x(130)
        pdf.cell(35, 6, label, align="R")
        pdf.cell(35, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(*dark)
    summary_line("Subtotal", f"{sym}{float(invoice.subtotal or 0):.2f}")

    if invoice.discount_amount and float(invoice.discount_amount) > 0:
        summary_line("Discount", f"-{sym}{float(invoice.discount_amount):.2f}")

    if invoice.tax_amount and float(invoice.tax_amount) > 0:
        summary_line(
            f"{invoice.tax_label} ({invoice.tax_rate}%)",
            f"{sym}{float(invoice.tax_amount):.2f}",
        )

    # Total line with accent
    pdf.set_draw_color(*primary)
    pdf.set_line_width(0.6)
    pdf.line(130, pdf.get_y(), 200, pdf.get_y())
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_text_color(*primary)
    summary_line("Total", f"{sym}{float(invoice.total or 0):.2f}", bold=True)

    if invoice.amount_paid and float(invoice.amount_paid) > 0:
        pdf.set_text_color(*dark)
        summary_line("Paid", f"-{sym}{float(invoice.amount_paid):.2f}")
        summary_line(
            "Balance Due",
            f"{sym}{float(invoice.balance_due or 0):.2f}",
            bold=True,
        )

    # ── Notes ──
    if invoice.notes:
        pdf.set_y(pdf.get_y() + 10)
        y_start = pdf.get_y()
        pdf.set_fill_color(*light_bg)

        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.set_xy(14, y_start + 3)
        pdf.cell(40, 4, "NOTES", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*muted)
        pdf.set_x(14)
        pdf.multi_cell(175, 4.5, invoice.notes, new_x="LMARGIN", new_y="NEXT")
        box_h = pdf.get_y() - y_start + 4
        # Draw background behind text (draw after to know height)
        pdf.set_fill_color(*light_bg)
        pdf.rect(10, y_start, 190, box_h, "F")
        # Re-render text on top of background
        pdf.set_xy(14, y_start + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.cell(40, 4, "NOTES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_x(14)
        pdf.multi_cell(175, 4.5, invoice.notes, new_x="LMARGIN", new_y="NEXT")

    # ── Payment Instructions ──
    if settings.payment_instructions:
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
            175, 4.5, settings.payment_instructions, new_x="LMARGIN", new_y="NEXT"
        )
        box_h = pdf.get_y() - y_start + 4
        pdf.set_fill_color(*light_bg)
        pdf.rect(10, y_start, 190, box_h, "F")
        pdf.set_xy(14, y_start + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*muted)
        pdf.cell(40, 4, "PAYMENT INSTRUCTIONS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_x(14)
        pdf.multi_cell(
            175, 4.5, settings.payment_instructions, new_x="LMARGIN", new_y="NEXT"
        )

    # ── Footer ──
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*muted)
    footer = invoice.from_name or ""
    if invoice.from_email:
        footer += f"  |  {invoice.from_email}"
    pdf.cell(0, 5, footer, align="C")

    return pdf.output()
