# ============================================================================
# File: main.py
# ============================================================================

import json
import asyncio
from crawler.menu_helper import (
    expand_all_menus
)
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

async def run():

    ensure_directories()

    config = load_config(
        "config/config.yaml"
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=[
                "--ignore-certificate-errors"
            ]
        )

        context = await browser.new_context(
            ignore_https_errors=True
        )

        page = await context.new_page()

        # 登入
        await login(page, config)

        print("Current URL:")
        print(await page.title())
        print(page.url)

        # 探索選單
        menus = await discover_menu_links(
            page
        )

        print("\n========== MENU ==========")

        for menu in menus:
            print(menu)

        print(
            f"\n共發現 {len(menus)} 個功能頁"
        )

        # 爬取所有頁面
        metadata = await crawl_pages(
            page,
            menus
        )

        # 儲存 metadata
        with open(
            "output/metadata.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"\n共產生 {len(metadata)} 筆 Metadata"
        )

        # 產生 Markdown 文件
        generate_manual(
            metadata
        )

        generate_docx()

        print(
            "\n✅ manual.md 已產生"
        )

        print(
            "✅ SENTRY_Manual.docx 已產生"
        )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(run())