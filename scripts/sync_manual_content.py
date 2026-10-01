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


CONTENT_FILE_HEADERS = {
    "en": """# Human-editable content used by the generated English manual.
#
# File structure and field guide
# version: Schema version. Do not change it manually.
# language: Language of this file. Keep this value as en.
# document_config: Cover, version, publication, introduction, footer, and back-cover text.
# ai_content_corrections: Verified text replacements applied after AI/cache loading.
# page_notes: Reader-facing cautions for selected menu/tab identifiers.
# pages: All editable manual pages, keyed by a stable menu/tab identifier.
# menu:.../tab:...: Stable page identifier used to match crawler metadata. Do not rename it.
# category: Category label shown for reference and easier searching.
# page: Page label shown for reference and easier searching.
# tab: Tab label; null means that the page has no tab.
# equivalent_tabs: Tabs merged into this entry because they share the same content.
# content: Values below this key are written into the generated manual.
#   overview: Main description of what the page does.
#   business_value: Why the page is useful to an administrator or organization.
#   button_descriptions: Explanations for visible, documentable buttons.
#     action_id: Stable crawler identifier for the button. Do not rename it.
#     include: true includes the button in the manual; false hides it.
#     confidence: AI confidence from 0 to 1. It is reference information only.
#     description: Reader-facing explanation of what the button does.
#   interaction_sections: Forms or panels opened by a button.
#     action_id: Button identifier that opens this form or panel. Do not rename it.
#     title: Heading used for the opened form or panel.
#     overview: Short explanation of the form or panel.
#     field_descriptions: List of field explanations inside the opened form or panel.
#   page_sections: Explanations for charts, status cards, tables, and other page areas.
#   field_descriptions: Explanations for fields visible directly on the page or in record details.
#   best_practices: Recommended operating practices for this page.
#   restrictions: Limitations, prerequisites, and cautions for this page.
#
# Editing notes
# - Text after # is a comment and is not included in the manual.
# - Keep the existing indentation, action_id values, and page identifiers.
# - Use [] for an intentionally empty list, '' for empty text, and null for no tab.
# - Quote a value when it contains YAML-sensitive characters and parsing fails.
# - Run this script after a new crawl. Existing human edits are preserved unless
#   --overwrite is explicitly supplied.

""",
    "zh-TW": """# 產生繁體中文手冊時使用的可人工編輯內容。
#
# 檔案結構與欄位說明
# version：YAML 結構版本，請勿手動修改。
# language：此檔案的語言，請保持為 zh-TW。
# document_config：封面、版本、出版聲明、前言、頁尾與封底文字。
# ai_content_corrections：載入 AI／Cache 後套用的已確認文字修正。
# page_notes：指定功能頁或頁籤顯示給讀者的注意事項。
# pages：所有可編輯的手冊頁面，並以穩定的選單／頁籤識別碼分類。
# menu:.../tab:...：用於對應爬蟲 Metadata 的穩定頁面識別碼，請勿改名。
# category：分類名稱，供閱讀與搜尋使用。
# page：功能頁名稱，供閱讀與搜尋使用。
# tab：頁籤名稱；null 代表該功能頁沒有頁籤。
# equivalent_tabs：因內容相同而合併到此頁的其他頁籤。
# content：此欄位下的內容會寫入最後產生的手冊。
#   overview：說明這個功能頁的主要用途。
#   business_value：說明此功能對管理員或組織的使用價值。
#   button_descriptions：頁面上可放入手冊的按鈕說明清單。
#     action_id：爬蟲產生的穩定按鈕識別碼，請勿改名。
#     include：true 會在手冊顯示該按鈕；false 會將它隱藏。
#     confidence：AI 判斷信心值，範圍為 0 到 1，僅供參考。
#     description：手冊中給讀者閱讀的按鈕功能說明。
#   interaction_sections：點選按鈕後開啟的表單或設定面板。
#     action_id：用於開啟該表單或面板的按鈕識別碼，請勿改名。
#     title：該表單或面板在手冊中使用的標題。
#     overview：該表單或面板的簡短功能說明。
#     field_descriptions：該表單或面板內部的欄位說明清單。
#   page_sections：圖表、狀態卡、表格與其他頁面區塊的說明。
#   field_descriptions：頁面上或資料列明細中可直接看到的欄位說明。
#   best_practices：操作此頁面時的建議做法。
#   restrictions：此頁面的限制、先決條件與注意事項。
#
# 編輯注意事項
# - # 後方的文字是註解，不會出現在手冊中。
# - 請保留原有縮排、action_id 與頁面識別碼。
# - 故意保留空清單時使用 []，空文字使用 ''，沒有頁籤時使用 null。
# - 若內容含有 YAML 特殊字元而無法讀取，請將整段文字加上引號。
# - 完成新一次爬取後執行此程式。除非明確加上 --overwrite，
#   否則不會覆蓋已有的人工修改。

""",
}


def load_existing(path):
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{path} 的最外層必須是 YAML mapping。")
    pages = config.get("pages") or {}
    if not isinstance(pages, dict):
        raise ValueError(f"{path} 的 pages 必須是 YAML mapping。")
    return config


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
    normalize_field_description_items,
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
        edited = content.get(field)
        generated_items = generated.get(field)
        if field == "field_descriptions":
            edited = normalize_field_description_items(edited)
            generated_items = normalize_field_description_items(generated_items)
        content[field] = merge_new_structured_items(
            edited,
            generated_items,
        )
    return {field: content[field] for field in content_fields}


def write_content_file(path, language, pages, existing_config):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = CONTENT_FILE_HEADERS[language]
    payload = {"version": 1, "language": language}
    payload.update({
        key: value
        for key, value in existing_config.items()
        if key not in {"version", "language", "pages"}
    })
    payload["pages"] = pages
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
        normalize_field_description_items,
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
        existing_config = load_existing(path)
        existing = existing_config.get("pages") or {}
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
                                normalize_field_description_items,
                            )
                        ),
                    }

        # Keep pages that temporarily disappeared from a crawl so human edits
        # are never silently discarded.
        for key, entry in existing.items():
            synced.setdefault(key, entry)

        write_content_file(path, language, synced, existing_config)
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
