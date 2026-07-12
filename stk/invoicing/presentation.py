TEMPLATES = {
    "precision": {
        "name": "Precision",
        "primary": (37, 33, 30),
        "paper": (255, 255, 255),
    },
    "branded": {"name": "Branded", "primary": (168, 50, 0), "paper": (255, 255, 255)},
    "editorial": {
        "name": "Editorial",
        "primary": (168, 50, 0),
        "paper": (255, 248, 243),
    },
}


def tax_statement(invoice):
    if invoice.tax_treatment == "reverse_charge":
        return "Reverse charge: VAT to be accounted for by the recipient (Art. 196 EU VAT Directive 2006/112/EC)."
    if invoice.tax_treatment == "exempt":
        return invoice.tax_exemption_reason or ""
    return ""


def service_period(invoice):
    if not invoice.service_date_from:
        return ""
    if invoice.service_date_to and invoice.service_date_to != invoice.service_date_from:
        return f"{invoice.service_date_from} to {invoice.service_date_to}"
    return str(invoice.service_date_from)
