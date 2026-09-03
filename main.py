# ============================================================================
# File: main.py
# ============================================================================

import json
import asyncio
import logging
from playwright.async_api import (
    async_playwright
)

from utils.config_loader import (
    load_config
)

from utils.file_helper import (
    ensure_directories
)

from crawler.login import (
    login
)

from crawler.menu_discovery import (
    discover_menu_links
)

from crawler.page_crawler import (
    crawl_pages
)

from document.markdown_generator import (
    generate_manual
)

from document.manual_generator import (
    generate_docx
) 

from utils.language_pairing import (
    add_english_terms,
    find_unpaired_pages
)


async def crawl_language(browser, config, language_cfg):

    language_code = language_cfg["code"]
    print(f"\n========== LANGUAGE: {language_code} ==========\n")

    context = await browser.new_context(
        ignore_https_errors=True
    )
    page = await context.new_page()

    try:
        await login(page, config, language_cfg)

        print("Current URL:")
        print(await page.title())
        print(page.url)

        menus = await discover_menu_links(page)

        print("\n========== MENU ==========")

        for menu in menus:
            print(menu)

        print(f"\n共發現 {len(menus)} 個功能頁")

        term_index = {}
        metadata = await crawl_pages(
            page,
            menus,
            language=language_code,
            output_root=f"output/{language_code}",
            term_index=term_index
        )

        return metadata, term_index

    finally:
        await context.close()

async def run():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    ensure_directories()

    config = load_config(
        "config/config.yaml"
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            slow_mo=0,
            args=[
                "--ignore-certificate-errors"
            ]
        )

        language_runs = (
            config.get("login", {})
            .get("language", {})
            .get("runs", [])
        )

        if not language_runs:
            raise RuntimeError(
                "config/config.yaml 缺少 login.language.runs"
            )

        all_metadata = {}
        all_terms = {}

        # 依 YAML 順序執行；預設為英文完整擷取後再擷取繁體中文。
        for language_cfg in language_runs:
            code = language_cfg["code"]
            metadata, term_index = await crawl_language(
                browser,
                config,
                language_cfg
            )
            all_metadata[code] = metadata
            all_terms[code] = term_index

            # Persist each completed crawl immediately. A later language or
            # pairing error must not discard a successful long-running crawl.
            with open(
                f"output/metadata_{code}.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            with open(
                f"output/terms_{code}.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(term_index, f, ensure_ascii=False, indent=2)

        english_metadata = all_metadata.get("en", [])
        chinese_metadata = all_metadata.get("zh-TW", [])
        add_english_terms(
            chinese_metadata,
            english_metadata,
            all_terms.get("en", {})
        )
        unpaired_pages = find_unpaired_pages(chinese_metadata)

        if unpaired_pages:
            raise RuntimeError(
                "以下中文頁面找不到對應的英文介面專有名詞："
                + ", ".join(unpaired_pages)
            )

        for code, metadata in all_metadata.items():
            metadata_path = f"output/metadata_{code}.json"

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(
                    metadata,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            generate_manual(
                metadata,
                output_path=f"output/manual_{code}.md",
                language=code
            )

            generate_docx(
                pages=metadata,
                language=code,
                output_path=f"output/SENTRY_Manual_{code}.docx"
            )

            print(
                f"✅ {code}: {len(metadata)} 筆 Metadata、Markdown 與 DOCX 已產生"
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(run())
