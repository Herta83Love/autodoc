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

    # SENTRY embeds authoritative icon descriptions in its hidden help panel.
    # Keep them as structured evidence for the VLM instead of flattening the
    # whole panel into unrelated page text.
    help_actions = await frame.evaluate("""
    () => Array.from(document.querySelectorAll('table.sidepaneltable'))
        .map((table, index) => {
            const icon = table.querySelector('.SPTicon i, td i');
            const image = table.querySelector('.SPTicon img, td img');
            const descriptions = Array.from(table.querySelectorAll('.SPTdesc'))
                .map(node => (node.textContent || '').trim())
                .filter(Boolean);
            return {
                help_index: index,
                icon: icon ? (icon.getAttribute('class') || '') : '',
                image_src: image ? (image.getAttribute('src') || '') : '',
                // This script is embedded in a Python triple-quoted string.
                // Escape the backslash so JavaScript receives "\\n" instead
                // of an actual newline inside a single-quoted literal.
                description: descriptions.join('\\n')
            };
        })
        .filter(item => item.description);
    """)

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

        // SENTRY hides the checkbox for both controls. #mazi-switch is an
        // on/off toggle. .mazi-switch-pick is a two-choice selector such as
        // Type: Exact Match / Wildcard Match. Document the visible widget.
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

        return Array.from(document.querySelectorAll('input,select,textarea'))
            .filter(control => {
                if (control.type === 'hidden') return false;
                const widget = switchWidget(control);
                return visibleInLayout(widget || control);
            })
            .map(control => {
                const widget = switchWidget(control);
                const item = control.closest('.operation-conf-item');
                const block = control.closest('.operation-conf-block');
                const section = directText(block, '.title');
                let label = directText(item, '.field');

                if (!label && control.id && !widget) {
                    const associated = document.querySelector(
                        `label[for="${CSS.escape(control.id)}"]`
                    );
                    label = associated ? (associated.innerText || '').trim() : '';
                }

                // A placeholder is an example/value hint, not a field name.
                // Treating it as a label previously leaked values such as
                // backup.yourdomain.com and backup filename patterns into the
                // generated manual.
                label = label
                    || (control.getAttribute('aria-label') || '').trim();

                let options = [];
                if (widget) {
                    options = switchOptions(widget);
                } else if (control.tagName === 'SELECT') {
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
        # Controls without a public label cannot be documented reliably. Keep
        # the internal name out of the AI input instead of asking it to guess.
        if not label:
            continue

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

    # Read-only rows, list cards and the unpair prompt have a public label
    # without a visible input. Switches and two-choice selectors are included
    # here as well so a hidden checkbox cannot drop the field.
    labeled_rows = await frame.evaluate("""
    () => {
        const shown = element => {
            if (!element) return false;
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
            return node ? (node.innerText || '').replace(/\\s+/g, ' ').trim() : '';
        };
        const choiceOptions = widget => {
            const values = [];
            widget.querySelectorAll('p').forEach(node => {
                const value = (node.innerText || '').replace(/\\s+/g, ' ').trim();
                if (value && !values.includes(value)) values.push(value);
            });
            return values;
        };
        const rows = [];
        const seen = new Set();
        const add = (section, label, options) => {
            label = String(label || '').replace(/\\s+/g, ' ').trim();
            section = String(section || '').replace(/\\s+/g, ' ').trim();
            if (!label || label.length > 80) return;
            const key = section + '\\n' + label;
            if (seen.has(key)) return;
            seen.add(key);
            rows.push({section, label, options: options || []});
        };

        document.querySelectorAll('.operation-conf-item').forEach(item => {
            if (!shown(item)) return;
            const widget = item.querySelector('[id="mazi-switch"], .mazi-switch-pick');
            const block = item.closest('.operation-conf-block');
            add(
                directText(block, '.title'),
                directText(item, '.field'),
                widget ? choiceOptions(widget) : []
            );
        });

        document.querySelectorAll('p.sub_title').forEach(node => {
            if (!shown(node) || node.closest('.modal, .hint-modal')) return;
            add('', node.innerText, []);
        });

        const legendOptions = () => Array.from(
            document.querySelectorAll('.action-prompt')
        ).map(node => (node.innerText || '').replace(/\\s+/g, ' ').trim())
        .filter(value => value && !/變更|儲存|change all|save change|sorting|mutiple|multiple selection|^排序$|^多選/i.test(value));

        document.querySelectorAll('.risk-level').forEach(level => {
            const options = legendOptions();
            level.querySelectorAll('.category .alias').forEach(alias => {
                add(directText(level, '.risk-header'), alias.innerText, options);
            });
        });

        if (document.querySelector('.tlds-area')) {
            const search = document.querySelector('input.search');
            if (search && shown(search)) {
                add('', search.getAttribute('placeholder') || '', []);
            }
            document.querySelectorAll('.type').forEach(box => {
                if (box.closest('.tlds-area')) return;
                const chips = Array.from(box.children).filter(node =>
                    node.tagName === 'DIV'
                    && (node.classList.contains('low') || node.classList.contains('gtld')
                        || node.classList.contains('changed'))
                );
                if (!chips.length) return;
                Array.from(box.children).forEach(node => {
                    if (node.tagName === 'DIV' && shown(node)) add('', node.innerText, []);
                });
            });
            const policy = legendOptions();
            if (policy.length) add('', policy[0], policy);
        }

        document.querySelectorAll('.hint-modal .modal-body').forEach(body => {
            const prompt = Array.from(body.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => (node.textContent || '').replace(/\\s+/g, ' ').trim())
                .filter(Boolean)
                .join(' ');
            const selected = body.querySelector('.vs__selected');
            const option = selected
                ? (selected.innerText || '').replace(/\\s+/g, ' ').trim()
                : '';
            add('', prompt, option ? [option] : []);
        });

        return rows;
    }
    """)
    known_fields = {
        (detail["section"], detail["label"]) for detail in field_details
    }
    for row in labeled_rows or []:
        section = str(row.get("section") or "").strip()
        label = str(row.get("label") or "").strip()
        if not label or (section, label) in known_fields:
            continue
        known_fields.add((section, label))
        field_details.append({
            "internal_name": "",
            "section": section,
            "label": label,
            "options": [
                str(option).strip()
                for option in row.get("options") or []
                if str(option).strip()
            ],
            "kind": "display",
        })

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
        .map(cell => {
            const line = String(cell.innerText || '')
                .split(/\\n/)
                .map(value => value.trim())
                .find(value => value && !/sort table by/i.test(value));
            return line || '';
        })
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
    known_fields = {
        (detail["section"], detail["label"]) for detail in field_details
    }
    for header in table_headers:
        if header.casefold() in {"no.", "no"}:
            continue
        if ("", header) in known_fields:
            continue
        known_fields.add(("", header))
        field_details.append({
            "internal_name": "",
            "section": "",
            "label": header,
            "options": [],
            "kind": "table",
        })
        if header not in fields:
            fields.append(header)

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

        help_actions=help_actions,

        interaction_flows=[],

        fields=fields,

        field_details=field_details,

        buttons=buttons,

        tables=[table_headers],

        headings=headings,

        descriptions=descriptions
    )
