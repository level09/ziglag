"""Run with `uv run python -m tests.browser_invoice_editor` (requires Chromium)."""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright, expect

from stk.commands import (
    _create_smoke_token,
    _free_localhost_port,
    _run_smoke_setup,
    _smoke_env,
    _wait_for_smoke_server,
)


async def exercise(base_url, token):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1200})
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(f"{base_url}/_test/login?token={token}")
        await page.evaluate("""async () => {
            await axios.post('/api/settings', {
                business_name: 'North Studio', address_line1: 'Example Street 12',
                address_line2: '10115 Berlin', tax_number: '12/345/67890',
                email: 'hello@example.test', currency_code: 'EUR', currency_symbol: '€',
                tax_type: 'on_total', tax_rate: 19, locale: 'en-IE'
            });
            await axios.post('/api/client/', {item: {
                name: 'Acme Studio', address_line1: 'Customer Street 2',
                address_line2: '10117 Berlin', email: 'accounts@example.test'
            }});
        }""")
        await page.goto(f"{base_url}/invoices/new")
        await expect(
            page.get_by_role("heading", name="Invoice", exact=True)
        ).to_be_visible()
        await page.get_by_label("Customer", exact=True).fill("Acme")
        await page.get_by_role("option", name="Acme Studio").click()
        await page.get_by_label("Description 1", exact=True).fill("September support")
        await page.get_by_label("Rate 1", exact=True).fill("95")
        await page.get_by_label("Qty 1", exact=True).fill("12")
        try:
            await expect(page.locator(".save-status")).to_have_text("Saved")
        except AssertionError:
            print(await page.locator(".invoice-workspace").inner_text())
            raise
        assert "/invoices/new" not in page.url
        invoice_url = page.url
        invoice_id = invoice_url.rsplit("/", 1)[1]
        saved = await page.evaluate(
            f"async () => (await axios.get('/api/invoice/{invoice_id}')).data"
        )
        assert saved["total"] == "1356.60", saved
        assert saved["client"]["name"] == "Acme Studio"

        # Keep typing while the prior snapshot is still in flight.
        started, release = asyncio.Event(), asyncio.Event()

        async def slow_save(route):
            if route.request.method == "POST":
                started.set()
                await release.wait()
            await route.continue_()

        save_url = f"**/api/invoice/{invoice_id}"
        await page.route(save_url, slow_save)
        await page.get_by_label("Description 1", exact=True).fill("First edit")
        await asyncio.wait_for(started.wait(), timeout=10)
        await page.get_by_label("Description 1", exact=True).fill("Latest edit")
        release.set()
        await expect(page.locator(".save-status")).to_have_text("Saved")
        await page.unroute(save_url, slow_save)
        await page.reload()
        await expect(page.get_by_label("Description 1", exact=True)).to_have_value(
            "Latest edit"
        )

        # A failed write keeps edits visible and protects navigation until retry.
        async def fail_save(route):
            if route.request.method == "POST":
                await route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({"message": "Test save failure"}),
                )
            else:
                await route.continue_()

        await page.route(save_url, fail_save)
        await page.get_by_label("Notes to customer").fill(
            "Thank you for your business."
        )
        await expect(
            page.get_by_role("alert").filter(has_text="Test save failure")
        ).to_be_visible()
        assert await page.evaluate("""() => {
            const event = new Event('beforeunload', {cancelable: true});
            window.dispatchEvent(event); return event.defaultPrevented;
        }""")
        await page.unroute(save_url, fail_save)
        await page.get_by_role("button", name="Retry save").click()
        await expect(page.locator(".save-status")).to_have_text("Saved")

        # Clearing a required date must reach the server, not leave a stale value.
        await page.get_by_label("Service from", exact=True).fill("")
        await page.get_by_role("button", name="Review and issue").click()
        await expect(page.get_by_text("Service date is required").first).to_be_visible()
        await expect(page.get_by_role("dialog")).not_to_be_visible()
        await page.get_by_label("Service from", exact=True).fill("2026-09-01")
        await page.get_by_label("Service to (optional)").fill("2026-09-30")
        await page.get_by_label("Invoice date", exact=True).fill("2026-09-30")
        await page.get_by_label("Due date", exact=True).fill("2026-10-14")
        await expect(page.locator(".save-status")).to_have_text("Saved")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.screenshot(
            path="/tmp/ziglag-invoice-editor-desktop.png", full_page=True
        )
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_function(
            "parseFloat(getComputedStyle(document.querySelector('.v-main')).paddingLeft) === 0"
        )
        await page.evaluate("window.scrollTo(0, 0)")
        await page.screenshot(
            path="/tmp/ziglag-invoice-editor-mobile.png", full_page=True
        )
        assert await page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        await page.set_viewport_size({"width": 1440, "height": 1200})

        # Review must not issue. Only the separate confirmation locks the invoice.
        await page.get_by_role("button", name="Review and issue").click()
        await expect(page.get_by_role("dialog")).to_be_visible()
        saved = await page.evaluate(
            f"async () => (await axios.get('/api/invoice/{invoice_id}')).data"
        )
        assert saved["issued_at"] is None
        await page.get_by_role("button", name="Issue invoice", exact=True).click()
        await expect(page.get_by_role("dialog")).not_to_be_visible()
        await expect(page.get_by_label("Description 1", exact=True)).not_to_be_visible()
        await expect(page.get_by_role("button", name="Record Payment")).to_be_visible()
        saved = await page.evaluate(
            f"async () => (await axios.get('/api/invoice/{invoice_id}')).data"
        )
        assert saved["issued_at"]
        response = await page.request.get(f"{base_url}/api/invoice/{invoice_id}/pdf")
        assert response.status == 200
        assert (await response.body()).startswith(b"%PDF")

        # A new customer is created only by an explicit selection, not search text.
        await page.goto(f"{base_url}/invoices/new")
        await page.get_by_label("Customer", exact=True).fill("New Studio")
        await page.get_by_role("button", name='Create customer "New Studio"').press(
            "Enter"
        )
        await page.get_by_label("Address", exact=True).fill("New Street 5")
        await page.get_by_label("Description 1", exact=True).fill("Consulting")
        await page.get_by_label("Rate 1", exact=True).fill("100")
        await expect(page.locator(".save-status")).to_have_text("Saved")
        second_id = page.url.rsplit("/", 1)[1]
        saved = await page.evaluate(
            f"async () => (await axios.get('/api/invoice/{second_id}')).data"
        )
        assert saved["client"]["name"] == "New Studio"
        assert saved["client"]["address_line1"] == "New Street 5"
        await page.get_by_label("Customer", exact=True).hover()
        await page.locator(".v-autocomplete .v-field__clearable").click()
        await expect(page.locator(".save-status")).to_have_text("Saved")
        saved = await page.evaluate(
            f"async () => (await axios.get('/api/invoice/{second_id}')).data"
        )
        assert saved["client_id"] is None and saved["client"] is None
        await page.get_by_label("Customer", exact=True).fill("Acme")
        await page.get_by_role("option", name="Acme Studio").click()
        await page.get_by_role("button", name="Add item").click()
        await page.get_by_label("Description 2", exact=True).fill("Expenses")
        await page.get_by_label("Rate 2", exact=True).fill("50")
        await page.locator(".document-options summary").click()
        await page.locator(".v-select").filter(has_text="Tax type").click()
        await page.get_by_role("option", name="Per line", exact=True).click()
        await page.get_by_label("Taxable item 2", exact=True).uncheck()
        await expect(page.locator(".summary-total .summary-value")).to_have_text(
            "€169.00"
        )
        await expect(page.locator(".save-status")).to_have_text("Saved")
        saved = await page.evaluate(
            f"async () => (await axios.get('/api/invoice/{second_id}')).data"
        )
        assert saved["total"] == "169.00" and saved["tax_amount"] == "19.00"
        assert not errors, errors
        await browser.close()
        print(
            "Invoice editor: create, autosave, queued edits, retry, validation, mobile, issue and archived PDF passed."
        )


def main(exercise_fn=exercise):
    with tempfile.TemporaryDirectory(prefix="ziglag-editor-") as directory:
        root = Path(directory)
        env = _smoke_env(root / "test.db")
        _run_smoke_setup(env)
        token = _create_smoke_token(
            env["SQLALCHEMY_DATABASE_URI"],
            env["SECRET_KEY"],
            env["SECURITY_PASSWORD_SALT"],
        )
        port = _free_localhost_port()
        base_url = f"http://127.0.0.1:{port}"
        # Isolate issued PDF archives as well as the database.
        server = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys; from stk.app import create_app; app = create_app(); app.instance_path = sys.argv[1]; app.run(host='127.0.0.1', port=int(sys.argv[2]), use_reloader=False)",
                str(root),
                str(port),
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_smoke_server(base_url, server)
            asyncio.run(exercise_fn(base_url, token))
        finally:
            server.terminate()
            stdout, stderr = server.communicate(timeout=10)
            if "Traceback" in stderr:
                print(stderr)


if __name__ == "__main__":
    main()
