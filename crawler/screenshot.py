"""Capture representative viewport segments while scrolling through an iframe."""

import re
import shutil
import tempfile
from pathlib import Path


SCROLL_PLAN_SCRIPT = """
() => {
    const root = document.scrollingElement || document.documentElement;
    const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
    const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
    const rootMax = Math.max(0, root.scrollHeight - viewportHeight);

    const candidates = Array.from(document.querySelectorAll('*'))
        .map((element, index) => {
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            const maxScroll = Math.max(0, element.scrollHeight - element.clientHeight);
            const overflow = `${style.overflowY} ${style.overflow}`;
            return {element, index, rect, style, maxScroll, overflow};
        })
        .filter(item => item.maxScroll > 4
            && item.rect.width >= viewportWidth * 0.35
            && item.rect.height >= Math.min(120, viewportHeight * 0.2)
            && item.rect.right > 0
            && item.rect.left < viewportWidth
            && item.rect.bottom > 0
            && item.rect.top < viewportHeight
            && item.style.display !== 'none'
            && item.style.visibility !== 'hidden'
            && /(auto|scroll|hidden|clip)/.test(item.overflow));

    candidates.sort((a, b) =>
        (b.maxScroll * b.rect.width) - (a.maxScroll * a.rect.width)
    );
    const inner = candidates[0];
    const innerScore = inner ? inner.maxScroll * inner.rect.width : 0;
    const rootScore = rootMax * viewportWidth;

    if (inner && innerScore > rootScore * 1.05) {
        const token = `autodoc-scroll-${Date.now()}-${Math.random()}`;
        inner.element.setAttribute('data-autodoc-scroll-target', token);
        return {
            type: 'element',
            token,
            originalTop: inner.element.scrollTop,
            maxScroll: inner.maxScroll,
            step: inner.element.clientHeight,
            rect: {
                x: inner.rect.left,
                y: inner.rect.top,
                width: inner.rect.width,
                height: inner.rect.height
            },
            viewport: {width: viewportWidth, height: viewportHeight}
        };
    }

    return {
        type: 'document',
        token: null,
        originalTop: root.scrollTop || window.scrollY || 0,
        maxScroll: rootMax,
        step: viewportHeight,
        rect: {x: 0, y: 0, width: viewportWidth, height: viewportHeight},
        viewport: {width: viewportWidth, height: viewportHeight}
    };
}
"""


SET_SCROLL_SCRIPT = """
({type, token, top}) => {
    if (type === 'element') {
        const element = document.querySelector(
            `[data-autodoc-scroll-target="${CSS.escape(token)}"]`
        );
        if (element) element.scrollTop = top;
    } else {
        const root = document.scrollingElement || document.documentElement;
        root.scrollTop = top;
        window.scrollTo(0, top);
    }
}
"""


RESTORE_SCROLL_SCRIPT = """
({type, token, top}) => {
    if (type === 'element') {
        const element = document.querySelector(
            `[data-autodoc-scroll-target="${CSS.escape(token)}"]`
        );
        if (element) {
            element.scrollTop = top;
            element.removeAttribute('data-autodoc-scroll-target');
        }
    } else {
        const root = document.scrollingElement || document.documentElement;
        root.scrollTop = top;
        window.scrollTo(0, top);
    }
}
"""


VISIBLE_BUTTONS_SCRIPT = """
() => {
    const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
    const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
    return Array.from(document.querySelectorAll('button')).map((button, index) => {
        const rect = button.getBoundingClientRect();
        const style = window.getComputedStyle(button);
        const iconNode = button.querySelector('i, svg');
        const label = (button.textContent || '').trim();
        const classTokens = new Set(
            (button.getAttribute('class') || '').toLowerCase().split(/\s+/).filter(Boolean)
        );
        const contextRoot = button.closest(
            '.content_box,.operation-conf-block,.chartWindow,.mazi-table,.contentBlock'
        );
        const headingNode = contextRoot && contextRoot.querySelector(
            ':scope > .title,:scope > .sub_title,:scope > h1,:scope > h2,:scope > h3'
        );
        let visible = style.display !== 'none'
            && style.visibility !== 'hidden'
            && Number(style.opacity || 1) > 0
            && rect.width > 0
            && rect.height > 0
            && rect.right > 0
            && rect.left < viewportWidth
            && rect.bottom > 0
            && rect.top < viewportHeight;

        for (let parent = button.parentElement; visible && parent; parent = parent.parentElement) {
            const parentStyle = window.getComputedStyle(parent);
            if (parentStyle.display === 'none'
                || parentStyle.visibility === 'hidden'
                || Number(parentStyle.opacity || 1) === 0
                || parent.getAttribute('aria-hidden') === 'true') {
                visible = false;
            }

            const overflow = `${parentStyle.overflowX} ${parentStyle.overflowY}`;
            if (visible && /(auto|scroll|hidden|clip)/.test(overflow)) {
                const parentRect = parent.getBoundingClientRect();
                if (rect.right <= parentRect.left || rect.left >= parentRect.right
                    || rect.bottom <= parentRect.top || rect.top >= parentRect.bottom) {
                    visible = false;
                }
            }
        }

        // SENTRY also uses <button> for full-width date bands and tiny
        // accessibility-only table sort controls. Those are not operation
        // icons and produce 1000px-wide strips or 4px-high lines when cropped.
        const maxDocumentableWidth = Math.min(420, viewportWidth * 0.5);
        const isFormControl = ['disabled', 'picking', 'page-tag', 'laptop']
            .some(token => classTokens.has(token))
            || /^sort table by\b/i.test(label)
            || (!iconNode && rect.width / Math.max(1, rect.height) >= 2
                && !classTokens.has('detail-button'));
        const documentable = visible
            && rect.top >= 0
            && rect.bottom <= viewportHeight
            && rect.width >= 12
            && rect.height >= 12
            && rect.width <= maxDocumentableWidth
            && !isFormControl
            && Boolean(iconNode || label);

        return {
            index,
            text: label,
            title: (button.getAttribute('title') || '').trim(),
            aria: (button.getAttribute('aria-label') || '').trim(),
            icon: iconNode ? (iconNode.getAttribute('class') || '') : '',
            buttonClass: button.getAttribute('class') || '',
            contextHeading: headingNode ? (headingNode.innerText || '').trim() : '',
            contextText: contextRoot
                ? (contextRoot.innerText || '').trim().slice(0, 500)
                : '',
            visible,
            documentable,
            box: {x: rect.left, y: rect.top, width: rect.width, height: rect.height}
        };
    }).filter(button => button.documentable);
}
"""


def _scroll_positions(max_scroll, step):
    max_scroll = max(0, int(round(max_scroll)))
    step = max(1, int(round(step)))
    positions = [0]
    while positions[-1] < max_scroll:
        positions.append(min(max_scroll, positions[-1] + step))
    return positions


async def _capture_frame_viewport(frame, path):
    """Capture exactly the visible iframe area instead of its clipped body."""
    page = frame.page
    try:
        frame_element = await frame.frame_element()
        box = await frame_element.bounding_box()
    except Exception:
        box = None

    if box:
        viewport = page.viewport_size
        if viewport:
            left = max(0, box['x'])
            top = max(0, box['y'])
            right = min(viewport['width'], box['x'] + box['width'])
            bottom = min(viewport['height'], box['y'] + box['height'])
            if right > left and bottom > top:
                await page.screenshot(
                    path=str(path),
                    clip={
                        'x': left,
                        'y': top,
                        'width': right - left,
                        'height': bottom - top
                    },
                    animations='disabled',
                    caret='hide'
                )
                return

    await frame.locator('body').screenshot(
        path=str(path),
        animations='disabled',
        caret='hide'
    )


def _representative_indexes(segment_count, title, limit=4):
    normalized = str(title).lower()
    is_tld_page = (
        'tld' in normalized
        or 'top_level_domain' in normalized
        or '頂級網域' in title
        or '頂級域名' in title
    )
    if is_tld_page or segment_count <= 1:
        return {0}
    if segment_count <= limit:
        return set(range(segment_count))

    # Keep evenly distributed views so long configuration pages retain both
    # their first and last sections without sending every viewport to the VLM.
    return {
        round(index * (segment_count - 1) / (limit - 1))
        for index in range(limit)
    }


def cleanup_screenshot_capture(capture):
    temporary_dir = capture.get('temporary_dir') if capture else None
    if temporary_dir:
        shutil.rmtree(temporary_dir, ignore_errors=True)


async def save_screenshot(frame, title, output_dir='output/screenshots'):
    safe_title = re.sub(r'[^a-zA-Z0-9_]', '_', title)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plan = await frame.evaluate(SCROLL_PLAN_SCRIPT)
    positions = _scroll_positions(plan['maxScroll'], plan['step'])
    representative_indexes = _representative_indexes(len(positions), title)
    temporary_dir = Path(tempfile.mkdtemp(prefix='autodoc_segments_'))
    segments = []
    screenshots = []

    try:
        try:
            for segment_index, top in enumerate(positions):
                await frame.evaluate(SET_SCROLL_SCRIPT, {
                    'type': plan['type'],
                    'token': plan['token'],
                    'top': top
                })
                await frame.evaluate("""
                () => new Promise(resolve => requestAnimationFrame(
                    () => requestAnimationFrame(resolve)
                ))
                """)
                if segment_index in representative_indexes:
                    segment_path = output_path / f'{safe_title}_{segment_index}.png'
                    screenshots.append(str(segment_path))
                    temporary = False
                else:
                    segment_path = temporary_dir / f'{safe_title}_{segment_index}.png'
                    temporary = True

                await _capture_frame_viewport(frame, segment_path)
                segments.append({
                    'top': top,
                    'path': str(segment_path),
                    'temporary': temporary,
                    'buttons': await frame.evaluate(VISIBLE_BUTTONS_SCRIPT)
                })
        finally:
            await frame.evaluate(RESTORE_SCROLL_SCRIPT, {
                'type': plan['type'],
                'token': plan['token'],
                'top': plan['originalTop']
            })
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise

    print(
        f"📷 分段頁面截圖：實際捲動 {len(segments)} 段，"
        f"保留 {len(screenshots)} 張供 AI 分析"
    )
    return {
        'path': screenshots[0],
        'paths': screenshots,
        'plan': plan,
        'segments': segments,
        'temporary_dir': str(temporary_dir)
    }
