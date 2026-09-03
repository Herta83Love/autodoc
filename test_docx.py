"""Use existing crawl output to regenerate the manual without Playwright.

This script is intended for iterating on ``document/manual_generator.py``.
It reads ``output/metadata.json`` and reuses the screenshots/icon images whose
paths are recorded in that file. No browser, login, or crawler code is run.
"""

import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
METADATA_PATH = OUTPUT_DIR / "metadata.json"
DOCX_PATH = OUTPUT_DIR / "SENTRY_Manual.docx"


def load_metadata():
    if not METADATA_PATH.is_file():
        raise FileNotFoundError(
            "找不到 output/metadata.json，請先執行 main.py 完成一次爬取。"
        )

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    if not isinstance(metadata, list):
        raise ValueError("output/metadata.json 格式錯誤：最外層必須是陣列。")

    if not metadata:
        raise ValueError("output/metadata.json 沒有任何頁面資料。")

    return metadata


def resolve_output_asset(path_value):
    """Resolve metadata paths regardless of the shell's current directory."""

    if not path_value:
        return None

    path = Path(path_value)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


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


def print_asset_warnings(missing_screenshots, missing_icons):
    if missing_screenshots:
        print(f"⚠️ 找不到 {len(missing_screenshots)} 張頁面截圖，相關圖片將被略過。")

        for page_index, path in missing_screenshots[:5]:
            print(f"   metadata 第 {page_index} 筆：{path}")

    if missing_icons:
        print(f"⚠️ 找不到 {len(missing_icons)} 張操作圖示，相關圖示將被略過。")

        for page_index, action_index, path in missing_icons[:5]:
            print(
                f"   metadata 第 {page_index} 筆、action 第 {action_index} 筆：{path}"
            )


def run():
    # The generators currently use project-relative config/output paths.
    # Normalizing cwd also lets this script run from any directory.
    os.chdir(PROJECT_ROOT)

    metadata = load_metadata()
    missing_screenshots, missing_icons = check_assets(metadata)

    print(f"載入 Metadata 成功，共 {len(metadata)} 筆")
    print_asset_warnings(missing_screenshots, missing_icons)
    print("開始使用既有 metadata 與截圖產生 Word 文件（不執行爬蟲）...")

    # Import after cwd normalization because the document modules initialize
    # cache/config paths during import.
    from utils.file_helper import ensure_directories
    from document.manual_generator import generate_docx

    ensure_directories()
    generate_docx()

    if not DOCX_PATH.is_file():
        raise RuntimeError("文件產生程序已結束，但找不到 output/SENTRY_Manual.docx。")

    print(f"✅ 文件已產生：{DOCX_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    try:
        run()
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(f"❌ 無法產生文件：{error}") from error
