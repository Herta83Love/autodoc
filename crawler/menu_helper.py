# ============================================================================
# File: menu_helper.py
# ============================================================================

import logging


logger = logging.getLogger(__name__)


async def expand_all_menus(page):

    # 盡可能把所有可展開選單打開

    selectors = [
        ".menu-item",
        ".nav-item",
        ".sidebar-item",
        ".treeview",
        ".has-submenu",
        ".menu-link"
    ]

    for selector in selectors:

        try:

            items = await page.locator(
                selector
            ).all()

            for item in items:

                try:
                    await item.click()
                except Exception as exc:
                    logger.debug(
                        "選單項目無法展開（selector=%s）：%s",
                        selector,
                        exc
                    )

        except Exception as exc:
            logger.debug(
                "選單 selector 無法查詢（selector=%s）：%s",
                selector,
                exc
            )

    await page.wait_for_timeout(3000)
