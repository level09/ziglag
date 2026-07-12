import re
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from stk.invoicing.models import Client, Invoice, InvoiceItem
from stk.invoicing.pdf import _build_pdf
from stk.invoicing.presentation import TEMPLATES, tax_statement
from stk.invoicing.views import invoice_archive_path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def valid_invoice(treatment="standard"):
    invoice = Invoice(
        user_id=1,
        invoice_number="TEST0001",
        from_name="Example Studio",
        from_address="Example Street 1\n10115 Berlin",
        from_tax_number="12/345/67890",
        from_vat_id="DE123456789",
        client_vat_id="PL1234567890",
        service_date_from=date(2026, 7, 1),
        service_date_to=date(2026, 7, 31),
        tax_treatment=treatment,
        template_key="precision",
        tax_rate=Decimal("19"),
    )
    invoice.client = Client(
        user_id=1, name="Example Client", address_line1="Client Street 2"
    )
    invoice.items = [
        InvoiceItem(description="Software development", quantity=1, unit_price=100)
    ]
    return invoice


class InvoiceValidationTests(unittest.TestCase):
    def test_archive_path_never_uses_invoice_number(self):
        archive_dir, archive_path = invoice_archive_path("/srv/app", 7, 42)
        self.assertEqual(archive_dir, "/srv/app/invoices/7/42")
        self.assertEqual(archive_path, "/srv/app/invoices/7/42/invoice-42.pdf")

    def test_standard_invoice_is_valid(self):
        self.assertEqual(valid_invoice().validate_for_issue(), [])

    def test_reverse_charge_requires_both_vat_ids(self):
        invoice = valid_invoice("reverse_charge")
        invoice.client_vat_id = ""
        self.assertIn(
            "Reverse charge requires supplier and client VAT IDs",
            invoice.validate_for_issue(),
        )

    def test_exempt_invoice_requires_reason(self):
        invoice = valid_invoice("exempt")
        self.assertIn("Tax exemption reason is required", invoice.validate_for_issue())

    def test_reverse_charge_has_standard_wording(self):
        invoice = valid_invoice("reverse_charge")
        self.assertIn("Art. 196", tax_statement(invoice))

    def test_templates_are_stable(self):
        self.assertEqual(set(TEMPLATES), {"precision", "branded", "editorial"})


class PdfTests(unittest.TestCase):
    def test_representative_invoice_stays_on_one_page(self):
        inv = {
            "from_name": "Example Studio",
            "from_email": "billing@example.test",
            "from_address": "Example Street 1\n10115 Berlin",
            "from_phone": "",
            "from_business_number": "",
            "from_tax_number": "12/345/67890",
            "from_vat_id": "DE123456789",
            "client_vat_id": "DE987654321",
            "invoice_number": "TEST0001",
            "date": "2026-07-31",
            "due_date": "2026-07-31",
            "terms": "on_receipt",
            "currency_symbol": "€",
            "subtotal": 6240,
            "tax_amount": 1185.6,
            "tax_label": "VAT",
            "tax_rate": 19,
            "discount_amount": 0,
            "total": 7425.6,
            "amount_paid": 0,
            "balance_due": 7425.6,
            "notes": "",
            "tax_treatment": "standard",
            "tax_statement": "",
            "service_period": "2026-07-01 to 2026-07-31",
            "template_key": "editorial",
            "client": {
                "name": "Łódź Example Sp. z o.o.",
                "email": "client@example.test",
                "address_line1": "Client Street 2",
                "address_line2": "10117 Berlin",
                "address_line3": "",
                "phone": "",
            },
            "items": [
                {
                    "description": "Software development",
                    "detail": "Service period: July 2026",
                    "unit_price": 52,
                    "quantity": 120,
                    "amount": 6240,
                }
            ],
        }
        settings = {
            "invoice_title": "Invoice",
            "unit_cost_label": "Rate",
            "quantity_label": "Qty",
            "payment_instructions": "IBAN: DE00 0000 0000 0000 0000 00",
        }
        rendered = []
        for template_key in TEMPLATES:
            with self.subTest(template_key=template_key):
                inv["template_key"] = template_key
                pdf = bytes(_build_pdf(inv, settings, None))
                rendered.append(pdf)
                self.assertEqual(len(re.findall(rb"/Type /Page\b", pdf)), 1)
        self.assertEqual(len(set(rendered)), 3)


class ProductionConfigTests(unittest.TestCase):
    def test_installers_generate_totp_secret(self):
        for filename in ("setup.sh", "deploy.sh"):
            with self.subTest(filename=filename):
                content = (PROJECT_ROOT / filename).read_text()
                self.assertIn("SECURITY_TOTP_SECRETS", content)

    def test_deploy_installs_invoice_font(self):
        content = (PROJECT_ROOT / "deploy.sh").read_text()
        self.assertIn("fonts-dejavu-core", content)

    def test_compose_persists_invoice_archive(self):
        content = (PROJECT_ROOT / "docker-compose.yml").read_text()
        self.assertIn("invoice-data:/app/instance", content)
        self.assertIn("invoice-data:", content)


if __name__ == "__main__":
    unittest.main()
