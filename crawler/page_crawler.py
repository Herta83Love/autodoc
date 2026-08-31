#page_crawler.py
import asyncio

import crawler.wait_helper

from crawler.frame_helper import (
    get_main_frame
)

from crawler.screenshot import (
    save_screenshot
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

            await link.click()

            await asyncio.sleep(1)

            frame = await get_main_frame(
                page
            )

            if frame is None:

                print(
                    "❌ 找不到 mainFrame"
                )

                continue

            await crawler.wait_helper.wait_frame_ready(
                frame
            )

            print(
                f"Frame URL: {frame.url}"
            )

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

                        await locator.first.click()

                        await crawler.wait_helper.wait_frame_ready(
                            frame
                        )

                        screenshot = (
                            await save_screenshot(
                                frame,
                                f"{title}_{tab_name}"
                            )
                        )

                        html_file = (
                            await save_html(
                                frame,
                                f"{title}_{tab_name}"
                            )
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

            html_file = (
                await save_html(
                    frame,
                    title
                )
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

            results.append(
                metadata.model_dump()
            )

            print(
                f"✅ 完成: {title}"
            )

            await asyncio.sleep(1)

        except Exception as e:

            print(
                f"❌ 頁面失敗: {title}"
            )

            print(e)

    print(
        f"\n完成，共取得 {len(results)} 筆 Metadata"
    )

    return results