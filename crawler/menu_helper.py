# ============================================================================
# File: menu_helper.py
# ============================================================================

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
                except:
                    pass

        except:
            pass

    await page.wait_for_timeout(3000)