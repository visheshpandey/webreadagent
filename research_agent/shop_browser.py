"""Real browser automation against a live demo storefront (saucedemo.com).

saucedemo.com is a stable, bot-friendly e-commerce site built by Sauce Labs
for automation testing, so it is used here for the "take a real action" step
instead of a real retailer, which would aggressively block bot traffic and
make the demo unreliable.

When ANAKIN_API_KEY is set, the browser itself is Anakin's managed cloud
browser (connected over CDP) rather than a local Chromium instance, so the
same Playwright script drives a remote, optionally screen-recorded session.
Falls back to a local browser if no key is set or the remote connection fails.
"""

from dataclasses import dataclass

from playwright.sync_api import sync_playwright

from . import anakin_client

BASE_URL = "https://www.saucedemo.com/"
LOGIN_USER = "standard_user"
LOGIN_PASS = "secret_sauce"


@dataclass
class Product:
    name: str
    price: str
    description: str


def _open_browser(p, log, headless: bool = True, slow_mo_ms: int = 0, record: bool = False,
                   use_anakin_browser: bool = True):
    """Return (browser, page). Prefers Anakin's cloud browser when configured,
    unless use_anakin_browser=False forces a local browser (e.g. so a headed
    run is visible on screen for a live recording)."""
    if use_anakin_browser and anakin_client.is_configured():
        try:
            opts = anakin_client.browser_connect_options(record=record)
            browser = p.chromium.connect_over_cdp(opts["ws_endpoint"], headers=opts["headers"])
            if browser.contexts and browser.contexts[0].pages:
                page = browser.contexts[0].pages[0]
            else:
                page = browser.new_page()
            log("Connected to Anakin's cloud browser" + (" (recording)" if record else ""))
            return browser, page
        except Exception as e:
            log(f"Could not connect to Anakin's browser ({e}), falling back to a local browser")

    browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
    page = browser.new_page()
    return browser, page


def list_products(log=print, headless: bool = True, use_anakin_browser: bool = True) -> list[Product]:
    """Log in and scrape the live product catalog (name, price, description)."""
    with sync_playwright() as p:
        browser, page = _open_browser(p, log, headless=headless, use_anakin_browser=use_anakin_browser)
        page.goto(BASE_URL, timeout=20000)
        page.fill("#user-name", LOGIN_USER)
        page.fill("#password", LOGIN_PASS)
        page.click("#login-button")
        page.wait_for_selector(".inventory_list", timeout=10000)

        products = []
        items = page.locator(".inventory_item")
        for i in range(items.count()):
            item = items.nth(i)
            name = item.locator(".inventory_item_name").inner_text()
            price = item.locator(".inventory_item_price").inner_text()
            desc = item.locator(".inventory_item_desc").inner_text()
            products.append(Product(name=name, price=price, description=desc))

        browser.close()
        log(f"Read {len(products)} live product listings from {BASE_URL}")
        return products


def buy_product(product_name: str, buyer_first_name: str, buyer_last_name: str,
                 buyer_zip: str, screenshot_path: str, log=print,
                 headless: bool = True, slow_mo_ms: int = 0, record: bool = False,
                 use_anakin_browser: bool = True) -> dict:
    """Log in, add the named product to cart, and complete checkout end-to-end.

    Returns a dict with the order summary and confirmation message. This is a
    real, reversible action (no real payment) that leaves a screenshot as proof.
    Set headless=False (and optionally slow_mo_ms) to watch a local browser live.
    Set record=True (requires ANAKIN_API_KEY) to have Anakin record the remote
    session server-side as a WebM video. Set use_anakin_browser=False to force
    a local browser even when ANAKIN_API_KEY is set (e.g. so --headed opens a
    real window on screen for a live recording instead of running in the cloud).
    """
    with sync_playwright() as p:
        browser, page = _open_browser(
            p, log, headless=headless, slow_mo_ms=slow_mo_ms, record=record,
            use_anakin_browser=use_anakin_browser,
        )
        page.goto(BASE_URL, timeout=20000)
        page.fill("#user-name", LOGIN_USER)
        page.fill("#password", LOGIN_PASS)
        page.click("#login-button")
        page.wait_for_selector(".inventory_list", timeout=10000)
        log(f"Logged in to {BASE_URL}")

        item_row = page.locator(".inventory_item").filter(has_text=product_name)
        item_row.locator("button").click()
        log(f"Added '{product_name}' to cart")

        page.click(".shopping_cart_link")
        page.wait_for_selector(".cart_list", timeout=10000)

        page.click("#checkout")
        page.wait_for_selector("#first-name", timeout=10000)
        page.fill("#first-name", buyer_first_name)
        page.fill("#last-name", buyer_last_name)
        page.fill("#postal-code", buyer_zip)
        page.click("#continue")
        page.wait_for_selector(".summary_info", timeout=10000)

        total = page.locator(".summary_total_label").inner_text()
        log(f"Checkout summary: {total}")

        page.click("#finish")
        page.wait_for_selector(".complete-header", timeout=10000)
        confirmation = page.locator(".complete-header").inner_text()

        page.screenshot(path=screenshot_path, full_page=True)
        log(f"Saved confirmation screenshot to {screenshot_path}")

        if not headless:
            page.wait_for_timeout(3000)

        browser.close()

        return {"product": product_name, "total": total, "confirmation": confirmation}
