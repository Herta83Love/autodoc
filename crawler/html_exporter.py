import re


async def save_html(
    frame,
    title
):

    safe_title = re.sub(
        r'[^a-zA-Z0-9_]',
        '_',
        title
    )

    path = (
        f"output/html/"
        f"{safe_title}.html"
    )

    html = await frame.content()

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(html)

    return path