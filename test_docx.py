"""Regenerate both manuals from existing crawl output without Playwright.

The script reuses bilingual metadata, screenshots, button images, and AI cache.
It also reapplies the English UI-term pairing before generating the Chinese
manual, so document-layout changes do not require another crawl.
"""

import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LANGUAGES = ("en", "zh-TW")


def load_json(path, expected_type, description, required=True):
    if not path.is_file():
        if not required:
            return expected_type()
        raise FileNotFoundError(
            f"找不到 {path.relative_to(PROJECT_ROOT)}，請先執行 main.py 完成雙語爬取。"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, expected_type):
        raise ValueError(
            f"{path.relative_to(PROJECT_ROOT)} 格式錯誤："
            f"最外層必須是{'陣列' if expected_type is list else '物件'}。"
        )

    if required and not data:
        raise ValueError(f"{path.relative_to(PROJECT_ROOT)} 沒有任何{description}。")

    return data


def load_bilingual_metadata():
    metadata = {
        language: load_json(
            OUTPUT_DIR / f"metadata_{language}.json",
            list,
            "頁面資料"
        )
        for language in LANGUAGES
    }
    english_terms = load_json(
        OUTPUT_DIR / "terms_en.json",
        dict,
        "英文介面名稱",
        required=False
    )
    return metadata, english_terms


def resolve_output_asset(path_value):
    if not path_value:
        return None

    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def check_assets(metadata):
    missing_screenshots = []
    missing_icons = []

    for page_index, page in enumerate(metadata, start=1):
        screenshot = resolve_output_asset(page.get("screenshot"))

        if screenshot is not None and not screenshot.is_file():
            missing_screenshots.append((page_index, screenshot))

        for action_index, action in enumerate(page.get("actions") or [], start=1):
            image = resolve_output_asset(action.get("image"))

            if image is not None and not image.is_file():
                missing_icons.append((page_index, action_index, image))

    return missing_screenshots, missing_icons


def print_asset_warnings(language, missing_screenshots, missing_icons):
    if missing_screenshots:
        print(
            f"⚠️ {language} 找不到 {len(missing_screenshots)} 張頁面截圖，"
            "相關圖片將被略過。"
        )
        for page_index, path in missing_screenshots[:5]:
            print(f"   Metadata 第 {page_index} 筆：{path}")

    if missing_icons:
        print(
            f"⚠️ {language} 找不到 {len(missing_icons)} 張操作圖示，"
            "相關圖示將被略過。"
        )
        for page_index, action_index, path in missing_icons[:5]:
            print(
                f"   Metadata 第 {page_index} 筆、Action 第 {action_index} 筆：{path}"
            )


def pair_chinese_terms(metadata, english_terms):
    from utils.language_pairing import add_english_terms, find_unpaired_pages

    chinese_pages = metadata["zh-TW"]
    add_english_terms(chinese_pages, metadata["en"], english_terms)
    unpaired = find_unpaired_pages(chinese_pages)

    if unpaired:
        raise RuntimeError(
            "以下中文頁面找不到對應的英文介面專有名詞："
            + ", ".join(unpaired)
            + "。請確認 output/terms_en.json 與英文 Metadata 是否完整。"
        )


def run():
    os.chdir(PROJECT_ROOT)

    from utils.file_helper import ensure_directories
    from document.manual_generator import generate_docx

    ensure_directories()
    metadata, english_terms = load_bilingual_metadata()
    pair_chinese_terms(metadata, english_terms)

    print("已載入並完成中英文 Metadata 配對：")
    for language in LANGUAGES:
        pages = metadata[language]
        print(f"  {language}: {len(pages)} 筆")
        missing_screenshots, missing_icons = check_assets(pages)
        print_asset_warnings(language, missing_screenshots, missing_icons)

    print("開始使用既有爬蟲與 AI Cache 產生雙語 Word 文件（不執行爬蟲）...")

    for language in LANGUAGES:
        output_path = OUTPUT_DIR / f"SENTRY_Manual_{language}.docx"
        generate_docx(
            pages=metadata[language],
            language=language,
            output_path=str(output_path.relative_to(PROJECT_ROOT))
        )

        if not output_path.is_file():
            raise RuntimeError(
                f"文件產生程序已結束，但找不到 {output_path.relative_to(PROJECT_ROOT)}。"
            )

        print(f"✅ {language} 文件已產生：{output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    try:
        run()
    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError
    ) as error:
        raise SystemExit(f"❌ 無法產生文件：{error}") from error

