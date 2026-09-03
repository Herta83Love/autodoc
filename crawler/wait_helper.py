"""Fast, bounded waits for SENTRY's SPA pages."""

import asyncio
import logging
from time import monotonic


logger = logging.getLogger(__name__)

DOM_SNAPSHOT_SCRIPT = r"""
() => {
    const body = document.body;
    if (!body) {
        return {ready: false, content: '', structure: '', pending_images: 0, loading: 1};
    }
    const isVisible = (element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden'
            && rect.width > 0 && rect.height > 0;
    };
    const text = (body.innerText || '').replace(/\s+/g, ' ').trim();
    const elements = body.querySelectorAll('*');
    const pendingImages = Array.from(body.images || []).filter(image => !image.complete).length;
    const loadingSelectors = [
        '[aria-busy="true"]', '.loading', '.loader', '.spinner',
        '.progress-overlay', '.v-overlay--active'
    ];
    const loading = loadingSelectors.reduce((count, selector) => {
        return count + Array.from(body.querySelectorAll(selector)).filter(isVisible).length;
    }, 0);
    const interactive = body.querySelectorAll(
        'input, select, textarea, button, table, canvas, svg'
    ).length;
    return {
        ready: document.readyState !== 'loading' && elements.length > 0,
        content: `${location.href}|${text.slice(0, 1200)}`,
        structure: `${elements.length}|${interactive}|${body.children.length}`,
        pending_images: pendingImages,
        loading
    };
}
"""


async def get_dom_snapshot(frame):
    return await frame.evaluate(DOM_SNAPSHOT_SCRIPT)


async def wait_dom_ready(
    frame,
    before_snapshot=None,
    timeout_ms=8000,
    change_timeout_ms=2500,
    stable_rounds=3,
    interval=0.15
):
    """Continue as soon as the new page has a usable, stable DOM."""
    started = monotonic()
    deadline = started + timeout_ms / 1000
    change_deadline = started + min(change_timeout_ms, timeout_ms) / 1000
    previous_structure = None
    stable_count = 0
    content_changed = before_snapshot is None

    try:
        await frame.locator("body").wait_for(
            state="visible",
            timeout=min(timeout_ms, 2500)
        )
    except Exception as exc:
        logger.debug("等待 frame body 顯示失敗：%s", exc)

    while monotonic() < deadline:
        try:
            snapshot = await get_dom_snapshot(frame)
            if before_snapshot is not None and (
                snapshot.get("content") != before_snapshot.get("content")
            ):
                content_changed = True

            usable = (
                snapshot.get("ready")
                and snapshot.get("pending_images", 0) == 0
                and snapshot.get("loading", 0) == 0
            )
            if not content_changed and monotonic() >= change_deadline:
                content_changed = True

            structure = snapshot.get("structure")
            if usable and content_changed and structure == previous_structure:
                stable_count += 1
            elif usable and content_changed:
                stable_count = 1
            else:
                stable_count = 0

            if stable_count >= stable_rounds:
                elapsed = monotonic() - started
                print(f"✅ DOM 已就緒並穩定（{elapsed:.2f} 秒）")
                return True
            previous_structure = structure
        except Exception as exc:
            logger.debug("讀取 DOM 狀態失敗：%s", exc)
            stable_count = 0

        await asyncio.sleep(interval)

    print(f"⚠️ DOM 等待逾時（{timeout_ms / 1000:.1f} 秒），繼續擷取")
    return False


async def wait_frame_ready(frame, timeout_ms=8000):
    return await wait_dom_ready(frame, timeout_ms=timeout_ms)


async def wait_page_content_change(frame, before_text, timeout=3):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        try:
            current_text = await frame.locator("body").inner_text()
            if current_text and current_text != before_text:
                return True
        except Exception as exc:
            logger.debug("等待頁面內容變更時讀取失敗：%s", exc)
        await asyncio.sleep(0.15)
    return False


async def wait_dom_stable(frame, stable_rounds=3, interval=0.15):
    return await wait_dom_ready(
        frame,
        stable_rounds=stable_rounds,
        interval=interval
    )
