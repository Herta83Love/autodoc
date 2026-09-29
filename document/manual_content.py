"""Load human-editable page content overrides from YAML."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path

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
    return result
