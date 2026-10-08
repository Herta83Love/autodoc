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
    // SENTRY hides the checkbox for both controls. #mazi-switch is an on/off
    // toggle. .mazi-switch-pick is a two-choice selector such as Type.
    const switchWidget = control => control.closest(
        '[id="mazi-switch"], .mazi-switch-pick'
    );
    const switchOptions = widget => {
        const values = [];
        widget.querySelectorAll('p').forEach(node => {
            const value = (node.innerText || '').replace(/\\s+/g, ' ').trim();
            if (value && !values.includes(value)) values.push(value);
        });
        return values;
    };
    const fields = Array.from(root.querySelectorAll('input,select,textarea'))
        .filter(control => {
            if (control.type === 'hidden') return false;
            const widget = switchWidget(control);
            return visible(widget || control);
        })
        .map(control => {
            const widget = switchWidget(control);
            const item = control.closest(
                '.operation-conf-item,.form-group,.field-group,.input-group'
            );
            const block = item && item.closest('.operation-conf-block');
            const sectionNode = block && block.querySelector(':scope > .title');
            const section = sectionNode ? (sectionNode.innerText || '').trim() : '';
            let label = '';
            if (item) {
                const labelNode = Array.from(
                    item.querySelectorAll('.field,.label,.sub_title,label')
                ).find(node => !widget || !widget.contains(node));
                if (labelNode) label = (labelNode.innerText || '').trim();
            }
            if (!label && control.id && !widget) {
                const associated = document.querySelector(
                    `label[for="${CSS.escape(control.id)}"]`
                );
                if (associated) label = (associated.innerText || '').trim();
            }
            label = label || (control.getAttribute('aria-label') || '').trim();
            const options = widget
                ? switchOptions(widget)
                : control.tagName === 'SELECT'
                ? Array.from(control.options)
                    .map(option => (option.textContent || '').trim()).filter(Boolean)
                : [];
            return {
                section,
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


# These controls write or reset the live configuration. 套用 is the SENTRY
# button that commits DNS and system settings immediately.
_COMMIT_LABELS = {
    "apply",
    "套用",
    "save",
    "儲存",
    "submit",
    "確認",
    "confirm",
    "default",
    "預設",
}
_COMMIT_CLASSES = {"btn-confirm", "btn-default"}


def _is_commit_label(value):
    text = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    return text in _COMMIT_LABELS


def _is_safe_add_action(action):
    classes = str(action.get("button_class") or "").lower().split()
    icon = str(action.get("icon") or "").lower()
    label = str(action.get("label") or action.get("text") or "").strip()
    if (
        _is_commit_label(label)
        or _is_commit_label(action.get("aria"))
        or _is_commit_label(action.get("title"))
        or _COMMIT_CLASSES.intersection(classes)
    ):
        return False
    return (
        "plus" in classes
        or "fa-plus" in icon
        or label.casefold() in {"add", "new", "新增", "建立"}
    )


async def _commits_settings(button):
    """Return True when this live control would change saved settings."""

    try:
        text = await button.inner_text()
        aria = await button.get_attribute("aria-label")
        title = await button.get_attribute("title")
        classes = (await button.get_attribute("class") or "").lower().split()
    except Exception:
        return True
    if _COMMIT_CLASSES.intersection(classes):
        return True
    return any(_is_commit_label(value) for value in (text, aria, title))


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
            locator = frame.get_by_role("button", name=text, exact=True)
            for index in range(await locator.count()):
                item = locator.nth(index)
                if not await item.is_visible() or await _commits_settings(item):
                    continue
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


def _distinguish_address_prefix(fields):
    """Keep an address and its prefix length as two fields.

    Secondary IP forms label both the address box and the /24 selector as Address.
    """

    previous_label = ""
    distinguished = []
    for field in fields or []:
        copied = dict(field)
        label = str(copied.get("label") or "").strip()
        options = [str(option).strip() for option in copied.get("options") or []]
        control_type = str(copied.get("type") or "").lower()
        prefix_choice = any(option.startswith("/") for option in options)
        if label and label == previous_label and (prefix_choice or control_type == "select-one" or control_type == "select"):
            copied["label"] = "Prefix" if label[:1].isascii() else "前綴"
        previous_label = label
        distinguished.append(copied)
    return distinguished


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
            if await _commits_settings(button):
                print(f"略過會寫入設定的按鈕：{page_name} {action_id}")
                continue
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
                    "fields": _distinguish_address_prefix(form.get("fields", [])),
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
