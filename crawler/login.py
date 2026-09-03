# ============================================================================
# File: login.py
# ============================================================================

import os
import logging

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def _normalized(value):

    return str(value or "").strip().casefold().replace("_", "-")


def _matches_language(value, candidates):

    normalized_value = _normalized(value)

    return any(
        normalized_value == _normalized(candidate)
        for candidate in candidates
        if candidate
    )


async def _select_native_language(page, language_cfg):

    configured_selector = str(
        language_cfg.get("selector") or ""
    ).strip()

    selectors = [configured_selector] if configured_selector else []
    selectors.extend([
        "select[name*='lang' i]",
        "select[id*='lang' i]",
        "select[name*='locale' i]",
        "select[id*='locale' i]",
        "select"
    ])

    labels = language_cfg.get("labels", [])
    values = language_cfg.get("values", [])
    candidates = [*labels, *values]
    visited = set()

    for selector in selectors:

        if not selector or selector in visited:
            continue

        visited.add(selector)
        locators = page.locator(selector)

        for index in range(await locators.count()):

            select = locators.nth(index)

            if not await select.is_visible():
                continue

            options = await select.locator("option").evaluate_all(
                """options => options.map(option => ({
                    value: option.value,
                    label: (option.textContent || '').trim()
                }))"""
            )

            for option in options:

                if not (
                    _matches_language(option.get("label"), candidates)
                    or _matches_language(option.get("value"), candidates)
                ):
                    continue

                await select.select_option(value=option["value"])
                logger.info(
                    "登入語言已切換為：%s",
                    option.get("label") or option.get("value")
                )
                return True

    return False


async def _select_custom_language(page, language_cfg):

    current_labels = language_cfg.get("current_labels", ["English"])
    target_labels = language_cfg.get("labels", [])
    configured_selector = str(
        language_cfg.get("selector") or ""
    ).strip()

    triggers = []

    if configured_selector:
        triggers.append(page.locator(configured_selector))

    for label in current_labels:
        triggers.extend([
            page.get_by_role("combobox", name=label, exact=False),
            page.get_by_role("button", name=label, exact=False),
            page.get_by_text(label, exact=True)
        ])

    for trigger_group in triggers:

        for index in range(await trigger_group.count()):

            trigger = trigger_group.nth(index)

            if not await trigger.is_visible():
                continue

            try:
                current_text = await trigger.inner_text()
            except Exception:
                current_text = ""

            if _matches_language(current_text, target_labels):
                logger.info("登入語言已是：%s", current_text.strip())
                return True

            await trigger.click()

            for label in target_labels:
                option_groups = [
                    page.get_by_role("option", name=label, exact=True),
                    page.get_by_role("menuitem", name=label, exact=True),
                    page.get_by_text(label, exact=True)
                ]

                for option in option_groups:
                    for option_index in range(await option.count()):
                        item = option.nth(option_index)

                        if await item.is_visible():
                            await item.click()
                            logger.info("登入語言已切換為：%s", label)
                            return True

    return False


async def select_login_language(page, login_cfg, language_override=None):

    language_cfg = dict(login_cfg.get("language", {}))
    language_cfg.update(language_override or {})

    if not language_cfg.get("enabled", False):
        return

    timeout_ms = int(language_cfg.get("timeout_ms", 10000))
    await page.wait_for_timeout(300)

    selected = await _select_native_language(page, language_cfg)

    if not selected:
        selected = await _select_custom_language(page, language_cfg)

    if not selected:
        message = (
            "無法在登入頁選擇目標語言。請確認 login.language.selector、"
            "labels 與 values 設定是否符合目前 SENTRY 登入頁。"
        )

        if language_cfg.get("required", True):
            raise RuntimeError(message)

        logger.warning(message)
        return

    try:
        await page.wait_for_load_state(
            "networkidle",
            timeout=timeout_ms
        )
    except Exception:
        await page.wait_for_timeout(500)


async def login(page, config, language_override=None):

    load_dotenv()

    login_cfg = config.get("login") or {}

    # 舊版設定檔可能沒有 enabled；缺省時維持原本的登入行為。
    if not login_cfg.get("enabled", True):
        return

    required_settings = [
        "url",
        "username_selector",
        "password_selector",
        "submit_selector"
    ]
    missing_settings = [
        key for key in required_settings
        if not login_cfg.get(key)
    ]

    if missing_settings:
        raise RuntimeError(
            "config/config.yaml 的 login 區塊缺少必要設定："
            + ", ".join(missing_settings)
        )

    await page.goto(
        login_cfg["url"],
        wait_until="networkidle"
    )

    # SENTRY 會依登入前選擇的語言決定登入後整個介面的語系。
    await select_login_language(
        page,
        login_cfg,
        language_override
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
