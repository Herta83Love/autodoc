# ============================================================================
# File: ai_generator.py
# ============================================================================

import json
from pathlib import Path

from services.azure_openai_service import (
    generate_manual_content
)

CACHE_VERSION = "v7"

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


def get_cache_file(page):

    page_name = page.get(
        "page",
        "unknown"
    )

    tab_name = page.get(
        "tab"
    )

    if tab_name:

        filename = (
            f"{CACHE_VERSION}_"
            f"{MODEL_NAME}_"
            f"{page_name}_{tab_name}.json"
        )

    else:

        filename = (
            f"{CACHE_VERSION}_"
            f"{MODEL_NAME}_"
            f"{page_name}.json"
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
            "status": "error",
            "error": str(e),
            "purpose": "",
            "usage_scenarios": [],
            "key_functions": [],
            "field_descriptions": [],
            "operation_steps": [],
            "best_practices": [],
            "notes": []
        }

        save_cache(
            cache_file,
            result
        )

        return result