# ============================================================================
# File: ai_generator.py
# ============================================================================

import json
import hashlib
from pathlib import Path

from services.vllm_service import (
    MODEL_NAME,
    generate_manual_content,
)

CACHE_VERSION = "V2.1"

CACHE_DIR = Path("output/ai_cache")

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def sanitize_filename(filename):
    return (
        filename
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )


def _update_hash_from_file(hasher, path):

    if not path:
        return

    file_path = Path(path)

    if not file_path.is_file():
        return

    with file_path.open("rb") as f:

        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)


def get_screenshot_paths(page):

    paths = page.get("screenshots") or []

    if not paths and page.get("screenshot"):
        paths = [page.get("screenshot")]

    return [path for path in paths if path]


def get_content_fingerprint(page):

    relevant_page_data = {
        "language": page.get("language"),
        "category": page.get("category"),
        "page": page.get("page"),
        "tab": page.get("tab"),
        "descriptions": page.get("descriptions", []),
        "headings": page.get("headings", []),
        "fields": page.get("fields", []),
        "field_details": page.get("field_details", []),
        "tables": page.get("tables", []),
        "actions": [
            {
                "label": action.get("label"),
                "icon": action.get("icon")
            }
            for action in page.get("actions", [])
        ]
    }

    hasher = hashlib.sha256()
    hasher.update(
        json.dumps(
            relevant_page_data,
            ensure_ascii=False,
            sort_keys=True
        ).encode("utf-8")
    )

    for screenshot_path in get_screenshot_paths(page):
        _update_hash_from_file(hasher, screenshot_path)

    for action in page.get("actions", []):
        _update_hash_from_file(hasher, action.get("image"))

    return hasher.hexdigest()


def get_internal_field_mapping(page):

    mapping = {}

    for detail in page.get("field_details") or []:
        internal_name = str(detail.get("internal_name") or "").strip()
        section = str(detail.get("section") or "").strip()
        label = str(detail.get("label") or "").strip()

        if not internal_name or not label:
            continue

        # Avoid replacing ordinary words such as "action" inside prose.
        if "_" not in internal_name and not internal_name.endswith("[]"):
            continue

        mapping[internal_name] = (
            f"{section}－{label}"
            if section
            else label
        )

    return mapping


def sanitize_internal_field_names(value, mapping):

    if isinstance(value, dict):
        return {
            key: sanitize_internal_field_names(item, mapping)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            sanitize_internal_field_names(item, mapping)
            for item in value
        ]

    if isinstance(value, str):
        for internal_name in sorted(mapping, key=len, reverse=True):
            value = value.replace(internal_name, mapping[internal_name])

    return value


def assert_no_internal_field_names(value, mapping):

    serialized = json.dumps(value, ensure_ascii=False)
    remaining = [
        internal_name
        for internal_name in mapping
        if internal_name in serialized
    ]

    if remaining:
        raise ValueError(
            "AI 結果仍包含內部欄位名稱："
            + ", ".join(sorted(remaining))
        )


def get_cache_file(page):

    page_name = page.get(
        "page",
        "unknown"
    )

    tab_name = page.get(
        "tab"
    )

    fingerprint = get_content_fingerprint(page)[:16]

    if tab_name:

        filename = (
            f"{CACHE_VERSION}_"
            f"{MODEL_NAME}_"
            f"{page_name}_{tab_name}_{fingerprint}.json"
        )

    else:

        filename = (
            f"{CACHE_VERSION}_"
            f"{MODEL_NAME}_"
            f"{page_name}_{fingerprint}.json"
        )

    filename = sanitize_filename(
        filename
    )

    return CACHE_DIR / filename


def load_cache(cache_file):

    try:

        with open(
            cache_file,
            "r",
            encoding="utf-8"
        ) as f:

            cache_data = json.load(f)

        if (
            isinstance(cache_data, dict)
            and "result" in cache_data
        ):
            return cache_data["result"]

        return cache_data

    except Exception as e:

        print("讀取 AI Cache 失敗")
        print(e)

        return None


def save_cache(
    cache_file,
    result
):

    try:

        cache_data = {
            "version": CACHE_VERSION,
            "model": MODEL_NAME,
            "result": result
        }

        with open(
            cache_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                cache_data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print("寫入 AI Cache 失敗")
        print(e)


def generate_manual_section(page):

    cache_file = get_cache_file(page)

    #
    # Cache Hit
    #
    if cache_file.exists():

        print(
            f"📂 AI Cache Hit: {cache_file.name}"
        )

        cached_result = load_cache(
            cache_file
        )

        if cached_result:
            return cached_result

    #
    # Cache Miss
    #
    print(
        f"🤖 Generate AI: {cache_file.name}"
    )

    try:

        result = generate_manual_content(
            page,
            get_screenshot_paths(page)
        )

        internal_field_mapping = get_internal_field_mapping(page)

        result = sanitize_internal_field_names(
            result,
            internal_field_mapping
        )

        assert_no_internal_field_names(
            result,
            internal_field_mapping
        )

        save_cache(
            cache_file,
            result
        )

        return result

    except Exception as e:

        print(
            "vLLM 呼叫失敗"
        )

        print(e)

        result = {
            "overview": "",
            "business_value": "",
            "button_descriptions": [],
            "page_sections": [],
            "field_descriptions": [],
            "best_practices": [],
            "restrictions": [],
            "status": "error",
            "error": str(e)
        }

        save_cache(
            cache_file,
            result
        )

        return result
