# ============================================================================
# File: markdown_generator.py
# ============================================================================

from jinja2 import Template

from document.templates import (
    PAGE_TEMPLATE
)


def generate_manual(
    pages,
    output_path="output/manual.md",
    language="zh-TW"
):

    title = (
        "System Administration Manual"
        if str(language).lower().startswith("en")
        else "系統操作手冊"
    )
    content = f"# {title}\n\n"

    for page in pages:

        template = Template(
            PAGE_TEMPLATE
        )

        content += template.render(
            title=page.get("title", ""),
            url=page.get("url", ""),
            screenshot=page.get(
                "screenshot",
                ""
            ),
            fields=page.get(
                "fields",
                []
            ),
            buttons=page.get(
                "buttons",
                []
            )
        )

        content += "\n\n---\n\n"

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)

    return content
