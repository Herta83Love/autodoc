# ============================================================================
# File: manual_generator.py
# ============================================================================

import json
import yaml
import ast
import re
from datetime import datetime
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx import Document
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from document.ai_generator import (
    generate_manual_section
)

bookmark_id = 1
DOCUMENT_CONFIG = (
    "config/document.yaml"
)
def generate_manual_toc(
    document,
    grouped
):

    document.add_heading(
        "目錄",
        level=1
    )

    for category, page_dict in grouped.items():

        p = document.add_paragraph()

        p.alignment = 1

        add_internal_link(
            p,
            category,
            f"bookmark_{sanitize_bookmark_name(category)}"
        )

        for page_name, items in page_dict.items():

            p = document.add_paragraph()

            add_internal_link(
                p,
                page_name,
                f"bookmark_{sanitize_bookmark_name(page_name)}"
            )

            rendered_tabs = set()

            for page in items:

                tab = (
                    page.get("tab") or ""
                ).strip()

                if (
                    tab
                    and tab not in rendered_tabs
                ):

                    p = document.add_paragraph()

                    add_internal_link(
                        p,
                        f"    {tab}",
                        f"bookmark_{sanitize_bookmark_name(page_name)}_{sanitize_bookmark_name(tab)}"
                    )

                    rendered_tabs.add(
                        tab
                    )

    document.add_page_break()
def normalize_ai_content(data):

    if not data:
        return data

    if isinstance(data, str):

        text = data.strip()

        if (
            text.startswith("{")
            and text.endswith("}")
        ):
            try:

                obj = ast.literal_eval(text)

                rows = []

                for k, v in obj.items():

                    rows.append(
                        f"{k}\n{v}"
                    )

                return rows

            except Exception:
                return text

        return text

    if isinstance(data, list):

        result = []

        for item in data:

            if not isinstance(item, str):
                result.append(item)
                continue

            text = item.strip()

            if (
                text.startswith("{")
                and text.endswith("}")
            ):
                try:

                    obj = ast.literal_eval(text)

                    for k, v in obj.items():

                        result.append(
                            f"{k}\n{v}"
                        )

                except Exception:
                    result.append(text)

            else:
                result.append(text)

        return result

    return data

def load_document_config():

    with open(
        DOCUMENT_CONFIG,
        "r",
        encoding="utf-8"
    ) as f:

        return yaml.safe_load(
            f
        )



def add_bookmark(
    paragraph,
    name
):

    global bookmark_id

    start = OxmlElement(
        "w:bookmarkStart"
    )

    start.set(
        qn("w:id"),
        str(bookmark_id)
    )

    start.set(
        qn("w:name"),
        name
    )

    end = OxmlElement(
        "w:bookmarkEnd"
    )

    end.set(
        qn("w:id"),
        str(bookmark_id)
    )

    paragraph._p.insert(
        0,
        start
    )

    paragraph._p.append(
        end
    )

    bookmark_id += 1

def add_bullet_list(
    document,
    items
):

    for item in items:

        if not item:
            continue

        if isinstance(item, dict):

            if (
                "field" in item
                and "description" in item
            ):
                text = (
                    f"{item['field']}："
                    f"{item['description']}"
                )

            elif (
                "name" in item
                and "description" in item
            ):
                text = (
                    f"{item['name']}："
                    f"{item['description']}"
                )

            else:
                text = json.dumps(
                    item,
                    ensure_ascii=False
                )

        else:

            text = str(item)

        document.add_paragraph(
            text,
            style="List Bullet"
        )
def add_action_section(
    document,
    actions,
    button_descriptions
):

    if not actions:
        return

    document.add_heading(
        "畫面操作圖示",
        level=5
    )

    for index, action in enumerate(actions):

        image = action.get(
            "image"
        )

        if image:

            try:

                document.add_picture(
                    image,
                    width=Inches(0.35)
                )

            except Exception:

                pass

        description = ""

        for item in button_descriptions:

            if (
                item.get(
                    "button_index"
                )
                == index
            ):

                description = item.get(
                    "description",
                    ""
                )

                break

        document.add_paragraph(
            description
        )

        document.add_paragraph()

def add_internal_link(
    paragraph,
    text,
    bookmark_name
):

    hyperlink = OxmlElement(
        "w:hyperlink"
    )

    hyperlink.set(
        qn("w:anchor"),
        bookmark_name
    )

    run = OxmlElement("w:r")

    rPr = OxmlElement("w:rPr")

    color = OxmlElement(
        "w:color"
    )

    color.set(
        qn("w:val"),
        "0563C1"
    )

    underline = OxmlElement(
        "w:u"
    )

    underline.set(
        qn("w:val"),
        "single"
    )

    rPr.append(color)
    rPr.append(underline)

    run.append(rPr)

    text_elem = OxmlElement(
        "w:t"
    )

    text_elem.text = text

    run.append(text_elem)

    hyperlink.append(run)

    paragraph._p.append(
        hyperlink
    )

def group_pages(pages):

    result = {}

    for page in pages:

        category = page.get(
            "category",
            "Others"
        )

        page_name = page.get(
            "page",
            ""
        )

        result.setdefault(
            category,
            {}
        )

        result[
            category
        ].setdefault(
            page_name,
            []
        )

        result[
            category
        ][
            page_name
        ].append(
            page
        )

    return result


def add_cover(
    document,
    config
):

    document.add_heading(
        config["document"]["product_name"],
        level=0
    )

    document.add_paragraph(
        config["cover"]["subtitle"]
    )

    document.add_paragraph(
        config["document"]["title"]
    )

    document.add_paragraph(
        f"Version {config['document']['version']}"
    )

    document.add_paragraph(
        datetime.now().strftime(
            "%Y-%m-%d"
        )
    )

    document.add_page_break()


def add_document_info(
    document,
    config
):

    document.add_heading(
        "文件資訊",
        level=1
    )

    document.add_paragraph(
        f"產品名稱：{config['document']['product_name']}"
    )

    document.add_paragraph(
        f"版本：{config['document']['version']}"
    )

    document.add_paragraph(
        f"公司：{config['document']['company']}"
    )

    document.add_paragraph(
        f"產生日期：{datetime.now().strftime('%Y-%m-%d')}"
    )

    document.add_page_break()


def add_revision_history(
    document
):

    document.add_heading(
        "修訂紀錄",
        level=1
    )

    table = document.add_table(
        rows=2,
        cols=3
    )

    table.style = (
        "Table Grid"
    )

    table.cell(
        0,
        0
    ).text = "版本"

    table.cell(
        0,
        1
    ).text = "日期"

    table.cell(
        0,
        2
    ).text = "說明"

    table.cell(
        1,
        0
    ).text = "1.0"

    table.cell(
        1,
        1
    ).text = datetime.now().strftime(
        "%Y-%m-%d"
    )

    table.cell(
        1,
        2
    ).text = "文件首次產生"

    document.add_page_break()

def sanitize_bookmark_name(text):

    return (
        str(text)
        .replace(" ", "_")
        .replace("&", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("(", "_")
        .replace(")", "_")
    )
def add_introduction(
    document,
    config
):

    intro = config["introduction"]

    document.add_heading(
        "前言",
        level=1
    )

    document.add_heading(
        "文件目的",
        level=2
    )

    document.add_paragraph(
        intro["purpose"]
    )

    document.add_heading(
        "適用對象",
        level=2
    )

    for item in intro["audience"]:

        document.add_paragraph(
            item,
            style="List Bullet"
        )

    document.add_heading(
        "登入系統",
        level=2
    )

    document.add_paragraph(
        intro["login_guide"]
    )

    document.add_heading(
        "介面導覽",
        level=2
    )

    document.add_paragraph(
        intro["interface_overview"]
    )

    document.add_page_break()


def generate_docx():

    config = load_document_config()

    with open(
        "output/metadata.json",
        "r",
        encoding="utf-8"
    ) as f:

        pages = json.load(
            f
        )

    grouped = group_pages(
        pages
    )

    document = Document()

    add_cover(
        document,
        config
    )

    add_document_info(
        document,
        config
    )

    add_revision_history(
        document
    )
    generate_manual_toc(document, grouped)

    add_introduction(
        document,
        config
    )

    for category, page_dict in grouped.items():

        h = document.add_heading(
            category,
            level=1
        )

        add_bookmark(
            h,
            f"bookmark_{sanitize_bookmark_name(category)}"
        )

        rendered_pages = set()

        for page_name, items in page_dict.items():

            if (
                page_name
                and page_name not in rendered_pages
            ):
                h = document.add_heading(
                    page_name,
                    level=1
                )

                add_bookmark(
                    h,
                    f"bookmark_{sanitize_bookmark_name(page_name)}"
                )

                rendered_pages.add(
                    page_name
                )

            rendered_tabs = set()

            for page in items:

                tab = (
                    page.get("tab") or ""
                ).strip()

                if (
                    tab
                    and tab not in rendered_tabs
                ):
                    h = document.add_heading(
                        tab,
                        level=1
                    )

                    add_bookmark(
                        h,
                        f"bookmark_{sanitize_bookmark_name(page_name)}_{sanitize_bookmark_name(tab)}"
                    )

                    rendered_tabs.add(
                        tab
                    )

                try:

                    section = (
                        generate_manual_section(
                            page
                        )
                    )
                    add_action_section(
                        document,
                        page.get(
                            "actions",
                            []
                        ),
                        section.get(
                            "button_descriptions",
                            []
                        )
                    )
                    print(
                        page.get(
                            "actions",
                            []
                        )
                    )
                    print(
                        section.get(
                            "button_descriptions",
                            []
                        )
                    )
                    for heading, key in [
                        ("功能概述", "overview"),
                        ("使用價值", "business_value"),
                        ("畫面組成", "page_sections"),

                        ("欄位說明", "field_descriptions"),
                        ("操作流程", "workflow"),
                        ("建議", "best_practices"),
                        ("注意事項", "restrictions")
                    ]:

                        data = normalize_ai_content(
                            section.get(
                                key,
                                []
                            )
                        )

                        if not data:
                            continue

                        document.add_heading(
                            heading,
                            level=5
                        )

                        if isinstance(
                            data,
                            list
                        ):
                            add_bullet_list(
                                document,
                                data
                            )
                        else:
                            document.add_paragraph(
                                str(data)
                            )

                except Exception as e:

                    print(
                        f"AI內容產生失敗: {e}"
                    )

    document.add_page_break()

    document.add_heading(
        "附錄",
        level=1
    )

    document.add_paragraph(
        "本文件由 SENTRY Documentation Generator 自動產生。"
    )

    document.add_page_break()

    document.add_heading(
        config["document"]["classification"],
        level=0
    )

    document.add_paragraph(
        config["footer"]["copyright"]
    )

    document.save(
        "output/SENTRY_Manual.docx"
    )

    print(
        "✅ 已產生：output/SENTRY_Manual.docx"
    )