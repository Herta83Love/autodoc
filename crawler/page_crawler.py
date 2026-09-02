# ============================================================================
# File: page_crawler.py
# ============================================================================

import asyncio

import crawler.wait_helper

from crawler.frame_helper import (
    get_main_frame
)

from crawler.screenshot import (
    save_screenshot
)
from crawler.action_extractor import (
    extract_actions
)
from crawler.html_exporter import (
    save_html
)
from crawler.page_parser import (
    analyze_page
)

from crawler.tab_explorer import (
    discover_tabs
)


async def crawl_pages(
    page,
    menu_items
):

    results = []

    total = len(menu_items)

    print(
        f"\n開始爬取 {total} 個頁面\n"
    )

    menu_links = await page.locator(
        ".menu-item"
    ).all()

    for index, link in enumerate(menu_links):

        try:

            menu_item = menu_items[index]

            category = menu_item.get(
                "category",
                "Unknown"
            )

            title = (
                await link.text_content()
            ).strip()

            print(
                f"\n[{index + 1}/{total}] {title}"
            )

            print(
                f"Category: {category}"
            )

            #
            # 先取得目前 frame
            #
            frame = await get_main_frame(
                page
            )

            before_text = ""

            if frame:

                try:

                    before_text = (
                        await frame.locator(
                            "body"
                        ).inner_text()
                    )[:800]

                except Exception:
                    pass

            #
            # 點擊選單
            #
            await link.click()

            #
            # 等待 frame
            #
            await asyncio.sleep(0.5)

            frame = await get_main_frame(
                page
            )

            if frame is None:

                print(
                    "❌ 找不到 mainFrame"
                )

                continue

            #
            # 等待頁面內容變化
            #
            for _ in range(30):

                await asyncio.sleep(0.5)

                try:

                    current_text = (
                        await frame.locator(
                            "body"
                        ).inner_text()
                    )[:800]

                    if (
                        current_text
                        and current_text != before_text
                    ):

                        print(
                            "✅ 頁面內容已更新"
                        )

                        break

                except Exception:
                    pass

            #
            # 等待頁面穩定
            #
            await crawler.wait_helper.wait_frame_ready(
                frame
            )

            #
            # 額外等待避免 Vue SPA 尚未完成 render
            #
            await crawler.wait_helper.wait_dom_stable(frame)

            print(
                f"Frame URL: {frame.url}"
            )

            #
            # Debug Body
            #
            try:

                body_text = (
                    await frame.locator(
                        "body"
                    ).inner_text()
                )

                print(
                    "\n===== BODY PREVIEW ====="
                )

                print(
                    body_text[:500]
                )

                print(
                    "\n========================\n"
                )

            except Exception:
                pass

            #
            # Debug HTML
            #
            try:

                html = await frame.content()

                debug_path = (
                    f"output/html/debug_{title}.html"
                )

                with open(
                    debug_path,
                    "w",
                    encoding="utf-8"
                ) as f:

                    f.write(html)

            except Exception as e:

                print(
                    f"Debug HTML保存失敗: {e}"
                )

            #
            # Discover Tabs
            #
            tabs = await discover_tabs(
                frame
            )

            print(
                f"找到 {len(tabs)} 個 Tabs"
            )

            #
            # 有 Tabs
            #
            if len(tabs) > 0:

                tab_names = []

                for tab in tabs:

                    name = tab["name"]

                    if name not in tab_names:

                        tab_names.append(
                            name
                        )

                for tab_name in tab_names:

                    try:

                        print(
                            f"切換 Tab: {tab_name}"
                        )

                        locator = frame.get_by_text(
                            tab_name,
                            exact=True
                        )

                        if (
                            await locator.count()
                            == 0
                        ):

                            print(
                                f"⚠️ 找不到 Tab: {tab_name}"
                            )

                            continue

                        before_tab = ""

                        try:

                            before_tab = (
                                await frame.locator(
                                    "body"
                                ).inner_text()
                            )[:800]

                        except Exception:
                            pass

                        await locator.first.click()

                        #
                        # 等待 Tab 內容變化
                        #
                        for _ in range(20):

                            await asyncio.sleep(0.5)

                            try:

                                current_tab = (
                                    await frame.locator(
                                        "body"
                                    ).inner_text()
                                )[:800]

                                if (
                                    current_tab
                                    and current_tab != before_tab
                                ):
                                    break

                            except Exception:
                                pass

                        await crawler.wait_helper.wait_frame_ready(
                            frame
                        )

                        await asyncio.sleep(1)

                        screenshot = (
                            await save_screenshot(
                                frame,
                                f"{title}_{tab_name}"
                            )
                        )

                        print(
                            f"Screenshot: {screenshot}"
                        )

                        html_file = (
                            await save_html(
                                frame,
                                f"{title}_{tab_name}"
                            )
                        )
                        actions = await extract_actions(
                            frame,
                            title,
                            tab_name
                        )
                        metadata = (
                            await analyze_page(

                                frame,

                                category,

                                title,

                                tab_name,

                                frame.url,

                                screenshot,

                                html_file
                            )
                        )
                        metadata.actions = actions

                        results.append(
                            metadata.model_dump()
                        )

                        print(
                            f"✅ 完成 Tab: {tab_name}"
                        )

                    except Exception as e:

                        print(
                            f"❌ Tab失敗: {tab_name}"
                        )

                        print(e)

                print(
                    f"✅ 完成: {title}"
                )

                continue

            #
            # 無 Tabs
            #
            screenshot = (
                await save_screenshot(
                    frame,
                    title
                )
            )

            print(
                f"Screenshot: {screenshot}"
            )

            html_file = (
                await save_html(
                    frame,
                    title
                )
            )
            actions = await extract_actions(
                frame,
                title,
                None
            )

            metadata = (
                await analyze_page(

                    frame,

                    category,

                    title,

                    None,

                    frame.url,

                    screenshot,

                    html_file
                )
            )

            metadata.actions = actions
            results.append(
                metadata.model_dump()
            )

            print(
                f"✅ 完成: {title}"
            )

            await asyncio.sleep(
                1
            )

        except Exception as e:

            print(
                f"❌ 頁面失敗: {title}"
            )

            print(e)

    print(
        f"\n完成，共取得 {len(results)} 筆 Metadata"
    )

    return results