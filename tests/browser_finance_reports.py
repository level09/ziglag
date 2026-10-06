"""Run with uv run python -m tests.browser_finance_reports."""

import asyncio
from datetime import date

from playwright.async_api import async_playwright, expect

from tests.browser_invoice_editor import main


async def exercise(base_url, token):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(f"{base_url}/_test/login?token={token}")
        await page.goto(f"{base_url}/invoices/new")
        await page.evaluate("""async () => {
            const iso = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            const today = new Date();
            const previous = new Date(today.getFullYear(), today.getMonth() - 1, 15);
            await axios.post('/api/settings', {business_name:'Finance Studio',
                address_line1:'Example Street 12', tax_number:'12/345/67890',
                currency_code:'EUR', currency_symbol:'€', tax_type:'on_total', tax_rate:0});
            const customer = await axios.post('/api/client/', {item:{name:'Finance Customer', address_line1:'Client Street 2'}});
            for (const [number, amount, currency, invoiceDate, paid] of [
                ['FIN-PAID-NOW', 300, 'EUR', today, 300],
                ['FIN-PAID-PREV', 100, 'EUR', previous, 100],
                ['FIN-PARTIAL', 200, 'EUR', previous, 50],
                ['FIN-USD', 100, 'USD', today, 0],
                ['FIN-DRAFT', 250, 'EUR', today, 0]
            ]) {
                const created = await axios.post('/api/invoice/', {
                    client_id:customer.data.id, invoice_number:number, date:iso(invoiceDate),
                    service_date_from:iso(invoiceDate), due_date:iso(today),
                    currency_code:currency, currency_symbol:currency === 'EUR' ? '€' : '$',
                    items:[{description:'Consulting', quantity:1, unit_price:amount}]
                });
                if (number !== 'FIN-DRAFT') await axios.post('/api/invoice/' + created.data.id + '/issue');
                if (paid) await axios.post('/api/invoice/' + created.data.id + '/payment', {amount:paid, payment_date:iso(today), method:'bank_transfer'});
            }
        }""")
        await page.goto(f"{base_url}/dashboard/")
        comparison = page.locator(".v-card").filter(
            has=page.get_by_role("heading", name="Paid invoice total this month")
        )
        await expect(comparison).to_contain_text("EUR 300.00")
        await expect(comparison).to_contain_text("+200.0%")
        await page.goto(f"{base_url}/invoices/")
        summary = page.locator(".v-card").filter(
            has=page.get_by_role("heading", name="Totals for all", exact=False)
        )
        await expect(summary).to_contain_text("5 matching invoices")
        await expect(summary).to_contain_text("EUR 850.00")
        await expect(summary).to_contain_text("EUR 150.00")
        await expect(summary).to_contain_text("USD 100.00")
        await page.get_by_role("button", name="Last month", exact=True).click()
        await expect(summary).to_contain_text("2 matching invoices")
        assert "start_date=" in page.url and "end_date=" in page.url
        await page.reload()
        await expect(summary).to_contain_text("2 matching invoices")
        await page.get_by_role("button", name="All dates", exact=True).click()
        await expect(summary).to_contain_text("5 matching invoices")
        await page.go_back()
        await expect(summary).to_contain_text("2 matching invoices")
        await page.get_by_role("button", name="This month", exact=True).click()
        await expect(summary).to_contain_text("3 matching invoices")
        await page.get_by_label("Search invoice or customer").fill("FIN-PAID")
        await expect(summary).to_contain_text("1 matching invoice")
        await page.get_by_role("button", name="All dates", exact=True).click()
        await expect(summary).to_contain_text("2 matching invoices")
        await page.goto(f"{base_url}/reports/")
        await expect(page.locator(".monthly-chart-bar")).to_have_count(12)
        await expect(page.locator(".annual")).to_contain_text(
            "300.00" if date.today().month == 1 else "400.00"
        )
        await page.get_by_role("button", name="Cash received", exact=True).click()
        await expect(
            page.get_by_role("heading", name="Cash received", exact=True)
        ).to_be_visible()
        await expect(page.locator(".annual")).to_contain_text("450.00")
        await expect(page.locator(".annual td").nth(1)).to_have_text("3")
        await expect(page.locator(".monthly-chart-bar")).to_have_count(12)

        # A slow response must not replace the selected report.
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(route):
            if "basis=invoices" in route.request.url:
                response = await route.fetch()
                started.set()
                await release.wait()
                await route.fulfill(response=response)
            else:
                await route.continue_()

        await page.route("**/api/reports/monthly?*", delayed)
        await page.get_by_role("button", name="Paid invoices", exact=True).click()
        await asyncio.wait_for(started.wait(), 10)
        await page.get_by_role("button", name="Cash received", exact=True).click()
        await expect(page.locator(".annual")).to_contain_text("450.00")
        release.set()
        await page.wait_for_timeout(300)
        await expect(page.locator(".annual")).to_contain_text("450.00")
        await page.unroute("**/api/reports/monthly?*", delayed)
        await page.screenshot(path="/tmp/ziglag-finance-reports.png", full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        for path in ("/invoices/", "/reports/", "/dashboard/"):
            await page.goto(base_url + path)
            await expect(page.get_by_role("heading", level=1)).to_be_visible()
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), path
        assert not errors, errors
        await browser.close()
        print(
            "Finance: comparisons, filtered totals, date shortcuts, history, charts, cash report, races and mobile passed."
        )


if __name__ == "__main__":
    main(exercise)
