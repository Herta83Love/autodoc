"""Discover explanatory content hidden behind safe, read-only UI interactions."""

import asyncio
import re
from pathlib import Path

from crawler.screenshot import cleanup_screenshot_capture, save_screenshot


VISUAL_SECTIONS_SCRIPT = r"""
() => {
    const visible = element => {
        if (!element) return false;
        for (let node = element; node; node = node.parentElement) {
            const style = window.getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden'
                || Number(style.opacity || 1) === 0) return false;
        }
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    };
    const text = element => element ? (element.innerText || '').trim() : '';
    const results = [];
    const seen = new Set();
    const add = (title, description, kind) => {
        title = String(title || '').trim();
        description = String(description || '').trim();
        if (!title || title.length > 120) return;
        const key = `${title.toLowerCase()}\n${description.toLowerCase()}`;
        if (seen.has(key)) return;
        seen.add(key);
        results.push({title, description, kind});
    };

    // Dashboard chart headers retain their authoritative explanation even
    // though the plotted series themselves are rendered to canvas/SVG.
    document.querySelectorAll('.header-section').forEach(header => {
        if (!visible(header)) return;
        const title = text(header.querySelector('.title,h1,h2,h3,h4'));
        const description = text(
            header.querySelector('.description,.desc,.subtitle,.sub_title')
        ) || Array.from(header.querySelectorAll('p'))
            .map(text).filter(value => value && value !== title).join(' ');
        add(title, description, 'chart');
    });

    // Risk dashboards use phase cards and detail blocks whose descriptions
    // explain what each metric represents.
    document.querySelectorAll('.phase-of-cyber-attack .summary > *, .detail-block')
        .forEach(block => {
            if (!visible(block)) return;
            const title = text(block.querySelector(
                '.event-header .title,.title,h1,h2,h3,h4'
            ));
            const description = text(block.querySelector(
                '.event-header .description,.description,.desc,.subtitle,.sub_title'
            ));
            add(title, description, 'metric');
        });

    // Generic fallback for other pages with charts. Limit extraction to the
    // nearest semantic panel and never treat raw chart values as instructions.
    document.querySelectorAll('canvas,svg').forEach(graphic => {
        if (!visible(graphic)) return;
        const block = graphic.closest(
            '.chartWindow,.content_box,.contentBlock,.traffic,.connection'
        );
        if (!block) return;
        const title = text(block.querySelector(
            '.header-section .title,:scope > .title,:scope > h1,:scope > h2,:scope > h3'
        ));
        const description = text(block.querySelector(
            '.header-section .description,:scope > .description,:scope > .desc'
        ));
        add(title, description, 'chart');
    });

    return results;
}
"""


DETAIL_FIELDS_SCRIPT = r"""
() => {
    const panel = document.querySelector('.log-detail.show');
    if (!panel) return null;
    const fields = Array.from(panel.querySelectorAll('.detail .data')).map(item => {
        const label = item.querySelector('.field');
        const value = item.querySelector('.value');
        return {
            label: label ? (label.innerText || '').trim() : '',
            sample_value: value ? (value.innerText || '').trim() : ''
        };
    }).filter(item => item.label);
    const heading = panel.querySelector('.title,.header,h1,h2,h3');
    return {
        title: heading ? (heading.innerText || '').trim() : '',
        fields
    };
}
"""


async def extract_visual_sections(frame):
    """Return titles and authoritative descriptions for charts/metric cards."""

    return await frame.evaluate(VISUAL_SECTIONS_SCRIPT)


async def _wait_for_detail_panel(frame, timeout_ms=3000):
    steps = max(1, timeout_ms // 100)
    for _ in range(steps):
        if await frame.locator(".log-detail.show").count():
            return True
        await asyncio.sleep(0.1)
    return False


async def _close_detail_panel(frame):
    selectors = (
        ".log-detail.show .fa-times",
        ".log-detail.show .close",
        ".log-detail.show [aria-label='Close']",
        ".log-detail.show [aria-label='關閉']",
    )
    for selector in selectors:
        locator = frame.locator(selector)
        if await locator.count():
            try:
                await locator.first.click(timeout=1500)
                for _ in range(15):
                    if not await frame.locator(".log-detail.show").count():
                        return True
                    await asyncio.sleep(0.1)
            except Exception:
                continue

    try:
        await frame.page.keyboard.press("Escape")
        for _ in range(10):
            if not await frame.locator(".log-detail.show").count():
                return True
            await asyncio.sleep(0.1)
    except Exception:
        pass
    return False


async def explore_readonly_details(
    frame,
    page_name,
    tab_name=None,
    output_dir="output/detail_flows",
    artifact_key=None,
):
    """Open one representative log row, record its field schema, then close it."""

    if not await frame.locator(".log-detail").count():
        return []

    rows = frame.locator(
        ".mazi-table-log table.log-list tbody "
        "tr:not(.table-log-search)"
    )
    row_count = await rows.count()
    if not row_count:
        return []

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_page = re.sub(r"[^a-zA-Z0-9_]", "_", str(page_name or "page"))
    safe_tab = re.sub(r"[^a-zA-Z0-9_]", "_", str(tab_name or ""))
    safe_artifact = re.sub(r"[^a-zA-Z0-9_]", "_", str(artifact_key or ""))
    capture_prefix = safe_artifact or f"{safe_page}_{safe_tab}"

    for row_index in range(min(row_count, 5)):
        row = rows.nth(row_index)
        try:
            if not await row.is_visible() or not (await row.inner_text()).strip():
                continue
            await row.scroll_into_view_if_needed(timeout=1500)
            await row.click(timeout=2000)
            if not await _wait_for_detail_panel(frame):
                continue

            details = await frame.evaluate(DETAIL_FIELDS_SCRIPT)
            if not details or not details.get("fields"):
                continue

            capture = await save_screenshot(
                frame,
                f"{capture_prefix}_record_details",
                output_dir,
            )
            try:
                details["screenshots"] = capture.get("paths", [])
            finally:
                cleanup_screenshot_capture(capture)
            return [details]
        except Exception as exc:
            print(f"⚠️ 無法探索 {page_name} 的資料列明細：{exc}")
        finally:
            if not await _close_detail_panel(frame):
                print(f"⚠️ {page_name} 的明細面板無法關閉，停止後續明細探索")
                break

    return []
