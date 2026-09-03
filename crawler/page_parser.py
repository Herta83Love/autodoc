# ============================================================================
# File: page_parser.py
# ============================================================================

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

    html_path,

    language="zh-TW",

    page_key="",

    menu_index=0,

    tab_index=None
):

    #
    # Buttons
    #
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
        .filter(Boolean);

    }
    """)

    #
    # Labels
    #
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
        .filter(Boolean);

    }
    """)

    #
    # Fields
    #
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
            );

        })
        .filter(Boolean);

    }
    """)

    #
    # Table Headers
    #
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
        .filter(Boolean);

    }
    """)

    #
    # Headings
    #
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
        .filter(Boolean);

    }
    """)

    #
    # Visible Descriptions Only
    #
    descriptions = await frame.evaluate("""
    () => {

        return Array.from(
            document.querySelectorAll(
                '.description'
            )
        )
        .filter(el => {

            const style =
                window.getComputedStyle(el);

            const rect =
                el.getBoundingClientRect();

            return (
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                rect.width > 0 &&
                rect.height > 0
            );

        })
        .map(x =>
            x.innerText.trim()
        )
        .filter(Boolean);

    }
    """)
    print(f"Description Found: {page_name}")

    for desc in descriptions:

        print(
            desc[:150]
        )
    #
    # Clean Results
    #
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

    #
    # Debug
    #
    try:

        body_text = await frame.locator(
            "body"
        ).inner_text()

        print(
            "\n===== BODY PREVIEW ====="
        )

        print(
            body_text[:500]
        )

        print(
            "\n========================\n"
        )

    except Exception:
        pass

    #
    # Build Metadata
    #
    return PageMetadata(

        language=language,

        page_key=page_key,

        menu_index=menu_index,

        tab_index=tab_index,

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
