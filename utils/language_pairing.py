from copy import deepcopy


def native_label(label, english_label):
    """Remove a YAML reference suffix that will be re-added during pairing."""

    label = str(label or "").strip()
    english_label = str(english_label or "").strip()
    for suffix in (f"（{english_label}）", f" ({english_label})"):
        if english_label and label.endswith(suffix):
            return label[:-len(suffix)].strip()
    return label


def restore_missing_localized_pages(
    localized_pages,
    reference_pages,
    manual_pages,
    language,
):
    """Restore crawled pages missing from one language using editable YAML labels."""

    localized_by_key = {
        page.get("page_key"): page
        for page in localized_pages
        if page.get("page_key")
    }
    restored_keys = []

    for reference in reference_pages:
        page_key = reference.get("page_key")
        if not page_key or page_key in localized_by_key:
            continue

        manual_entry = (manual_pages or {}).get(page_key)
        if not isinstance(manual_entry, dict):
            continue

        restored = deepcopy(reference)
        restored["language"] = language
        restored["category"] = native_label(
            manual_entry.get("category") or restored.get("category"),
            reference.get("category"),
        )
        restored["page"] = native_label(
            manual_entry.get("page") or restored.get("page"),
            reference.get("page"),
        )
        restored["title"] = restored["page"]
        restored["tab"] = native_label(
            manual_entry.get("tab"),
            reference.get("tab"),
        ) or None
        restored["english_category"] = reference.get("category")
        restored["english_page"] = reference.get("page")
        restored["english_tab"] = reference.get("tab")

        localized_pages.append(restored)
        localized_by_key[page_key] = restored
        restored_keys.append(page_key)

    if restored_keys:
        reference_order = {
            page.get("page_key"): index
            for index, page in enumerate(reference_pages)
            if page.get("page_key")
        }
        localized_pages.sort(
            key=lambda page: reference_order.get(
                page.get("page_key"),
                len(reference_order),
            )
        )

    return restored_keys


def add_english_terms(chinese_pages, english_pages, english_terms=None):
    """Attach official English UI terms using the crawl term manifest first."""

    english_by_key = {
        page.get("page_key"): page
        for page in english_pages
        if page.get("page_key")
    }
    english_by_key.update(english_terms or {})

    for page in chinese_pages:
        page_key = page.get("page_key")
        english = english_by_key.get(page_key)

        # A page may have been exposed as tabs in only one language. The menu
        # term is still authoritative for category/page names.
        if english is None and page_key and "/tab:" in page_key:
            english = english_by_key.get(page_key.split("/tab:", 1)[0])

        if english is None:
            continue

        page["english_category"] = english.get("category")
        page["english_page"] = english.get("page")
        page["english_tab"] = english.get("tab")

    return chinese_pages


def find_unpaired_pages(chinese_pages):

    return [
        page.get("page_key") or page.get("page") or "unknown"
        for page in chinese_pages
        if not page.get("english_page")
    ]
