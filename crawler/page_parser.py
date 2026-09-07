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

    screenshot_paths=None,

    language="zh-TW",

    page_key="",

    menu_index=0,

    tab_index=None
):

    field_details_raw = await frame.evaluate("""
    () => {
        const visibleInLayout = element => {
            for (let node = element; node; node = node.parentElement) {
                const style = window.getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden') {
                    return false;
                }
            }
            return true;
        };

        const directText = (container, selector) => {
            if (!container) return '';
            const node = container.querySelector(`:scope > ${selector}`);
            return node ? (node.innerText || '').trim() : '';
        };

        return Array.from(document.querySelectorAll('input,select,textarea'))
            .filter(control => control.type !== 'hidden' && visibleInLayout(control))
            .map(control => {
                const item = control.closest('.operation-conf-item');
                const block = control.closest('.operation-conf-block');
                const section = directText(block, '.title');
                let label = directText(item, '.field');

                if (!label && control.id) {
                    const associated = document.querySelector(
                        `label[for="${CSS.escape(control.id)}"]`
                    );
                    label = associated ? (associated.innerText || '').trim() : '';
                }

                label = label
                    || (control.getAttribute('aria-label') || '').trim()
                    || (control.getAttribute('placeholder') || '').trim();

                let options = [];
                if (control.tagName === 'SELECT') {
                    options = Array.from(control.options)
                        .map(option => (option.textContent || '').trim())
                        .filter(Boolean);
                } else if (control.type === 'checkbox' || control.type === 'radio') {
                    const optionLabel = control.id
                        ? document.querySelector(`label[for="${CSS.escape(control.id)}"]`)
                        : null;
                    const optionText = optionLabel
                        ? (optionLabel.innerText || '').trim()
                        : '';
                    if (optionText && optionText !== label) options = [optionText];
                }

                return {
                    internal_name: control.name || control.id || '',
                    section,
                    label,
                    options
                };
            });
    }
    """)

    field_details_by_key = {}
    for detail in field_details_raw:
        section = str(detail.get("section") or "").strip()
        label = str(detail.get("label") or "").strip()
        internal_name = str(detail.get("internal_name") or "").strip()
        key = (section, label, internal_name)
        if key not in field_details_by_key:
            field_details_by_key[key] = {
                "internal_name": internal_name,
                "section": section,
                "label": label,
                "options": []
            }
        for option in detail.get("options") or []:
            option = str(option).strip()
            if option and option not in field_details_by_key[key]["options"]:
                field_details_by_key[key]["options"].append(option)

    field_details = list(field_details_by_key.values())

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

    fields = []
    for detail in field_details:
        section = detail["section"]
        label = detail["label"]
        display_name = f"{section}－{label}" if section and label else label
        if display_name and display_name not in fields:
            fields.append(display_name)

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
                'h1,h2,h3,h4,h5,h6,.operation-conf-block > .title'
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

    fields = clean_items(fields)

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

        screenshots=screenshot_paths or [screenshot_path],

        html=html_path,

        fields=fields,

        field_details=field_details,

        buttons=buttons,

        tables=[table_headers],

        headings=headings,

        descriptions=descriptions
    )
