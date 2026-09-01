# ============================================================================
# File: tab_explorer.py
# ============================================================================

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

                except Exception:
                    pass

        except Exception:
            pass

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