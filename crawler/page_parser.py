#page_parser.py
from models.page import (
    PageMetadata
)

from utils.metadata_cleaner import (
    clean_items
)


async def analyze_page(

    frame,

    category,

    page_name,

    tab_name,

    url,

    screenshot_path,

    html_path
):

    buttons = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                'button'
            )
        )
        .map(x =>
            (x.innerText || '').trim()
        )
        .filter(Boolean)

    }
    """)

    labels = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                'label'
            )
        )
        .map(x =>
            x.innerText.trim()
        )
        .filter(Boolean)

    }
    """)

    fields = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                'input,select,textarea'
            )
        )
        .map(x => {

            return (
                x.placeholder ||
                x.name ||
                x.id ||
                ''
            )

        })
        .filter(Boolean)

    }
    """)

    table_headers = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                'th'
            )
        )
        .map(x =>
            x.innerText.trim()
        )
        .filter(Boolean)

    }
    """)

    headings = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                'h1,h2,h3,h4,h5,h6'
            )
        )
        .map(x =>
            x.innerText.trim()
        )
        .filter(Boolean)

    }
    """)

    descriptions = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                '.description'
            )
        )
        .map(x =>
            x.innerText.trim()
        )
        .filter(Boolean)

    }
    """)

    buttons = clean_items(
        buttons
    )

    fields = clean_items(
        fields + labels
    )

    table_headers = clean_items(
        table_headers
    )

    headings = clean_items(
        headings
    )

    descriptions = clean_items(
        descriptions
    )

    return PageMetadata(

        category=category,

        page=page_name,

        tab=tab_name,

        title=(
            f"{page_name}_{tab_name}"
            if tab_name
            else page_name
        ),

        url=url,

        screenshot=screenshot_path,

        html=html_path,

        fields=fields,

        buttons=buttons,

        tables=[table_headers],

        headings=headings,

        descriptions=descriptions
    )