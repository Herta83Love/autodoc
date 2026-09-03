def add_english_terms(chinese_pages, english_pages):
    """Attach official English UI terms using stable crawl position keys."""

    english_by_key = {
        page.get("page_key"): page
        for page in english_pages
        if page.get("page_key")
    }

    for page in chinese_pages:
        english = english_by_key.get(page.get("page_key"))

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
