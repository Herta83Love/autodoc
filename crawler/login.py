# ============================================================================
# File: login.py
# ============================================================================

import os

from dotenv import load_dotenv


async def login(page, config):

    load_dotenv()

    login_cfg = config["login"]

    if not login_cfg["enabled"]:
        return

    await page.goto(
        login_cfg["url"],
        wait_until="networkidle"
    )

    username = os.getenv("LOGIN_USERNAME")
    password = os.getenv("LOGIN_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "LOGIN_USERNAME 與 LOGIN_PASSWORD 必須設定於環境變數或 .env"
        )

    username_selector = login_cfg["username_selector"]
    password_selector = login_cfg["password_selector"]
    submit_selector = login_cfg["submit_selector"]

    await page.fill(
        username_selector,
        username
    )

    await page.fill(
        password_selector,
        password
    )

    await page.screenshot(
        path="output/login_before.png"
    )

    await page.click(
        submit_selector
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
