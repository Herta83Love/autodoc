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
