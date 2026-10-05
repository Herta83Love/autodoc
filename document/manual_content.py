"""Load human-editable page content overrides from YAML."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import re

import yaml


CONTENT_DIR = Path("output/manual_content")
DOCUMENT_CONFIG_PATH = Path("config/document.yaml")
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


LEGACY_RECORD_FIELD_PREFIX = re.compile(
    r"^\s*\d+\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*[－-]\s*"
)


def manual_content_path(language):
    return CONTENT_DIR / f"{language}.yaml"


def page_content_key(page):
    key = str(page.get("page_key") or "").strip()
    if not key:
        raise ValueError("頁面缺少 page_key，無法對應 output/manual_content YAML。")
    return key


def normalize_field_description_items(items):
    """Remove unstable record-number/timestamp prefixes from older YAML."""

    normalized = []
    known = set()
    for item in deepcopy(items or []):
        if isinstance(item, str):
            item = LEGACY_RECORD_FIELD_PREFIX.sub("", item).strip()
        identity = structured_item_identity(item)
        if identity and identity in known:
            continue
        if identity:
            known.add(identity)
        normalized.append(item)
    return normalized


def structured_item_identity(item):
    if isinstance(item, dict):
        return str(item.get("action_id") or item.get("title") or "").strip()
    text = str(item or "").strip()
    text = LEGACY_RECORD_FIELD_PREFIX.sub("", text)
    return re.split(r"[：:]", text, maxsplit=1)[0].strip()


@lru_cache(maxsize=None)
def load_manual_config(language):
    path = manual_content_path(language)
    if not path.is_file():
        return {}

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if not isinstance(config, dict):
        raise ValueError(f"{path} 的最外層必須是 YAML mapping。")
    return config


def load_manual_content(language):
    path = manual_content_path(language)
    config = load_manual_config(language)

    pages = config.get("pages") or {}
    if not isinstance(pages, dict):
        raise ValueError(f"{path} 的 pages 必須是 YAML mapping。")
    return pages


def _language_key(language):

    return "en" if str(language).lower().startswith("en") else "zh-TW"


def load_config_document():
    """Load the default preface stored in config/document.yaml."""

    if not DOCUMENT_CONFIG_PATH.is_file():
        return {}

    with DOCUMENT_CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if not isinstance(config, dict):
        raise ValueError(f"{DOCUMENT_CONFIG_PATH} 的最外層必須是 YAML mapping。")
    return config


def document_settings_from_config(language):
    """Return one language's preface from config/document.yaml."""

    raw = load_config_document()
    if not raw:
        return {}

    key = _language_key(language)
    locales = raw.get("locales") or {}
    localized = locales.get(key) if isinstance(locales, dict) else None

    # locales.<language> may be a complete document shell. A partial locale
    # only overrides the shared top-level sections from older files.
    if isinstance(localized, dict) and localized.get("document") and localized.get("introduction"):
        return deepcopy(localized)

    if not isinstance(raw.get("document"), dict):
        return {}

    resolved = deepcopy(raw)
    resolved.pop("locales", None)
    if isinstance(localized, dict):
        resolved.update(localized)
    return resolved


def load_output_document_settings(language):
    """Return document_config from the output manual YAML, if present."""

    path = manual_content_path(language)
    settings = load_manual_config(language).get("document_config") or {}
    if not isinstance(settings, dict):
        raise ValueError(f"{path} 的 document_config 必須是 YAML mapping。")
    return settings


def load_document_settings(language):
    """Load the preface, preferring output when it differs from config."""

    key = _language_key(language)
    base = document_settings_from_config(language)
    output_settings = load_output_document_settings(language)
    output_path = manual_content_path(language)

    if output_settings and output_settings != base:
        print(
            f"{key}: output 的文件前言與 config/document.yaml 不一致，"
            f"改以 {output_path.as_posix()} 為準"
        )
        return deepcopy(output_settings)

    if not base:
        raise ValueError(
            "找不到文件前言。請在 config/document.yaml 提供內容，"
            f"或在 {output_path.as_posix()} 提供 document_config。"
        )

    if output_settings:
        print(f"{key}: 文件前言與 config/document.yaml 一致")
    else:
        print(f"{key}: 使用 config/document.yaml 的文件前言")
    return deepcopy(base)


def load_ai_content_corrections(language):
    """Load deterministic prose replacements from the unified YAML."""

    path = manual_content_path(language)
    replacements = load_manual_config(language).get("ai_content_corrections") or []
    if not isinstance(replacements, list):
        raise ValueError(f"{path} 的 ai_content_corrections 必須是陣列。")
    return deepcopy(replacements)


def load_page_note_entries(language):
    """Load reader-facing page notes from the unified YAML."""

    path = manual_content_path(language)
    entries = load_manual_config(language).get("page_notes") or []
    if not isinstance(entries, list):
        raise ValueError(f"{path} 的 page_notes 必須是陣列。")
    return deepcopy(entries)


def load_page_overviews(language):
    """Load one shared overview for each multi-tab feature page."""

    path = manual_content_path(language)
    overviews = load_manual_config(language).get("page_overviews") or {}
    if not isinstance(overviews, dict):
        raise ValueError(f"{path} 的 page_overviews 必須是 YAML mapping。")
    return deepcopy(overviews)


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
            value = deepcopy(content[field])
            if field == "field_descriptions":
                value = normalize_field_description_items(value)
            result[field] = value

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
            edited = result.get(field)
            generated = generated_content.get(field)
            if field == "field_descriptions":
                edited = normalize_field_description_items(edited)
                generated = normalize_field_description_items(generated)
            result[field] = merge_new_structured_items(
                edited,
                generated,
            )
    return result


def merge_new_structured_items(edited, generated):
    edited = deepcopy(edited or [])
    generated = generated or []
    if not isinstance(edited, list) or not isinstance(generated, list):
        return edited

    known = {
        structured_item_identity(item)
        for item in edited
        if structured_item_identity(item)
    }
    for item in generated:
        key = structured_item_identity(item)
        if key and key not in known:
            edited.append(deepcopy(item))
            known.add(key)
    return edited
