"""Run with uv run python -m tests.browser_product_workspace."""

import asyncio
import json

from playwright.async_api import async_playwright, expect

from tests.browser_invoice_editor import main


async def exercise(base_url, token):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(f"{base_url}/_test/login?token={token}")
        await expect(page.get_by_text("Your first invoice starts here")).to_be_visible()
        await page.goto(f"{base_url}/invoices/new")
        invoice_id = await page.evaluate("""async () => { try {
            await axios.post('/api/settings', {
                business_name:'North Studio', address_line1:'Example Street 12',
                address_line2:'10115 Berlin', tax_number:'12/345/67890',
                email:'hello@example.test', currency_code:'EUR', currency_symbol:'€',
                tax_type:'on_total', tax_rate:0
            });
            const customer = await axios.post('/api/client/', {item:{
                name:'North & South Studio with a long customer name',
                address_line1:'Customer Street 2', email:'accounts@example.test'
            }});
            const today = new Date().toLocaleDateString('en-CA');
            const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
            let issuedId;
            for (let i = 0; i < 28; i++) {
                const created = await axios.post('/api/invoice/', {
                    client_id:customer.data.id, invoice_number:'WORK-' + String(i).padStart(3, '0'),
                    date:today, service_date_from:today, due_date:yesterday.toLocaleDateString('en-CA'),
                    items:[{description:'September support', quantity:1, unit_price:100}]
                });
                if (i === 0) {
                    issuedId = created.data.id;
                    await axios.post('/api/invoice/' + issuedId + '/issue');
                }
            }
            return issuedId;
            } catch(error) { throw new Error(JSON.stringify({url:error.config?.url, status:error.response?.status, data:error.response?.data})); }
        }""")
        await page.goto(f"{base_url}/dashboard/")
        await expect(
            page.locator(".summary-card").filter(has_text="Unpaid invoices")
        ).to_contain_text("EUR 100.00")
        await page.screenshot(
            path="/tmp/ziglag-workspace-dashboard.png", full_page=True
        )
        await page.goto(f"{base_url}/invoices/?status=draft&page=2")
        await expect(
            page.get_by_role("link", name="WORK-001", exact=True)
        ).to_be_visible()
        search = page.get_by_label("Search invoice or customer")
        await search.fill("WORK-000")
        await expect(page.get_by_text("No matching invoices")).to_be_visible()
        await page.get_by_role("button", name="All", exact=True).click()
        await expect(
            page.get_by_role("link", name="WORK-000", exact=True)
        ).to_be_visible()
        assert "page=1" in page.url
        await search.fill("North & South")
        await expect(page.locator("tbody tr")).to_have_count(25)

        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(route):
            if "search=WORK-001" in route.request.url:
                response = await route.fetch()
                started.set()
                await release.wait()
                await route.fulfill(response=response)
            else:
                await route.continue_()

        await page.route("**/api/invoices?*", delayed)
        await search.fill("WORK-001")
        await asyncio.wait_for(started.wait(), 10)
        await search.fill("WORK-002")
        await expect(
            page.get_by_role("link", name="WORK-002", exact=True)
        ).to_be_visible()
        release.set()
        await page.wait_for_timeout(300)
        await expect(
            page.get_by_role("link", name="WORK-001", exact=True)
        ).not_to_be_visible()
        await page.unroute("**/api/invoices?*", delayed)

        async def failure(route):
            await route.fulfill(status=503, content_type="application/json", body="{}")

        await page.route("**/api/invoices?*", failure)
        await search.fill("WORK-003")
        await expect(page.get_by_role("alert")).to_contain_text(
            "Previous results may not match"
        )
        await page.unroute("**/api/invoices?*", failure)
        await page.get_by_role("button", name="Retry", exact=True).click()
        link = page.get_by_role("link", name="WORK-003", exact=True)
        await expect(link).to_be_visible()
        await link.focus()
        await page.keyboard.press("Enter")
        await expect(page.get_by_label("Description 1", exact=True)).to_have_value(
            "September support"
        )
        await page.go_back()
        await expect(page.get_by_label("Search invoice or customer")).to_have_value(
            "WORK-003"
        )
        await page.get_by_label("Search invoice or customer").fill("")
        await expect(page.locator("tbody tr")).to_have_count(25)
        await page.screenshot(path="/tmp/ziglag-workspace-invoices.png", full_page=True)

        for theme in ["dark", "light"]:
            await page.evaluate(
                '(theme) => localStorage.setItem("ziglag-theme", theme)', theme
            )
            await page.reload()
            await expect(page.locator("tbody tr")).to_have_count(25)
            await page.screenshot(
                path=f"/tmp/ziglag-workspace-{theme}.png", full_page=True
            )
        await page.set_viewport_size({"width": 390, "height": 844})
        await expect(page.locator(".mobile-invoice")).to_have_count(25)
        await page.wait_for_function(
            "parseFloat(getComputedStyle(document.querySelector('.v-main')).paddingLeft) === 0"
        )
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        await page.screenshot(path="/tmp/ziglag-workspace-mobile.png", full_page=False)
        await page.set_viewport_size({"width": 1440, "height": 1000})

        await page.goto(f"{base_url}/invoices/{invoice_id}")

        # Send is intercepted so this test never contacts a mail server.
        async def email_failure(route):
            await route.fulfill(
                status=504,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": "Email status could not be confirmed. Check before sending again."
                    }
                ),
            )

        await page.route("**/send", email_failure)
        await page.get_by_role("button", name="Email invoice", exact=True).click()
        await (
            page.get_by_role("dialog")
            .get_by_role("button", name="Continue", exact=True)
            .click()
        )
        await expect(
            page.get_by_text(
                "Email status could not be confirmed. Check before sending again."
            )
        ).to_be_visible()
        await page.unroute("**/send", email_failure)
        await page.evaluate(
            """async (id) => {
            await axios.post('/api/invoice/' + id + '/payment', {
                amount:100, payment_date:new Date().toLocaleDateString('en-CA'), method:'bank_transfer'
            });
        }""",
            invoice_id,
        )
        await page.goto(f"{base_url}/reports/")
        await expect(page.locator(".annual")).to_contain_text("100.00")
        await page.route("**/api/reports/monthly?*", failure)
        await page.locator(".v-select").filter(has_text="Year").click()
        await page.get_by_role("option").nth(1).click()
        await expect(page.get_by_role("alert")).to_contain_text(
            "The report could not be loaded"
        )
        await page.unroute("**/api/reports/monthly?*", failure)
        await page.get_by_role("button", name="Retry", exact=True).click()
        await expect(
            page.get_by_text("No paid invoices for", exact=False)
        ).to_be_visible()
        await page.evaluate("""async () => {
            const draft = (await axios.get('/api/invoices', {params:{status:'draft'}})).data.items[0];
            const invoice = (await axios.get('/api/invoice/' + draft.id)).data;
            await axios.post('/api/client/' + invoice.client_id, {item:{name:'Customer' + 'x'.repeat(180)}});
            await axios.post('/api/invoice/' + draft.id, {invoice_number:'REF' + '9'.repeat(47)});
        }""")
        for width in [1440, 390]:
            await page.set_viewport_size({"width": width, "height": 900})
            await page.goto(base_url + "/invoices/")
            await expect(
                page.get_by_role("link", name="REF" + "9" * 47, exact=True)
            ).to_be_visible()
            if width == 390:
                await page.wait_for_function(
                    "parseFloat(getComputedStyle(document.querySelector('.v-main')).paddingLeft) === 0"
                )
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), ("long text", width)
            assert (
                await page.locator(".workspace > .v-card[aria-busy]")
                .filter(has=page.locator(".v-pagination"))
                .evaluate("el => el.scrollWidth <= el.clientWidth")
            ), ("clipped long text", width)
        for width in [720, 390]:
            await page.set_viewport_size({"width": width, "height": 900})
            for path in ["/dashboard/", "/reports/", f"/invoices/{invoice_id}"]:
                await page.goto(base_url + path)
                await page.wait_for_function(
                    "parseFloat(getComputedStyle(document.querySelector('.v-main')).paddingLeft) === 0"
                )
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), (width, path)
        await page.goto(base_url + "/invoices/")
        await expect(page.locator(".mobile-invoice")).to_have_count(25)
        await page.screenshot(path="/tmp/ziglag-workspace-mobile.png")
        await page.get_by_role("button", name="Account menu").click()
        await expect(page.get_by_text("Change password", exact=True)).to_be_visible()
        await page.keyboard.press("Escape")
        await page.emulate_media(reduced_motion="reduce")
        await page.get_by_role("button", name="Toggle navigation").click()
        await expect(
            page.get_by_role("link", name="Customers", exact=True)
        ).to_be_visible()
        anonymous = await browser.new_page(viewport={"width": 390, "height": 844})
        await anonymous.goto(base_url + "/login")
        await expect(anonymous.locator('input[type="password"]')).to_be_visible()
        assert await anonymous.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        )
        await anonymous.close()
        assert not errors, errors
        await browser.close()
        print(
            "Workspace: dashboard, search, filters, races, retry, history, themes, mobile, email feedback and reports passed."
        )


if __name__ == "__main__":
    main(exercise)
