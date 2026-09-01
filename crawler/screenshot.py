# ============================================================================
# File: screenshot.py
# ============================================================================

import re


async def save_screenshot(
    frame,
    title
):

    safe_title = re.sub(
        r'[^a-zA-Z0-9_]',
        '_',
        title
    )

    path = (
        f"output/screenshots/"
        f"{safe_title}.png"
    )

    await frame.locator("body").screenshot(
        path=path
    )

    return path