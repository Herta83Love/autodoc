# ============================================================================
# File: screenshot.py
# ============================================================================

import re
from pathlib import Path


async def save_screenshot(
    frame,
    title,
    output_dir="output/screenshots"
):

    safe_title = re.sub(
        r'[^a-zA-Z0-9_]',
        '_',
        title
    )

    path = (
        f"{output_dir}/"
        f"{safe_title}.png"
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    await frame.locator("body").screenshot(
        path=path
    )

    return path
