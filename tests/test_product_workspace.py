import tempfile
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiosmtplib.errors import SMTPResponseException, SMTPServerDisconnected
from quart_security import hash_password

import stk.extensions as ext
from stk.agent_login import create_agent_login_token
from stk.app import create_app
from stk.invoicing.models import BusinessSettings, Client, Invoice
from stk.user.models import User
from tests.test_agent_operability import AgentLoginTestingConfig


class WorkspaceConfig(AgentLoginTestingConfig):
    WTF_CSRF_ENABLED = False


class ProductWorkspaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = create_app(WorkspaceConfig)
        self.app.instance_path = self.directory.name
        async with ext.engine.begin() as conn:
            await conn.run_sync(ext.Base.metadata.create_all)
        self.today = date.today()
        async with ext.async_session_factory() as session:
            users = [
                User(
                    email=email,
                    name="Studio",
                    active=True,
                    confirmed_at=datetime.now(),
                    password=hash_password("TestPassword123!"),
                )
                for email in ["owner@example.com", "other@example.com"]
            ]
            session.add_all(users)
            await session.flush()
            self.uid, self.other = [user.id for user in users]
            customer = Client(
                user_id=self.uid,
                name="A & B 100%_Studio",
                email="customer@example.test",
            )
            session.add_all(
                [
                    customer,
                    BusinessSettings(
                        user_id=self.uid, currency_code="EUR", currency_symbol="€"
                    ),
                ]
            )
            await session.flush()
            self.ids = {}
            for name, status, total, balance, currency, due, owner in [
                ("DRAFT", "draft", "100", "100", "EUR", -1, self.uid),
                ("UNPAID", "sent", "200", "200", "EUR", -1, self.uid),
                ("PARTIAL", "sent", "300", "250", "EUR", 1, self.uid),
                ("PAID", "paid", "400", "0", "EUR", -1, self.uid),
                ("CANCELLED", "cancelled", "500", "500", "EUR", -1, self.uid),
                ("USD", "sent", "600", "600", "USD", 1, self.uid),
                ("OTHER", "sent", "900", "900", "EUR", -1, self.other),
                ("TODAY", "sent", "10", "10", "EUR", 0, self.uid),
                ("UNDATED", "sent", "20", "20", "EUR", None, self.uid),
            ]:
                inv = Invoice(
                    user_id=owner,
                    invoice_number=name,
                    status=status,
                    issued_at=None if status == "draft" else datetime.now(),
                    date=self.today,
                    due_date=self.today + timedelta(days=due)
                    if due is not None
                    else None,
                    total=Decimal(total),
                    balance_due=Decimal(balance),
                    currency_code=currency,
                    client_id=customer.id
                    if owner == self.uid and status != "draft"
                    else None,
                    client_name_snapshot="Archived customer",
                    from_name="Studio",
                )
                session.add(inv)
                await session.flush()
                self.ids[name] = inv.id
                archive = (
                    Path("invoices")
                    / str(owner)
                    / str(inv.id)
                    / f"invoice-{inv.id}.pdf"
                )
                target = Path(self.directory.name) / archive
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"%PDF-test-archive")
                inv.archived_pdf_path = str(archive)
            await session.commit()
        self.client = self.app.test_client()
        async with self.app.app_context():
            token = create_agent_login_token("owner@example.com", "/dashboard/")
        response = await self.client.get("/_test/login", query_string={"token": token})
        self.assertEqual(response.status_code, 302)

    async def asyncTearDown(self):
        await ext.engine.dispose()
        self.directory.cleanup()

    async def listing(self, **params):
        response = await self.client.get("/api/invoices", query_string=params)
        self.assertEqual(response.status_code, 200)
        return await response.get_json()

    async def test_filters_exclude_drafts_cancelled_and_other_users(self):
        expected = {
            "draft": ["DRAFT"],
            "overdue": ["UNPAID"],
            "paid": ["PAID"],
            "outstanding": ["UNPAID", "PARTIAL", "USD", "TODAY", "UNDATED"],
        }
        for status, numbers in expected.items():
            with self.subTest(status=status):
                result = await self.listing(status=status)
                self.assertCountEqual(
                    [x["invoice_number"] for x in result["items"]], numbers
                )
                self.assertEqual(result["total"], len(numbers))
        response = await self.client.get("/api/invoices?status=invalid")
        self.assertEqual(response.status_code, 400)

    async def test_dashboard_groups_balances_by_currency(self):
        captured = {}

        async def render(template, **context):
            captured.update(context)
            return "ok"

        with patch("stk.portal.views.render_template", side_effect=render):
            response = await self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        stats = captured["stats"]
        self.assertEqual(stats["draft_count"], 1)
        self.assertEqual(stats["overdue_count"], 1)
        self.assertEqual(
            {r["currency_code"]: r["amount"] for r in stats["outstanding_by_currency"]},
            {"EUR": "480.00", "USD": "600.00"},
        )

    async def test_search_number_without_customer_and_literal_wildcards(self):
        self.assertEqual((await self.listing(search="DRAFT"))["total"], 1)
        self.assertEqual((await self.listing(search="Archived customer"))["total"], 7)
        self.assertEqual((await self.listing(search="%_"))["total"], 0)
        self.assertEqual((await self.listing(search="OTHER"))["total"], 0)

    async def test_reports_group_currency_and_use_decimal_totals(self):
        async with ext.async_session_factory() as session:
            paid = await session.get(Invoice, self.ids["PAID"])
            paid.total = Decimal("0.10")
            session.add_all(
                [
                    Invoice(
                        user_id=self.uid,
                        invoice_number="SMALL",
                        status="paid",
                        issued_at=datetime.now(),
                        total=Decimal("0.20"),
                        balance_due=0,
                        currency_code="EUR",
                        date=self.today,
                    ),
                    Invoice(
                        user_id=self.uid,
                        invoice_number="USD-PAID",
                        status="paid",
                        issued_at=datetime.now(),
                        total=Decimal("9"),
                        balance_due=0,
                        currency_code="USD",
                        date=self.today,
                    ),
                ]
            )
            await session.commit()
        response = await self.client.get(
            "/api/reports/monthly",
            query_string={"year": self.today.year, "currency": "EUR"},
        )
        data = await response.get_json()
        self.assertEqual(data["yearly_total"], "0.30")
        self.assertEqual(data["currency_code"], "EUR")
        self.assertEqual(data["currencies"], ["EUR", "USD"])
        self.assertEqual(data["yearly_invoices"], 2)

    async def test_overpayment_stays_in_paid_list_and_report(self):
        async with ext.async_session_factory() as session:
            invoice = await session.get(Invoice, self.ids["PAID"])
            invoice.balance_due = Decimal("-10.00")
            await session.commit()
        result = await self.listing(status="paid")
        self.assertEqual([row["invoice_number"] for row in result["items"]], ["PAID"])
        response = await self.client.get(
            "/api/reports/monthly", query_string={"year": self.today.year}
        )
        self.assertEqual((await response.get_json())["yearly_total"], "400.00")

    async def test_report_uses_invoice_date_not_payment_date(self):
        async with ext.async_session_factory() as session:
            invoice = await session.get(Invoice, self.ids["PAID"])
            invoice.date = date(self.today.year - 1, 12, 31)
            invoice.paid_at = datetime(self.today.year, 1, 2)
            await session.commit()
        response = await self.client.get(
            "/api/reports/monthly", query_string={"year": self.today.year - 1}
        )
        report = await response.get_json()
        self.assertEqual(report["months"][11]["total"], "400.00")
        response = await self.client.get(
            "/api/reports/monthly", query_string={"year": self.today.year}
        )
        empty = await response.get_json()
        self.assertEqual(empty["yearly_total"], "0.00")
        self.assertEqual(empty["currency_code"], "EUR")

    async def test_search_escapes_literal_customer_characters(self):
        async with ext.async_session_factory() as session:
            draft = await session.get(Invoice, self.ids["DRAFT"])
            issued = await session.get(Invoice, self.ids["UNPAID"])
            draft.client_id = issued.client_id
            await session.commit()
        for search in ["A & B", "%_"]:
            result = await self.listing(search=search)
            self.assertEqual(
                [row["invoice_number"] for row in result["items"]], ["DRAFT"]
            )

    async def test_send_waits_for_smtp_and_preserves_paid_status(self):
        with patch("aiosmtplib.send", new_callable=AsyncMock) as send:
            response = await self.client.post(f"/api/invoice/{self.ids['PAID']}/send")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                (await response.get_json())["message"],
                "Email accepted by the mail server",
            )
            send.assert_awaited_once()
        async with ext.async_session_factory() as session:
            invoice = await session.get(Invoice, self.ids["PAID"])
            self.assertEqual(invoice.status, "paid")
            self.assertEqual(
                (Path(self.directory.name) / invoice.archived_pdf_path).read_bytes(),
                b"%PDF-test-archive",
            )

    async def test_send_rejection_and_timeout_are_not_success(self):
        for error, code in [
            (SMTPResponseException(550, "private server detail"), 502),
            (TimeoutError(), 504),
            (SMTPServerDisconnected("connection lost"), 504),
        ]:
            with (
                self.subTest(error=error),
                patch("aiosmtplib.send", new_callable=AsyncMock, side_effect=error),
            ):
                response = await self.client.post(
                    f"/api/invoice/{self.ids['UNPAID']}/send"
                )
                self.assertEqual(response.status_code, code)
                self.assertNotIn(
                    "private server detail", (await response.get_json())["message"]
                )

    async def test_send_rejects_wrong_owner_and_cancelled_invoice(self):
        for key, code in [("OTHER", 404), ("CANCELLED", 409)]:
            response = await self.client.post(f"/api/invoice/{self.ids[key]}/send")
            self.assertEqual(response.status_code, code)
