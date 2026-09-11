"""Safely inspect forms opened by non-mutating add buttons."""

import asyncio
import json
import re
from pathlib import Path
from time import monotonic

from crawler.screenshot import cleanup_screenshot_capture, save_screenshot


class UnsafeInteractionState(RuntimeError):
    """Raised when an explored form cannot be closed without submitting."""


STATE_SCRIPT = """
() => {
    const activeRoute = document.querySelector('.route_link .router-link-exact-active');
    const visibleDialogs = Array.from(document.querySelectorAll(
        '[role="dialog"],.modal,.dialog,.drawer'
    )).filter(element => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden'
            && Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
    });
    const root = visibleDialogs[0]
        || document.querySelector('.route_view') || document.body;
    const titleNode = root.querySelector(
        '.modal-title,.dialog-title,.title,h1,h2,h3'
    );
    return JSON.stringify({
        href: location.href,
        activeRoute: activeRoute ? (activeRoute.innerText || '').trim() : '',
        dialogs: visibleDialogs.length,
        controls: document.querySelectorAll('input,select,textarea').length,
        title: titleNode ? (titleNode.innerText || '').trim() : ''
    });
}
"""


FORM_SCRIPT = """
() => {
    const visible = element => {
        for (let node = element; node; node = node.parentElement) {
            const style = window.getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden'
                || Number(style.opacity || 1) === 0) return false;
        }
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    };
    const dialog = Array.from(document.querySelectorAll(
        '[role="dialog"],.modal,.dialog,.drawer'
    )).find(visible);
    const root = dialog || document.querySelector('.route_view') || document.body;
    const titleNode = root.querySelector(
        '.modal-title,.dialog-title,.title,h1,h2,h3'
    );
    const fields = Array.from(root.querySelectorAll('input,select,textarea'))
        .filter(control => control.type !== 'hidden' && visible(control))
        .map(control => {
            const item = control.closest(
                '.operation-conf-item,.form-group,.field-group,.input-group'
            );
            let label = '';
            if (item) {
                const labelNode = item.querySelector('.field,label,.label,.sub_title');
                if (labelNode) label = (labelNode.innerText || '').trim();
            }
            if (!label && control.id) {
                const associated = document.querySelector(
                    `label[for="${CSS.escape(control.id)}"]`
                );
                if (associated) label = (associated.innerText || '').trim();
            }
            label = label || (control.getAttribute('aria-label') || '').trim();
            const options = control.tagName === 'SELECT'
                ? Array.from(control.options)
                    .map(option => (option.textContent || '').trim()).filter(Boolean)
                : [];
            return {
                label,
                internal_name: control.name || control.id || '',
                type: (control.type || control.tagName).toLowerCase(),
                required: control.required || control.getAttribute('aria-required') === 'true',
                placeholder: (control.getAttribute('placeholder') || '').trim(),
                inputmode: (control.getAttribute('inputmode') || '').trim(),
                min: (control.getAttribute('min') || '').trim(),
                max: (control.getAttribute('max') || '').trim(),
                step: (control.getAttribute('step') || '').trim(),
                accept: (control.getAttribute('accept') || '').trim(),
                options
            };
        })
        .filter(field => field.label);
    return {
        title: titleNode ? (titleNode.innerText || '').trim() : '',
        kind: dialog ? 'dialog' : 'page',
        fields
    };
}
"""


def _is_safe_add_action(action):
    classes = str(action.get("button_class") or "").lower().split()
    icon = str(action.get("icon") or "").lower()
    label = str(action.get("label") or "").lower()
    return (
        "plus" in classes
        or "fa-plus" in icon
        or label in {"add", "new", "新增", "建立"}
    )


def _decode_state(value):
    try:
        return json.loads(value)
    except Exception:
        return {}


def _state_changed(before, current):
    before_data = _decode_state(before)
    current_data = _decode_state(current)
    keys = ("href", "activeRoute", "dialogs", "controls", "title")
    return any(before_data.get(key) != current_data.get(key) for key in keys)


def _state_restored(before, current):
    before_data = _decode_state(before)
    current_data = _decode_state(current)
    return (
        before_data.get("href") == current_data.get("href")
        and before_data.get("activeRoute") == current_data.get("activeRoute")
        and current_data.get("dialogs", 0) <= before_data.get("dialogs", 0)
    )


async def _wait_for_restored_state(frame, before, timeout_ms=8000):
    deadline = monotonic() + timeout_ms / 1000
    while monotonic() < deadline:
        try:
            current = await frame.evaluate(STATE_SCRIPT)
            if _state_restored(before, current):
                return True
        except Exception:
            # A hash-route change or reload can briefly destroy the execution
            # context. The Frame object remains usable after navigation.
            pass
        await asyncio.sleep(0.1)
    return False


async def _wait_for_state_change(frame, before, timeout_ms=6000):
    deadline = monotonic() + timeout_ms / 1000
    while monotonic() < deadline:
        try:
            current = await frame.evaluate(STATE_SCRIPT)
            if _state_changed(before, current):
                await asyncio.sleep(0.15)
                return current
        except Exception:
            pass
        await asyncio.sleep(0.1)
    return None


async def _restore_state(frame, before):
    # Escape closes most dialogs without submitting them.
    try:
        await frame.page.keyboard.press("Escape")
        if await _wait_for_restored_state(frame, before, timeout_ms=800):
            return True
    except Exception:
        pass

    for text in ("Cancel", "Close", "取消", "關閉"):
        try:
            locator = frame.get_by_text(text, exact=True)
            for index in range(await locator.count()):
                item = locator.nth(index)
                if await item.is_visible():
                    await item.click()
                if await _wait_for_restored_state(frame, before, timeout_ms=1200):
                    return True
        except Exception:
            continue

    # Configuration pages usually use an iframe-local hash route. Going back
    # inside that frame is non-mutating and avoids clicking Save/Apply.
    try:
        await frame.evaluate("history.back()")
        if await _wait_for_restored_state(frame, before, timeout_ms=2500):
            return True
    except Exception:
        pass

    # Some SENTRY add pages replace the iframe hash instead of pushing a
    # usable browser-history entry. Restore the exact pre-click iframe URL.
    # If the URL never changed (for example an unrecognised modal), reload the
    # current route to discard the unsaved form without clicking Save/Apply.
    before_data = _decode_state(before)
    target_href = str(before_data.get("href") or "").strip()
    if target_href:
        try:
            await frame.evaluate(
                """
                target => {
                    if (location.href === target) location.reload();
                    else location.replace(target);
                }
                """,
                target_href,
            )
        except Exception:
            # Expected when location.reload/replace destroys this execution
            # context before Playwright receives the return value.
            pass
        if await _wait_for_restored_state(frame, before, timeout_ms=10000):
            return True

    return False


async def explore_safe_actions(
    frame,
    actions,
    page_name,
    tab_name=None,
    output_dir="output/action_flows",
    artifact_key=None,
):
    """Open add forms, capture their fields, then return without saving."""

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    flows = []
    safe_page = re.sub(r"[^a-zA-Z0-9_]", "_", str(page_name or "page"))
    safe_tab = re.sub(r"[^a-zA-Z0-9_]", "_", str(tab_name or ""))
    safe_artifact = re.sub(
        r"[^a-zA-Z0-9_]",
        "_",
        str(artifact_key or ""),
    )
    capture_prefix = safe_artifact or f"{safe_page}_{safe_tab}"

    for action in actions:
        if not _is_safe_add_action(action):
            continue
        dom_index = action.get("dom_index")
        if not isinstance(dom_index, int):
            continue

        before = await frame.evaluate(STATE_SCRIPT)
        action_id = str(action.get("action_id") or f"button-{dom_index}")
        try:
            button = frame.locator("button").nth(dom_index)
            await button.scroll_into_view_if_needed(timeout=2000)
            await button.click(timeout=3000)
            changed = await _wait_for_state_change(frame, before)
            if not changed:
                continue

            form = await frame.evaluate(FORM_SCRIPT)
            capture = await save_screenshot(
                frame,
                f"{capture_prefix}_{action_id}_form",
                output_dir,
            )
            try:
                flows.append({
                    "action_id": action_id,
                    "context_heading": action.get("context_heading", ""),
                    "type": form.get("kind", "page"),
                    "title": form.get("title", ""),
                    "screenshots": capture.get("paths", []),
                    "fields": form.get("fields", []),
                })
            finally:
                cleanup_screenshot_capture(capture)
        except Exception as exc:
            print(f"⚠️ 無法探索 {page_name} {action_id}：{exc}")
        finally:
            restored = await _restore_state(frame, before)
            if not restored:
                try:
                    current = await frame.evaluate(STATE_SCRIPT)
                except Exception as exc:
                    current = f"無法讀取目前狀態：{exc}"
                print(f"⚠️ 互動前狀態: {before}")
                print(f"⚠️ 返回後狀態: {current}")
                raise UnsafeInteractionState(
                    f"探索 {page_name} {action_id} 後無法安全返回原頁面"
                )

    return flows
