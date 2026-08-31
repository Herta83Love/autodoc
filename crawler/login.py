import os


async def login(page, config):

    login_cfg = config["login"]

    if not login_cfg["enabled"]:
        return

    await page.goto(
        login_cfg["url"],
        wait_until="networkidle"
    )

    await page.fill(
        'input[name="account"]',
        os.getenv("LOGIN_USERNAME")
    )

    await page.fill(
        'input[name="password"]',
        os.getenv("LOGIN_PASSWORD")
    )

    await page.screenshot(
        path="output/login_before.png"
    )

    await page.click(
    'input[type="submit"]'
)

    await page.wait_for_timeout(3000)

    print(await page.title())
    print(page.url)

    await page.wait_for_load_state(
        "networkidle"
    )

    await page.screenshot(
        path="output/login_after.png"
    )

    print("✅ Login Success")