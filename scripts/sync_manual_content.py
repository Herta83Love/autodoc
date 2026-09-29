"""Create or update the human-editable manual content YAML files.

Existing page content is preserved by default. Use --overwrite only when the
intent is to replace all human edits with the current AI/cache output.
"""

import argparse
import os
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "zh-TW")
sys.path.insert(0, str(PROJECT_ROOT))


def load_existing(path):
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    pages = config.get("pages") or {}
    if not isinstance(pages, dict):
        raise ValueError(f"{path} 的 pages 必須是 YAML mapping。")
    return pages


def ordered_content(result, content_fields):
    return {
        field: result.get(
            field,
            "" if field in {"overview", "business_value"} else [],
        )
        for field in content_fields
    }


def preserve_existing_content(
    previous,
    generated,
    content_fields,
    merge_new_structured_items,
):
    """Keep human edits while adding any newly supported content fields."""

    content = dict(previous.get("content") or {})
    for field in content_fields:
        content.setdefault(field, generated[field])
    for field in (
        "button_descriptions",
        "interaction_sections",
        "page_sections",
        "field_descriptions",
    ):
        content[field] = merge_new_structured_items(
            content.get(field),
            generated.get(field),
        )
    return {field: content[field] for field in content_fields}


def write_content_file(path, language, pages):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Human-editable content used by the generated manual.\n"
        "# Edit values under content; category/page/tab are lookup labels.\n"
        "# Run python3 scripts/sync_manual_content.py after a new crawl to add\n"
        "# missing pages without overwriting existing human edits.\n\n"
    )
    payload = {"version": 1, "language": language, "pages": pages}
    rendered = yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )
    path.write_text(header + rendered, encoding="utf-8")


def sync(overwrite=False):
    os.chdir(PROJECT_ROOT)

    from test_docx import load_bilingual_metadata, pair_chinese_terms
    from document.ai_generator import generate_ai_manual_section
    from document.manual_content import (
        CONTENT_FIELDS,
        manual_content_path,
        merge_new_structured_items,
        page_content_key,
    )
    from document.manual_generator import (
        group_pages,
        merge_equivalent_tabs,
        prepare_display_pages,
    )

    metadata, english_terms = load_bilingual_metadata()
    pair_chinese_terms(metadata, english_terms)

    for language in LANGUAGES:
        path = manual_content_path(language)
        existing = load_existing(path)
        synced = {}
        grouped = merge_equivalent_tabs(
            group_pages(prepare_display_pages(metadata[language], language))
        )

        for page_dict in grouped.values():
            for items in page_dict.values():
                for page in items:
                    key = page_content_key(page)
                    generated = generate_ai_manual_section(page)
                    content = ordered_content(generated, CONTENT_FIELDS)
                    previous = existing.get(key) or {}
                    synced[key] = {
                        "category": page.get("category") or "",
                        "page": page.get("page") or "",
                        "tab": page.get("tab") or None,
                        "equivalent_tabs": page.get("equivalent_tabs") or [],
                        "content": (
                            content
                            if overwrite or not previous
                            else preserve_existing_content(
                                previous,
                                content,
                                CONTENT_FIELDS,
                                merge_new_structured_items,
                            )
                        ),
                    }

        # Keep pages that temporarily disappeared from a crawl so human edits
        # are never silently discarded.
        for key, entry in existing.items():
            synced.setdefault(key, entry)

        write_content_file(path, language, synced)
        print(f"✅ 已同步 {len(synced)} 個頁面：{path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing human edits with the current AI/cache content.",
    )
    args = parser.parse_args()
    sync(overwrite=args.overwrite)


if __name__ == "__main__":
    main()
