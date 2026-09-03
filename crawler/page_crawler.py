# ============================================================================
# File: page_crawler.py
# ============================================================================

from pathlib import Path

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
    menu_items,
    language="zh-TW",
    output_root="output/zh-TW",
    term_index=None
):

    results = []

    total = len(menu_items)
    screenshot_dir = f"{output_root}/screenshots"
    html_dir = f"{output_root}/html"
    icon_dir = f"{output_root}/icons"
    Path(html_dir).mkdir(parents=True, exist_ok=True)
    term_index = term_index if term_index is not None else {}

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

            # Save official UI terms before screenshots or parsing can fail.
            term_index[f"menu:{index}"] = {
                "category": category,
                "page": title,
                "tab": None
            }

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

            before_snapshot = None

            if frame:

                try:

                    before_snapshot = await crawler.wait_helper.get_dom_snapshot(
                        frame
                    )

                except Exception:
                    pass

            #
            # 點擊選單
            #
            await link.click()

            frame = await get_main_frame(
                page,
                timeout_ms=3000
            )

            if frame is None:

                print(
                    "❌ 找不到 mainFrame"
                )

                continue

            await crawler.wait_helper.wait_dom_ready(
                frame,
                before_snapshot=before_snapshot
            )

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
                    f"{html_dir}/debug_{index}_{title}.html"
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

                for tab_index, tab_name in enumerate(tab_names):

                    term_index[f"menu:{index}/tab:{tab_index}"] = {
                        "category": category,
                        "page": title,
                        "tab": tab_name
                    }

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

                        before_tab = None

                        try:

                            before_tab = await crawler.wait_helper.get_dom_snapshot(
                                frame
                            )

                        except Exception:
                            pass

                        await locator.first.click()

                        await crawler.wait_helper.wait_dom_ready(
                            frame,
                            before_snapshot=before_tab
                        )

                        screenshot = (
                            await save_screenshot(
                                frame,
                                f"{index}_{title}_{tab_index}_{tab_name}",
                                screenshot_dir
                            )
                        )

                        print(
                            f"Screenshot: {screenshot}"
                        )

                        html_file = (
                            await save_html(
                                frame,
                                f"{index}_{title}_{tab_index}_{tab_name}",
                                html_dir
                            )
                        )
                        actions = await extract_actions(
                            frame,
                            title,
                            tab_name,
                            icon_dir,
                            screenshot
                        )
                        metadata = (
                            await analyze_page(

                                frame,

                                category,

                                title,

                                tab_name,

                                frame.url,

                                screenshot,

                                html_file,

                                language=language,

                                page_key=f"menu:{index}/tab:{tab_index}",

                                menu_index=index,

                                tab_index=tab_index
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
                    f"{index}_{title}",
                    screenshot_dir
                )
            )

            print(
                f"Screenshot: {screenshot}"
            )

            html_file = (
                await save_html(
                    frame,
                    f"{index}_{title}",
                    html_dir
                )
            )
            actions = await extract_actions(
                frame,
                title,
                None,
                icon_dir,
                screenshot
            )

            metadata = (
                await analyze_page(

                    frame,

                    category,

                    title,

                    None,

                    frame.url,

                    screenshot,

                    html_file,

                    language=language,

                    page_key=f"menu:{index}",

                    menu_index=index,

                    tab_index=None
                )
            )

            metadata.actions = actions
            results.append(
                metadata.model_dump()
            )

            print(
                f"✅ 完成: {title}"
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
