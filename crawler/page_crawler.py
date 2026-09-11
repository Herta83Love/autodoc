# ============================================================================
# File: page_crawler.py
# ============================================================================

import asyncio
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

import crawler.wait_helper

from crawler.frame_helper import (
    get_main_frame
)

from crawler.screenshot import (
    cleanup_screenshot_capture,
    save_screenshot
)
from crawler.action_extractor import (
    extract_actions
)
from crawler.interaction_explorer import (
    UnsafeInteractionState,
    explore_safe_actions
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


def _route_identity(value):
    """Return the stable URL portion used to identify a SENTRY page."""

    parsed = urlsplit(str(value or "").strip())
    path = parsed.path.rstrip("/") or "/"
    return parsed.netloc.casefold(), path.casefold()


def _matches_expected_route(current_url, expected_url):
    if not expected_url:
        return False
    return _route_identity(current_url) == _route_identity(expected_url)


async def _wait_for_page_transition(
    page,
    previous_snapshot,
    previous_url="",
    expected_url="",
    expected_title="",
    allow_unchanged=False,
    timeout_ms=15000,
):
    """Wait for real navigation, not merely stability of the old page."""

    started = monotonic()
    deadline = started + timeout_ms / 1000
    latest_frame = None
    while monotonic() < deadline:
        latest_frame = await get_main_frame(page, timeout_ms=1000)
        if latest_frame is None:
            await asyncio.sleep(0.1)
            continue
        try:
            snapshot = await crawler.wait_helper.get_dom_snapshot(latest_frame)
            # Menu metadata contains the authoritative SENTRY route. Live
            # dashboards update their DOM continuously, so a changed snapshot
            # alone must not be accepted while we are still on the old route.
            if expected_url and _matches_expected_route(
                latest_frame.url,
                expected_url,
            ):
                await crawler.wait_helper.wait_dom_ready(latest_frame)
                return latest_frame

            # Keep the old fallback only for menu entries that do not expose a
            # target URL. Otherwise an update on Top Reports can be mistaken
            # for navigation to Schedule Reports.
            if not expected_url and latest_frame.url != previous_url:
                await crawler.wait_helper.wait_dom_ready(latest_frame)
                return latest_frame
            if (
                not expected_url
                and previous_snapshot is not None
                and snapshot != previous_snapshot
            ):
                await crawler.wait_helper.wait_dom_ready(
                    latest_frame,
                    before_snapshot=previous_snapshot,
                )
                return latest_frame
            # The first menu can already be active after login. Accept an
            # unchanged frame only when its visible body explicitly identifies
            # the requested page; otherwise keep waiting for real navigation.
            if allow_unchanged and monotonic() - started >= 0.8 and expected_title:
                body_text = await latest_frame.locator("body").inner_text()
                if expected_title.casefold() in body_text.casefold():
                    await crawler.wait_helper.wait_dom_ready(latest_frame)
                    return latest_frame
        except Exception:
            pass
        await asyncio.sleep(0.1)

    raise RuntimeError("選單點擊後頁面內容未完成切換，停止擷取以避免跨頁污染")


async def _active_tab_name(frame):
    return str(await frame.evaluate("""
    () => {
        const active = document.querySelector(
            '.route_link a.router-link-exact-active,'
            + '.route_link a.active,'
            + '.route_link a[aria-selected="true"],'
            + '.route_link a[aria-current="page"]'
        );
        return active ? (active.innerText || active.textContent || '').trim() : '';
    }
    """) or "").strip()


async def _wait_for_tab_transition(
    frame,
    expected_tab,
    timeout_ms=8000,
):
    """Wait until the requested tab, rather than any live DOM update, is active."""

    deadline = monotonic() + timeout_ms / 1000
    last_active = ""
    while monotonic() < deadline:
        try:
            last_active = await _active_tab_name(frame)
            if last_active.casefold() == str(expected_tab).strip().casefold():
                # The active class can change one render tick before Vue swaps
                # the route content. Wait two frames, then stabilise the new
                # view. This avoids accepting live table-row updates from the
                # previously active History Logs tab as a successful switch.
                await frame.evaluate("""
                () => new Promise(resolve => requestAnimationFrame(
                    () => requestAnimationFrame(resolve)
                ))
                """)
                await crawler.wait_helper.wait_dom_ready(frame)
                if (
                    (await _active_tab_name(frame)).casefold()
                    == str(expected_tab).strip().casefold()
                ):
                    return
        except Exception:
            pass
        await asyncio.sleep(0.1)
    raise RuntimeError(
        f"Tab 點擊後未切換至 {expected_tab}（目前作用中：{last_active or '無'}），"
        "停止擷取以避免使用上一個 Tab"
    )


async def _visible_tab_names(frame, tabs):
    route_links = frame.locator(".route_link a")
    route_names = []
    try:
        for index in range(await route_links.count()):
            link = route_links.nth(index)
            if await link.is_visible():
                name = str(await link.inner_text()).strip()
                if name and name not in route_names:
                    route_names.append(name)
    except Exception:
        route_names = []

    if route_names:
        return route_names

    names = []
    for tab in tabs:
        name = str(tab.get("name") or "").strip()
        if not name or name in names:
            continue
        locator = frame.get_by_text(name, exact=True)
        try:
            if await locator.count() and await locator.first.is_visible():
                names.append(name)
        except Exception:
            continue
    return names


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
            previous_url = frame.url if frame else ""
            expected_url = str(menu_item.get("url") or "").strip()
            await link.click()

            frame = await _wait_for_page_transition(
                page,
                before_snapshot,
                previous_url,
                expected_url,
                title,
                index == 0,
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

            tab_names = await _visible_tab_names(frame, tabs)

            print(
                f"找到 {len(tabs)} 個 Tabs"
            )

            #
            # 有 Tabs
            #
            if tab_names:

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

                        locator = frame.locator(".route_link").get_by_text(
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

                        is_active = await locator.first.evaluate("""
                        element => element.classList.contains('router-link-exact-active')
                            || element.classList.contains('active')
                            || element.getAttribute('aria-selected') === 'true'
                            || element.getAttribute('aria-current') === 'page'
                        """)

                        if not is_active:
                            await locator.first.click()
                            await _wait_for_tab_transition(
                                frame,
                                tab_name,
                            )
                        else:
                            await crawler.wait_helper.wait_dom_ready(frame)

                        screenshot_capture = (
                            await save_screenshot(
                                frame,
                                f"{index}_{title}_{tab_index}_{tab_name}",
                                screenshot_dir
                            )
                        )
                        screenshot = screenshot_capture["path"]

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
                        try:
                            actions = await extract_actions(
                                frame,
                                title,
                                tab_name,
                                icon_dir,
                                screenshot_capture,
                                artifact_key=f"menu_{index}_tab_{tab_index}",
                            )
                        finally:
                            cleanup_screenshot_capture(screenshot_capture)
                        metadata = (
                            await analyze_page(

                                frame,

                                category,

                                title,

                                tab_name,

                                frame.url,

                                screenshot,

                                html_file,

                                screenshot_paths=screenshot_capture["paths"],

                                language=language,

                                page_key=f"menu:{index}/tab:{tab_index}",

                                menu_index=index,

                                tab_index=tab_index
                            )
                        )
                        metadata.actions = actions
                        metadata.interaction_flows = await explore_safe_actions(
                            frame,
                            actions,
                            title,
                            tab_name,
                            f"{output_root}/action_flows",
                            artifact_key=f"menu_{index}_tab_{tab_index}",
                        )

                        results.append(
                            metadata.model_dump()
                        )

                        print(
                            f"✅ 完成 Tab: {tab_name}"
                        )

                    except UnsafeInteractionState:
                        raise

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
            screenshot_capture = (
                await save_screenshot(
                    frame,
                    f"{index}_{title}",
                    screenshot_dir
                )
            )
            screenshot = screenshot_capture["path"]

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
            try:
                actions = await extract_actions(
                    frame,
                    title,
                    None,
                    icon_dir,
                    screenshot_capture,
                    artifact_key=f"menu_{index}",
                )
            finally:
                cleanup_screenshot_capture(screenshot_capture)

            metadata = (
                await analyze_page(

                    frame,

                    category,

                    title,

                    None,

                    frame.url,

                    screenshot,

                    html_file,

                    screenshot_paths=screenshot_capture["paths"],

                    language=language,

                    page_key=f"menu:{index}",

                    menu_index=index,

                    tab_index=None
                )
            )

            metadata.actions = actions
            metadata.interaction_flows = await explore_safe_actions(
                frame,
                actions,
                title,
                None,
                f"{output_root}/action_flows",
                artifact_key=f"menu_{index}",
            )
            results.append(
                metadata.model_dump()
            )

            print(
                f"✅ 完成: {title}"
            )

        except UnsafeInteractionState:
            raise

        except Exception as e:

            print(
                f"❌ 頁面失敗: {title}"
            )

            print(e)

    print(
        f"\n完成，共取得 {len(results)} 筆 Metadata"
    )

    return results
