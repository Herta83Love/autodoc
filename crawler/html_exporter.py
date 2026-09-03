# ============================================================================
# File: html_exporter.py
# ============================================================================

import re
from pathlib import Path


async def save_html(
    frame,
    title,
    output_dir="output/html"
):

    safe_title = re.sub(
        r'[^a-zA-Z0-9_]',
        '_',
        title
    )

    path = (
        f"{output_dir}/"
        f"{safe_title}.html"
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    html = await frame.content()

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(html)

    return path
