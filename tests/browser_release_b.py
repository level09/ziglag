"""Run with uv run python -m tests.browser_release_b."""

import asyncio

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
        await expect(page.get_by_text("Get ready to issue invoices")).to_be_visible()
        await page.get_by_role("link", name="Complete profile").click()
        await expect(page.get_by_label("Business Name", exact=True)).to_be_visible()
        await page.get_by_label("Business Name", exact=True).fill("North Studio")
        await page.get_by_label("Address Line 1", exact=True).fill("Example Street 12")
        await page.get_by_label("Steuernummer", exact=True).fill("12/345/67890")
        await page.get_by_label("Payment instructions", exact=True).fill(
            "Please use the invoice reference.\nBank: Example Bank"
        )

        async def failure(route):
            if route.request.method == "POST":
                await route.fulfill(
                    status=503, content_type="application/json", body="{}"
                )
            else:
                await route.continue_()

        await page.route("**/api/settings", failure)
        await page.get_by_role("button", name="Save changes").click()
        await expect(page.locator(".v-alert")).to_contain_text(
            "Your changes are still here"
        )
        await expect(page.get_by_label("Business Name", exact=True)).to_have_value(
            "North Studio"
        )
        await page.unroute("**/api/settings", failure)
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(route):
            if route.request.method == "POST":
                response = await route.fetch()
                started.set()
                await release.wait()
                await route.fulfill(response=response)
            else:
                await route.continue_()

        await page.route("**/api/settings", delayed)
        await page.get_by_role("button", name="Save changes").click()
        await asyncio.wait_for(started.wait(), 10)
        await page.get_by_label("Owner Name", exact=True).fill("Newer edit")
        release.set()
        await expect(page.locator(".settings-savebar")).to_contain_text(
            "Unsaved changes"
        )
        await expect(page.get_by_label("Owner Name", exact=True)).to_have_value(
            "Newer edit"
        )
        await page.unroute("**/api/settings", delayed)
        dialogs = []

        async def stay(dialog):
            dialogs.append(dialog.type)
            await dialog.dismiss()

        page.on("dialog", stay)
        await page.get_by_role("link", name="Dashboard", exact=True).click()
        assert dialogs == ["beforeunload"], dialogs
        assert "/settings/business/" in page.url
        page.remove_listener("dialog", stay)
        await page.get_by_role("button", name="Save changes").click()
        await expect(page.locator(".settings-savebar")).to_contain_text(
            "All changes saved"
        )
        await expect(page.get_by_text("Business profile ready")).to_be_visible()
        await page.evaluate("scrollTo(0, 0)")
        await page.screenshot(path="/tmp/ziglag-settings-desktop.png")
        await page.goto(base_url + "/dashboard/")
        await expect(
            page.get_by_role("link", name="Create your first invoice")
        ).to_be_visible()
        await expect(
            page.get_by_text("Get ready to issue invoices")
        ).not_to_be_visible()

        await page.goto(base_url + "/clients/")
        await page.get_by_role("button", name="New customer").click()
        await page.get_by_role("button", name="Save", exact=True).click()
        await expect(page.get_by_label("Name", exact=True)).to_be_focused()
        await page.get_by_label("Name", exact=True).fill("South Studio")
        await page.get_by_label("Address Line 1", exact=True).fill("Customer Street 2")
        await page.get_by_label("Email", exact=True).fill("customer@example.test")
        await page.route("**/api/client/", failure)
        await page.get_by_role("button", name="Save", exact=True).click()
        await expect(page.get_by_role("dialog")).to_be_visible()
        await expect(page.get_by_label("Name", exact=True)).to_have_value(
            "South Studio"
        )
        await expect(page.locator(".v-alert")).to_contain_text(
            "Your changes are still here"
        )
        await page.unroute("**/api/client/", failure)
        await page.get_by_role("button", name="Save", exact=True).click()
        await expect(page.get_by_role("dialog")).not_to_be_visible()
        await expect(
            page.get_by_role("button", name="South Studio", exact=True)
        ).to_be_visible()
        await page.get_by_label("Search customers").fill("no matching name")
        await expect(page.get_by_text("No matching customers")).to_be_visible()
        await page.get_by_label("Search customers").fill("South")
        await expect(
            page.get_by_role("button", name="South Studio", exact=True)
        ).to_be_visible()

        await page.goto(base_url + "/invoices/new")
        await page.get_by_label("Customer", exact=True).fill("South")
        await page.get_by_role("option", name="South Studio").click()
        await page.get_by_label("Description 1", exact=True).fill("Design services")
        await page.get_by_label("Rate 1", exact=True).fill("100")
        await page.get_by_label("Service from", exact=True).fill("2026-09-01")
        await expect(page.locator(".save-status")).to_have_text("Saved")
        invoice_id = page.url.rsplit("/", 1)[1]
        await page.get_by_role("button", name="Review and issue").click()
        await page.get_by_role("button", name="Issue invoice", exact=True).click()
        await expect(page.get_by_role("dialog")).not_to_be_visible()
        share = await page.evaluate(
            "async id => (await axios.post('/api/invoice/' + id + '/share')).data",
            invoice_id,
        )
        archive = await page.request.get(base_url + f"/api/invoice/{invoice_id}/pdf")
        archived_bytes = await archive.body()
        public = await browser.new_page(viewport={"width": 1440, "height": 1000})
        for theme in ["light", "dark"]:
            await public.emulate_media(color_scheme=theme)
            for width in [1440, 390]:
                await public.set_viewport_size({"width": width, "height": 900})
                await public.goto(base_url + share["url"])
                await expect(
                    public.get_by_role("link", name="Download PDF")
                ).to_be_visible()
                await expect(
                    public.get_by_text("Bank: Example Bank", exact=False)
                ).to_be_visible()
                assert await public.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), (theme, width)
                await public.screenshot(
                    path=f"/tmp/ziglag-public-{theme}-{width}.png", full_page=True
                )
        downloaded = await public.request.get(base_url + share["url"] + "/pdf")
        assert await downloaded.body() == archived_bytes
        assert archived_bytes.startswith(b"%PDF")
        await public.keyboard.press("Tab")
        assert await public.locator(".download").evaluate(
            "el => el === document.activeElement"
        )
        variants = await page.evaluate(
            """async id => {
            const original = (await axios.get('/api/invoice/' + id)).data;
            const results = [];
            for (const template of ['branded', 'editorial']) {
                const created = await axios.post('/api/invoice/', {
                    client_id: original.client_id, template_key: template,
                    date: original.date, service_date_from: original.date,
                    currency_code: 'EUR', currency_symbol: '€',
                    notes: '<script>window.bad=true</script>' + 'LongNote'.repeat(30),
                    items: [{description:'Support', quantity:1, unit_price:25}]
                });
                await axios.post('/api/invoice/' + created.data.id + '/issue');
                await axios.post('/api/invoice/' + created.data.id + '/payment', {
                    amount:25, payment_date:original.date, method:'bank_transfer'
                });
                results.push((await axios.post('/api/invoice/' + created.data.id + '/share')).data.url);
            }
            await axios.post('/api/invoice/' + id + '/payment', {
                amount:40, payment_date:original.date, method:'bank_transfer'
            });
            const partial = (await axios.get('/api/invoice/' + id)).data;
            if (partial.balance_due !== '60.00') throw new Error('Partial balance mismatch');
            await axios.post('/api/invoice/' + id + '/payment', {
                amount:60, payment_date:original.date, method:'bank_transfer'
            });
            return results;
        }""",
            invoice_id,
        )
        for url in variants:
            await public.goto(base_url + url)
            await expect(public.get_by_text("Paid in full", exact=True)).to_be_visible()
            assert await public.evaluate(
                "!window.bad && document.documentElement.scrollWidth <= innerWidth"
            )
            await expect(
                public.locator(".multiline").filter(has_text="<script>")
            ).to_be_visible()
        await page.goto(base_url + "/clients/")
        await expect(page.locator("tbody")).to_contain_text("EUR")
        await expect(page.locator("tbody")).to_contain_text("USD")
        for width in [720, 390]:
            await page.set_viewport_size({"width": width, "height": 900})
            for path in ["/clients/", "/settings/business/"]:
                await page.goto(base_url + path)
                await page.wait_for_function(
                    "parseFloat(getComputedStyle(document.querySelector('.v-main')).paddingLeft) === 0"
                )
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), (width, path)
                if path == "/settings/business/":
                    await expect(
                        page.get_by_label("Business Name", exact=True)
                    ).to_be_visible()
                    await page.screenshot(path=f"/tmp/ziglag-settings-{width}.png")
        assert not errors, errors
        await browser.close()
        print(
            "Release B: setup, customer retry, settings retry and in-flight edits, navigation protection, issue, public light/dark/mobile and archived PDF passed."
        )


if __name__ == "__main__":
    main(exercise)
