# ============================================================================
# File: manual_generator.py
# ============================================================================

import json
import yaml
import ast
import re
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from document.ai_generator import (
    generate_manual_section
)

bookmark_id = 1
DOCUMENT_CONFIG = (
    "config/document.yaml"
)

ASSET_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSET_DIR / "urmazi_logo.png"
COVER_CHARACTERS_PATH = ASSET_DIR / "sentry_cover_characters.png"

BRAND_BLUE = RGBColor(31, 101, 133)
BRAND_GREEN = RGBColor(112, 173, 71)
BRAND_ORANGE = RGBColor(247, 170, 20)
PALE_BLUE = RGBColor(227, 238, 242)
TEXT_BLACK = RGBColor(0, 0, 0)
MUTED_GRAY = RGBColor(100, 100, 100)
LIGHT_GRAY = "D9D9D9"


def set_run_font(
    run,
    name="Inter",
    size=None,
    color=None,
    bold=None,
    italic=None
):

    run.font.name = name

    if run._element.get_or_add_rPr().rFonts is None:
        run._element.get_or_add_rPr().get_or_add_rFonts()

    run._element.rPr.rFonts.set(qn("w:ascii"), name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), name)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")

    if size is not None:
        run.font.size = Pt(size)

    if color is not None:
        run.font.color.rgb = color

    if bold is not None:
        run.bold = bold

    if italic is not None:
        run.italic = italic


def add_field(run, instruction):

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    field_code = OxmlElement("w:instrText")
    field_code.set(qn("xml:space"), "preserve")
    field_code.text = instruction

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    run._r.extend([begin, field_code, separate, end])


def add_paragraph_top_border(paragraph, color=LIGHT_GRAY, size="4"):

    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))

    if borders is None:
        borders = OxmlElement("w:pBdr")
        p_pr.append(borders)

    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), size)
    top.set(qn("w:space"), "6")
    top.set(qn("w:color"), color)
    borders.append(top)


def configure_document_styles(document):

    background = document._element.find(qn("w:background"))

    if background is None:
        background = OxmlElement("w:background")
        document._element.insert(0, background)

    background.set(qn("w:color"), "FFFFFF")

    normal = document.styles["Normal"]
    normal.font.name = "Inter"
    normal.font.size = Pt(10)
    normal.font.color.rgb = TEXT_BLACK
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Inter")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Inter")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(4)

    heading_tokens = {
        "Heading 1": (18, TEXT_BLACK, 12, 4),
        "Heading 2": (14, TEXT_BLACK, 10, 2),
        "Heading 3": (11.5, TEXT_BLACK, 8, 2),
        "Heading 4": (10.5, TEXT_BLACK, 6, 2),
        "Heading 5": (10, TEXT_BLACK, 6, 2)
    }

    for name, (size, color, before, after) in heading_tokens.items():

        style = document.styles[name]
        style.font.name = "Inter"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = color
        style._element.rPr.rFonts.set(qn("w:ascii"), "Inter")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Inter")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for name, left, size in [
        ("TOC 1", Cm(0), 10.5),
        ("TOC 2", Cm(0.55), 10),
        ("TOC 3", Cm(1.1), 9.5)
    ]:

        try:
            style = document.styles[name]
        except KeyError:
            continue

        style.font.name = "Inter"
        style.font.size = Pt(size)
        style.font.color.rgb = TEXT_BLACK
        style.paragraph_format.left_indent = left
        style.paragraph_format.space_after = Pt(2)


def enforce_white_background_black_text(document):
    """Write explicit white/black colors across every Word story and style."""

    background = document._element.find(qn("w:background"))

    if background is None:
        background = OxmlElement("w:background")
        document._element.insert(0, background)

    background.set(qn("w:color"), "FFFFFF")
    background.attrib.pop(qn("w:themeColor"), None)
    background.attrib.pop(qn("w:themeTint"), None)
    background.attrib.pop(qn("w:themeShade"), None)

    def force_run_black(run_element):
        r_pr = run_element.find(qn("w:rPr"))

        if r_pr is None:
            r_pr = OxmlElement("w:rPr")
            run_element.insert(0, r_pr)

        color = r_pr.find(qn("w:color"))

        if color is None:
            color = OxmlElement("w:color")
            r_pr.append(color)

        color.set(qn("w:val"), "000000")
        color.attrib.pop(qn("w:themeColor"), None)
        color.attrib.pop(qn("w:themeTint"), None)
        color.attrib.pop(qn("w:themeShade"), None)

    story_roots = [document._element]

    for section in document.sections:
        story_roots.extend([
            section.header._element,
            section.first_page_header._element,
            section.even_page_header._element,
            section.footer._element,
            section.first_page_footer._element,
            section.even_page_footer._element,
        ])

    seen_roots = set()

    for root in story_roots:
        root_id = id(root)

        if root_id in seen_roots:
            continue

        seen_roots.add(root_id)

        for run_element in root.iter(qn("w:r")):
            force_run_black(run_element)

        for shading in root.iter(qn("w:shd")):
            shading.set(qn("w:val"), "clear")
            shading.set(qn("w:color"), "auto")
            shading.set(qn("w:fill"), "FFFFFF")
            shading.attrib.pop(qn("w:themeFill"), None)
            shading.attrib.pop(qn("w:themeFillTint"), None)
            shading.attrib.pop(qn("w:themeFillShade"), None)

        for cell_properties in root.iter(qn("w:tcPr")):
            if cell_properties.find(qn("w:shd")) is None:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:val"), "clear")
                shading.set(qn("w:color"), "auto")
                shading.set(qn("w:fill"), "FFFFFF")
                cell_properties.append(shading)

        for highlight in root.iter(qn("w:highlight")):
            highlight.set(qn("w:val"), "none")

    styles_root = document.styles._element

    for style in styles_root.iter(qn("w:style")):
        r_pr = style.find(qn("w:rPr"))

        if r_pr is None:
            r_pr = OxmlElement("w:rPr")
            style.append(r_pr)

        color = r_pr.find(qn("w:color"))

        if color is None:
            color = OxmlElement("w:color")
            r_pr.append(color)

        color.set(qn("w:val"), "000000")
        color.attrib.pop(qn("w:themeColor"), None)
        color.attrib.pop(qn("w:themeTint"), None)
        color.attrib.pop(qn("w:themeShade"), None)

    for color in styles_root.iter(qn("w:color")):
        color.set(qn("w:val"), "000000")
        color.attrib.pop(qn("w:themeColor"), None)
        color.attrib.pop(qn("w:themeTint"), None)
        color.attrib.pop(qn("w:themeShade"), None)

    for shading in styles_root.iter(qn("w:shd")):
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:color"), "auto")
        shading.set(qn("w:fill"), "FFFFFF")
        shading.attrib.pop(qn("w:themeFill"), None)
        shading.attrib.pop(qn("w:themeFillTint"), None)
        shading.attrib.pop(qn("w:themeFillShade"), None)

    for highlight in styles_root.iter(qn("w:highlight")):
        highlight.set(qn("w:val"), "none")

    doc_defaults = styles_root.find(qn("w:docDefaults"))

    if doc_defaults is not None:
        r_pr_default = doc_defaults.find(qn("w:rPrDefault"))

        if r_pr_default is None:
            r_pr_default = OxmlElement("w:rPrDefault")
            doc_defaults.append(r_pr_default)

        r_pr = r_pr_default.find(qn("w:rPr"))

        if r_pr is None:
            r_pr = OxmlElement("w:rPr")
            r_pr_default.append(r_pr)

        color = r_pr.find(qn("w:color"))

        if color is None:
            color = OxmlElement("w:color")
            r_pr.append(color)

        color.set(qn("w:val"), "000000")
        color.attrib.pop(qn("w:themeColor"), None)
        color.attrib.pop(qn("w:themeTint"), None)
        color.attrib.pop(qn("w:themeShade"), None)


def configure_page(section):

    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(1.9)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)
    section.header_distance = Cm(0.45)
    section.footer_distance = Cm(0.55)


def clear_container(container):

    for paragraph in container.paragraphs:
        paragraph._element.getparent().remove(paragraph._element)

    for table in container.tables:
        table._element.getparent().remove(table._element)


def set_branded_header_footer(section):

    configure_page(section)

    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    clear_container(section.header)
    clear_container(section.footer)

    header_p = section.header.add_paragraph()
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_p.paragraph_format.space_after = Pt(4)

    if LOGO_PATH.exists():
        header_p.add_run().add_picture(
            str(LOGO_PATH),
            width=Inches(1.35)
        )

    footer_p = section.footer.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer_p.paragraph_format.space_before = Pt(4)
    add_paragraph_top_border(footer_p)

    section_run = footer_p.add_run()
    add_field(section_run, ' STYLEREF "Heading 1" ')
    set_run_font(section_run, size=8.5, color=MUTED_GRAY)

    divider = footer_p.add_run("  |  ")
    set_run_font(divider, size=8.5, color=MUTED_GRAY)

    page_run = footer_p.add_run()
    add_field(page_run, " PAGE ")
    set_run_font(page_run, size=8.5, color=MUTED_GRAY, bold=True)


def set_blank_header_footer(section):

    configure_page(section)
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    clear_container(section.header)
    clear_container(section.footer)
    section.header.add_paragraph()
    section.footer.add_paragraph()
def enable_field_updates(document):

    settings = document.settings._element
    update_fields = settings.find(qn("w:updateFields"))

    if update_fields is None:
        update_fields = OxmlElement("w:updateFields")
        settings.append(update_fields)

    update_fields.set(qn("w:val"), "true")


def generate_manual_toc(document, grouped):

    title = document.add_paragraph()
    title.paragraph_format.space_before = Pt(8)
    title.paragraph_format.space_after = Pt(24)
    title_run = title.add_run("目錄 / TABLE OF CONTENTS")
    set_run_font(
        title_run,
        size=18,
        color=TEXT_BLACK,
        bold=True
    )

    for category, page_dict in grouped.items():

        category_p = document.add_paragraph()
        category_p.paragraph_format.space_before = Pt(6)
        category_p.paragraph_format.space_after = Pt(2)
        add_internal_link(
            category_p,
            category,
            f"bookmark_{sanitize_bookmark_name(category)}",
            color="000000",
            underline=False,
            bold=True,
            size=11
        )

        for page_name, items in page_dict.items():

            page_p = document.add_paragraph()
            page_p.paragraph_format.left_indent = Cm(0.55)
            page_p.paragraph_format.space_after = Pt(1)
            add_internal_link(
                page_p,
                page_name,
                f"bookmark_{sanitize_bookmark_name(page_name)}",
                color="000000",
                underline=False,
                size=10
            )

            rendered_tabs = set()

            for page in items:

                tab = (page.get("tab") or "").strip()

                if not tab or tab in rendered_tabs:
                    continue

                tab_p = document.add_paragraph()
                tab_p.paragraph_format.left_indent = Cm(1.15)
                tab_p.paragraph_format.space_after = Pt(1)
                add_internal_link(
                    tab_p,
                    tab,
                    f"bookmark_{sanitize_bookmark_name(page_name)}_{sanitize_bookmark_name(tab)}",
                    color="404040",
                    underline=False,
                    size=9.5
                )
                rendered_tabs.add(tab)

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

    descriptions = {}

    for item in button_descriptions or []:

        if not isinstance(item, dict):
            continue

        description = str(item.get("description") or "").strip()
        index = item.get("button_index")

        if description and isinstance(index, int):
            descriptions[index] = description

    renderable_actions = []

    for index, action in enumerate(actions):

        image = action.get("image")
        description = descriptions.get(index)

        if not image or not description or not Path(image).is_file():
            continue

        renderable_actions.append((image, description))

    if not renderable_actions:
        return

    document.add_heading(
        "畫面操作圖示",
        level=5
    )

    for image, description in renderable_actions:

        image_p = document.add_paragraph()
        image_p.paragraph_format.space_before = Pt(3)
        image_p.paragraph_format.space_after = Pt(2)

        try:
            image_p.add_run().add_picture(
                image,
                width=Inches(0.68)
            )
        except Exception as exc:
            print(f"按鈕圖片加入失敗: {image}: {exc}")
            continue

        description_p = document.add_paragraph(description)
        description_p.paragraph_format.left_indent = Cm(0.15)
        description_p.paragraph_format.space_after = Pt(6)

def add_internal_link(
    paragraph,
    text,
    bookmark_name,
    color="0563C1",
    underline=True,
    bold=False,
    size=None
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

    color_element = OxmlElement(
        "w:color"
    )

    color_element.set(
        qn("w:val"),
        color
    )

    underline_element = OxmlElement(
        "w:u"
    )

    underline_element.set(
        qn("w:val"),
        "single" if underline else "none"
    )

    rPr.append(color_element)
    rPr.append(underline_element)

    if bold:
        bold_element = OxmlElement("w:b")
        rPr.append(bold_element)

    if size is not None:
        size_element = OxmlElement("w:sz")
        size_element.set(qn("w:val"), str(int(size * 2)))
        rPr.append(size_element)

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

    section = document.sections[0]
    section.top_margin = Cm(0.8)
    section.bottom_margin = Cm(0)
    section.left_margin = Cm(1.35)
    section.right_margin = Cm(1.35)
    set_blank_header_footer(section)
    section.top_margin = Cm(0.8)
    section.bottom_margin = Cm(0)
    section.left_margin = Cm(1.35)
    section.right_margin = Cm(1.35)

    logo_p = document.add_paragraph()
    logo_p.paragraph_format.space_after = Pt(24)

    if LOGO_PATH.exists():
        logo_p.add_run().add_picture(
            str(LOGO_PATH),
            width=Inches(1.7)
        )

    title_p = document.add_paragraph()
    title_p.paragraph_format.space_after = Pt(2)
    title_run = title_p.add_run(
        f"{config['document']['product_name']} PDNS"
    )
    set_run_font(
        title_run,
        size=31,
        color=BRAND_BLUE,
        bold=True
    )

    subtitle_p = document.add_paragraph()
    subtitle_p.paragraph_format.space_after = Pt(7)
    subtitle_run = subtitle_p.add_run(
        config["cover"]["subtitle"]
    )
    set_run_font(
        subtitle_run,
        size=22,
        color=BRAND_BLUE
    )

    version_p = document.add_paragraph()
    version_p.paragraph_format.space_after = Pt(12)
    version_run = version_p.add_run(
        f"Version {config['document']['version']}  |  "
        f"{datetime.now().strftime('%Y-%m-%d')}"
    )
    set_run_font(
        version_run,
        size=9.5,
        color=MUTED_GRAY
    )

    art_p = document.add_paragraph()
    art_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    art_p.paragraph_format.space_before = Pt(2)
    art_p.paragraph_format.space_after = Pt(0)

    if COVER_CHARACTERS_PATH.exists():
        art_p.add_run().add_picture(
            str(COVER_CHARACTERS_PATH),
            width=Inches(7.0)
        )


def add_document_info(
    document,
    config
):

    document.add_heading("文件資訊", level=1)

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

    publication = config["publication"]

    notice = document.add_paragraph()
    notice.paragraph_format.space_before = Pt(18)
    notice_run = notice.add_run(publication["notice_title"])
    set_run_font(notice_run, size=14, color=TEXT_BLACK, bold=True)

    document.add_paragraph(
        publication["change_notice"]
    )

    document.add_paragraph(
        publication["trademark_notice"]
    )

    support = document.add_paragraph()
    support.add_run("文件意見與技術支援：").bold = True
    support.add_run(publication["support_url"])

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

    table.autofit = False

    for cell, width in zip(table.rows[0].cells, [Cm(2.5), Cm(3.5), Cm(10)]):
        cell.width = width

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

    for row in table.rows:
        for cell, width in zip(row.cells, [Cm(2.5), Cm(3.5), Cm(10)]):
            cell.width = width

    for cell in table.rows[0].cells:
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "FFFFFF")
        cell._tc.get_or_add_tcPr().append(shading)

        for run in cell.paragraphs[0].runs:
            set_run_font(
                run,
                size=9.5,
                color=TEXT_BLACK,
                bold=True
            )

    for cell in table.rows[1].cells:
        for run in cell.paragraphs[0].runs:
            set_run_font(run, size=9.5, color=TEXT_BLACK)

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


def add_back_cover(document, config):

    back_cover = config["back_cover"]
    publication = config["publication"]

    logo_p = document.add_paragraph()
    logo_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    logo_p.paragraph_format.space_after = Pt(110)

    if LOGO_PATH.exists():
        logo_p.add_run().add_picture(
            str(LOGO_PATH),
            width=Inches(1.65)
        )

    brand_p = document.add_paragraph()
    brand_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    brand_p.paragraph_format.space_after = Pt(10)
    brand_run = brand_p.add_run("SENTRY PDNS")
    set_run_font(
        brand_run,
        size=28,
        color=BRAND_BLUE,
        bold=True
    )

    thanks_p = document.add_paragraph()
    thanks_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    thanks_p.paragraph_format.space_after = Pt(36)
    thanks_run = thanks_p.add_run(back_cover["thank_you"])
    set_run_font(thanks_run, size=14, color=TEXT_BLACK)

    support_p = document.add_paragraph()
    support_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    support_run = support_p.add_run(back_cover["support_label"])
    set_run_font(support_run, size=10, color=MUTED_GRAY, bold=True)

    link_p = document.add_paragraph()
    link_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    link_p.paragraph_format.space_after = Pt(110)
    link_run = link_p.add_run(publication["support_url"])
    set_run_font(link_run, size=10.5, color=BRAND_BLUE)

    sentry_p = document.add_paragraph()
    sentry_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sentry_p.paragraph_format.space_after = Pt(16)
    sentry_run = sentry_p.add_run("SENTRY")
    set_run_font(sentry_run, size=46, color=PALE_BLUE, bold=True)

    copyright_p = document.add_paragraph()
    copyright_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    copyright_run = copyright_p.add_run(
        config["footer"]["copyright"]
    )
    set_run_font(copyright_run, size=8.5, color=MUTED_GRAY)


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

    enable_field_updates(document)
    configure_document_styles(document)

    add_cover(
        document,
        config
    )

    body_section = document.add_section(
        WD_SECTION.NEW_PAGE
    )
    set_branded_header_footer(body_section)

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
                    level=2
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
                        level=3
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

    document.add_heading(
        "附錄",
        level=1
    )

    document.add_paragraph(
        "本文件由 SENTRY Documentation Generator 自動產生。"
    )

    back_section = document.add_section(
        WD_SECTION.NEW_PAGE
    )
    set_blank_header_footer(back_section)
    back_section.top_margin = Cm(1.2)
    back_section.bottom_margin = Cm(1.2)
    add_back_cover(document, config)

    enforce_white_background_black_text(document)

    document.save(
        "output/SENTRY_Manual.docx"
    )

    print(
        "✅ 已產生：output/SENTRY_Manual.docx"
    )
