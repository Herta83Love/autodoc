"""Extract button metadata and crop all icons from one page screenshot."""

import io
import re
from pathlib import Path
from time import monotonic

from PIL import Image


BUTTON_DATA_SCRIPT = """
buttons => {
    const body = document.body;
    const bodyRect = body.getBoundingClientRect();
    return buttons.map((button, index) => {
        const rect = button.getBoundingClientRect();
        const style = window.getComputedStyle(button);
        const iconNode = button.querySelector('i, svg');
        const visible = style.display !== 'none'
            && style.visibility !== 'hidden'
            && Number(style.opacity || 1) > 0
            && rect.width > 0 && rect.height > 0;
        return {
            index,
            text: (button.textContent || '').trim(),
            title: (button.getAttribute('title') || '').trim(),
            aria: (button.getAttribute('aria-label') || '').trim(),
            icon: iconNode ? (iconNode.getAttribute('class') || '') : '',
            visible,
            box: {
                x: rect.left - bodyRect.left,
                y: rect.top - bodyRect.top,
                width: rect.width,
                height: rect.height
            },
            body: {width: bodyRect.width, height: bodyRect.height}
        };
    });
}
"""


def safe_filename(value):
    return re.sub(r"[^a-zA-Z0-9_]", "_", str(value or ""))


def crop_button(source, button, image_path, padding_css=3):
    box = button["box"]
    body = button["body"]
    if body["width"] <= 0 or body["height"] <= 0:
        return False

    scale_x = source.width / body["width"]
    scale_y = source.height / body["height"]
    padding_x = padding_css * scale_x
    padding_y = padding_css * scale_y
    left = max(0, round(box["x"] * scale_x - padding_x))
    top = max(0, round(box["y"] * scale_y - padding_y))
    right = min(source.width, round((box["x"] + box["width"]) * scale_x + padding_x))
    bottom = min(source.height, round((box["y"] + box["height"]) * scale_y + padding_y))

    if right <= left or bottom <= top:
        return False

    source.crop((left, top, right, bottom)).save(image_path, format="PNG")
    return image_path.is_file()


async def open_page_screenshot(frame, screenshot_path=None):
    if screenshot_path and Path(screenshot_path).is_file():
        with Image.open(screenshot_path) as image:
            return image.convert("RGB")

    buffer = await frame.locator("body").screenshot(
        animations="disabled",
        caret="hide"
    )
    with Image.open(io.BytesIO(buffer)) as image:
        return image.convert("RGB")


async def extract_actions(
    frame,
    page_name,
    tab_name=None,
    output_dir="output/icons",
    screenshot_path=None
):
    started = monotonic()
    icon_dir = Path(output_dir)
    icon_dir.mkdir(parents=True, exist_ok=True)

    try:
        buttons = await frame.locator("button").evaluate_all(BUTTON_DATA_SCRIPT)
    except Exception as exc:
        print(f"⚠️ 按鈕資料擷取失敗：{exc}")
        return []

    candidates = []
    for button in buttons:
        label = button["text"] or button["title"] or button["aria"]
        if button["visible"] and (label or button["icon"]):
            button["label"] = label
            candidates.append(button)

    if not candidates:
        return []

    try:
        source = await open_page_screenshot(frame, screenshot_path)
    except Exception as exc:
        print(f"⚠️ 頁面截圖無法用於按鈕裁切：{exc}")
        return []

    safe_page = safe_filename(page_name)
    safe_tab = safe_filename(tab_name)
    actions = []
    for button in candidates:
        image_path = icon_dir / f"{safe_page}_{safe_tab}_{button['index']}.png"
        try:
            saved = crop_button(source, button, image_path)
        except Exception as exc:
            print(f"⚠️ 按鈕圖片裁切失敗：{image_path}：{exc}")
            saved = False

        if saved:
            actions.append({
                "label": button["label"],
                "icon": button["icon"],
                "image": str(image_path)
            })

    source.close()
    elapsed = monotonic() - started
    print(
        f"✅ 按鈕圖片已由單張頁面截圖裁切："
        f"{len(actions)}/{len(candidates)} 張（{elapsed:.2f} 秒）"
    )
    return actions
