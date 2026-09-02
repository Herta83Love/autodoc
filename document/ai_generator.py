# ============================================================================
# File: ai_generator.py
# ============================================================================

import json
import hashlib
from pathlib import Path

from services.azure_openai_service import (
    generate_manual_content
)

CACHE_VERSION = "V2"

MODEL_NAME = "gpt-4.1-mini"

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


def get_content_fingerprint(page):

    relevant_page_data = {
        "category": page.get("category"),
        "page": page.get("page"),
        "tab": page.get("tab"),
        "descriptions": page.get("descriptions", []),
        "headings": page.get("headings", []),
        "fields": page.get("fields", []),
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

    _update_hash_from_file(hasher, page.get("screenshot"))

    for action in page.get("actions", []):
        _update_hash_from_file(hasher, action.get("image"))

    return hasher.hexdigest()


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
            page.get("screenshot")
        )

        save_cache(
            cache_file,
            result
        )

        return result

    except Exception as e:

        print(
            "Azure OpenAI 呼叫失敗"
        )

        print(e)

        result = {
            "overview": "",
            "business_value": "",
            "button_descriptions": [],
            "page_sections": [],
            "field_descriptions": [],
            "workflow": [],
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
