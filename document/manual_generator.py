#manual_generator.py
import json

from pathlib import Path

from docx import Document
from docx.shared import Inches

from document.ai_generator import (
    generate_manual_section
)


def group_pages(pages):

    grouped = {}

    for page in pages:

        category = page.get(
            "category",
            "Others"
        )

        page_name = page.get(
            "page",
            page.get(
                "title",
                ""
            )
        )

        grouped.setdefault(
            category,
            {}
        )

        grouped[
            category
        ].setdefault(
            page_name,
            []
        )

        grouped[
            category
        ][
            page_name
        ].append(
            page
        )

    return grouped


def add_bullet_list(
    document,
    items
):

    if not items:
        return

    for item in items:

        if not item:
            continue

        document.add_paragraph(
            str(item),
            style="List Bullet"
        )


def generate_docx():

    metadata_file = (
        "output/metadata.json"
    )

    with open(
        metadata_file,
        "r",
        encoding="utf-8"
    ) as f:

        pages = json.load(f)

    grouped = group_pages(
        pages
    )

    document = Document()

    document.add_heading(
        "SENTRY 使用手冊",
        level=0
    )

    document.add_paragraph(
        f"共產生 {len(pages)} 個功能頁"
    )

    for category, pages_dict in grouped.items():

        document.add_page_break()

        document.add_heading(
            category,
            level=1
        )

        for page_name, page_items in pages_dict.items():

            document.add_heading(
                page_name,
                level=2
            )

            for page in page_items:

                tab_name = page.get(
                    "tab"
                )

                if tab_name:

                    document.add_heading(
                        tab_name,
                        level=3
                    )

                screenshot = page.get(
                    "screenshot"
                )

                if (
                    screenshot
                    and Path(
                        screenshot
                    ).exists()
                ):

                    try:

                        document.add_picture(
                            screenshot,
                            width=Inches(6.5)
                        )

                    except Exception as e:

                        print(
                            f"圖片插入失敗: {screenshot}"
                        )

                        print(e)

                try:

                    section = (
                        generate_manual_section(
                            page
                        )
                    )

                    summary = section.get(
                        "summary",
                        ""
                    )

                    features = section.get(
                        "features",
                        []
                    )
                    field_descriptions = section.get(
                        "field_descriptions",
                        []
                    )

                    steps = section.get(
                        "steps",
                        []
                    )

                    notes = section.get(
                        "notes",
                        []
                    )

                    if summary:

                        document.add_heading(
                            "AI摘要",
                            level=4
                        )

                        document.add_paragraph(
                            summary
                        )

                    if features:

                        document.add_heading(
                            "主要功能",
                            level=4
                        )

                        add_bullet_list(
                            document,
                            features
                        )
                    if field_descriptions:

                        document.add_heading(
                            "欄位說明",
                            level=4
                        )

                        add_bullet_list(
                            document,
                            field_descriptions
                        )

                    if steps:

                        document.add_heading(
                            "操作步驟",
                            level=4
                        )

                        for step in steps:

                            document.add_paragraph(
                                str(step)
                            )

                    if notes:

                        document.add_heading(
                            "注意事項",
                            level=4
                        )

                        add_bullet_list(
                            document,
                            notes
                        )

                except Exception as e:

                    print(
                        "AI內容產生失敗"
                    )

                    print(e)

                descriptions = page.get(
                    "descriptions",
                    []
                )

                if descriptions:

                    document.add_heading(
                        "原廠功能說明",
                        level=4
                    )

                    for desc in descriptions:

                        if not desc:
                            continue

                        document.add_paragraph(
                            desc
                        )

                headings = page.get(
                    "headings",
                    []
                )

                if headings:

                    document.add_heading(
                        "功能區塊",
                        level=4
                    )

                    add_bullet_list(
                        document,
                        headings
                    )

                fields = page.get(
                    "fields",
                    []
                )

                if fields:

                    document.add_heading(
                        "設定項目",
                        level=4
                    )

                    add_bullet_list(
                        document,
                        fields
                    )

                buttons = page.get(
                    "buttons",
                    []
                )

                if buttons:

                    document.add_heading(
                        "操作按鈕",
                        level=4
                    )

                    add_bullet_list(
                        document,
                        buttons
                    )

                tables = page.get(
                    "tables",
                    []
                )

                table_columns = []

                for row in tables:

                    if not row:
                        continue

                    for column in row:

                        if column:

                            table_columns.append(
                                column
                            )

                if table_columns:

                    document.add_heading(
                        "資料表欄位",
                        level=4
                    )

                    add_bullet_list(
                        document,
                        table_columns
                    )

    output_file = (
        "output/SENTRY_Manual.docx"
    )

    document.save(
        output_file
    )

    print(
        f"✅ 已產生：{output_file}"
    )
