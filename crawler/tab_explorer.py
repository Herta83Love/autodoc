# ============================================================================
# File: tab_explorer.py
# ============================================================================

import logging


logger = logging.getLogger(__name__)


async def discover_tabs(frame):

    tabs = []

    selectors = [

        # 第一層 Tab
        ".route_link a",

        # 第二層 Tab
        ".chart_change_button button",

        # 保底
        "[role='tab']",
        ".tab",
        ".tabs a",
        ".nav-tabs a",
        ".nav-link"
    ]

    for selector in selectors:

        try:

            locators = await frame.locator(
                selector
            ).all()

            for locator in locators:

                try:

                    text = await locator.text_content()

                    if not text:
                        continue

                    text = text.strip()

                    if len(text) == 0:
                        continue

                    tabs.append({
                        "name": text,
                        "locator": locator,
                        "selector": selector
                    })

                except Exception as exc:
                    logger.debug(
                        "略過無法解析的 Tab（selector=%s）：%s",
                        selector,
                        exc
                    )

        except Exception as exc:
            logger.debug(
                "Tab selector 無法查詢（selector=%s）：%s",
                selector,
                exc
            )

    unique = {}

    for tab in tabs:

        unique[
            tab["name"]
        ] = tab

    print(
        f"找到 {len(unique)} 個 Tabs"
    )

    for name in unique:

        print(
            f"Tab: {name}"
        )

    return list(
        unique.values()
    )
