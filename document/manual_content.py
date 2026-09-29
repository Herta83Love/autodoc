"""Load human-editable page content overrides from YAML."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import re

import yaml


CONTENT_DIR = Path("config/manual_content")
CONTENT_FIELDS = (
    "overview",
    "business_value",
    "button_descriptions",
    "interaction_sections",
    "page_sections",
    "field_descriptions",
    "best_practices",
    "restrictions",
)


def manual_content_path(language):
    return CONTENT_DIR / f"{language}.yaml"


def page_content_key(page):
    key = str(page.get("page_key") or "").strip()
    if not key:
        raise ValueError("頁面缺少 page_key，無法對應 config/manual_content YAML。")
    return key


@lru_cache(maxsize=None)
def load_manual_content(language):
    path = manual_content_path(language)
    if not path.is_file():
        return {}

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    pages = config.get("pages") or {}
    if not isinstance(pages, dict):
        raise ValueError(f"{path} 的 pages 必須是 YAML mapping。")
    return pages


def apply_manual_content(page, generated_content):
    """Apply explicitly present YAML fields after AI/cache normalization."""

    language = str(page.get("language") or "zh-TW")
    entry = load_manual_content(language).get(page_content_key(page))
    if not entry:
        return generated_content

    content = entry.get("content") or {}
    if not isinstance(content, dict):
        raise ValueError(
            f"{manual_content_path(language)} 中 "
            f"{page_content_key(page)}.content 必須是 YAML mapping。"
        )

    result = deepcopy(generated_content)
    for field in CONTENT_FIELDS:
        if field in content:
            result[field] = deepcopy(content[field])

    # A later crawl may discover a previously hidden chart, record field, or
    # form action. Keep human-edited YAML authoritative for known items while
    # appending newly discovered structured items so crawler improvements are
    # visible immediately. Running sync_manual_content.py afterwards writes
    # those additions into YAML for future editing.
    for field in (
        "button_descriptions",
        "interaction_sections",
        "page_sections",
        "field_descriptions",
    ):
        if field in content:
            result[field] = merge_new_structured_items(
                result.get(field),
                generated_content.get(field),
            )
    return result


def merge_new_structured_items(edited, generated):
    edited = deepcopy(edited or [])
    generated = generated or []
    if not isinstance(edited, list) or not isinstance(generated, list):
        return edited

    def identity(item):
        if isinstance(item, dict):
            return str(item.get("action_id") or item.get("title") or "").strip()
        text = str(item or "").strip()
        return re.split(r"[：:]", text, maxsplit=1)[0].strip()

    known = {identity(item) for item in edited if identity(item)}
    for item in generated:
        key = identity(item)
        if key and key not in known:
            edited.append(deepcopy(item))
            known.add(key)
    return edited
