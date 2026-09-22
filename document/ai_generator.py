# ============================================================================
# File: ai_generator.py
# ============================================================================

import json
import hashlib
import re
from pathlib import Path

import yaml

from services.vllm_service import (
    MODEL_NAME,
    assess_tab_equivalence,
    generate_manual_content,
    is_public_field_label,
)

CACHE_VERSION = "V6"

CACHE_DIR = Path("output/ai_cache")
AI_CONTENT_CORRECTIONS_CONFIG = Path("config/ai_content_corrections.yaml")

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def load_ai_content_corrections():
    if not AI_CONTENT_CORRECTIONS_CONFIG.is_file():
        return {}

    with AI_CONTENT_CORRECTIONS_CONFIG.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return config.get("replacements") or {}


def apply_ai_content_corrections(value, language):
    """Apply verified product facts without mutating the cached AI payload."""

    replacements = load_ai_content_corrections().get(language) or []

    if isinstance(value, dict):
        return {
            key: apply_ai_content_corrections(item, language)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            apply_ai_content_corrections(item, language)
            for item in value
        ]

    if isinstance(value, str):
        for replacement in replacements:
            old = str(replacement.get("from") or "")
            new = str(replacement.get("to") or "")
            if old:
                value = value.replace(old, new)

    return value

TAB_GROUP_CACHE_DIR = CACHE_DIR / "tab_groups"
TAB_GROUP_CACHE_DIR.mkdir(parents=True, exist_ok=True)


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
        "equivalent_tabs": page.get("equivalent_tabs", []),
        "equivalence_note": page.get("equivalence_note", ""),
        "descriptions": page.get("descriptions", []),
        "headings": page.get("headings", []),
        "fields": page.get("fields", []),
        "field_details": page.get("field_details", []),
        "tables": page.get("tables", []),
        "actions": [
            {
                "action_id": action.get("action_id"),
                "label": action.get("label"),
                "icon": action.get("icon"),
                "button_class": action.get("button_class"),
                "context_heading": action.get("context_heading"),
                "context_text": action.get("context_text"),
            }
            for action in page.get("actions", [])
        ],
        "help_actions": page.get("help_actions", []),
        "interaction_flows": page.get("interaction_flows", []),
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

    for flow in page.get("interaction_flows", []):
        for screenshot_path in flow.get("screenshots", []):
            _update_hash_from_file(hasher, screenshot_path)

    return hasher.hexdigest()


def _normalize_structure_value(value):
    """Remove instance values while retaining the public UI structure."""

    if isinstance(value, dict):
        return {
            key: _normalize_structure_value(value[key])
            for key in sorted(value)
            if key not in {
                "internal_name",
                "value",
                "checked",
                "selected",
                "image",
            }
        }

    if isinstance(value, list):
        return [_normalize_structure_value(item) for item in value]

    return str(value or "").strip()


def get_tab_structure_signature(page):
    """Return a conservative signature used only to select AI candidates."""

    structure = {
        "headings": page.get("headings", []),
        "field_details": page.get("field_details", []),
        "fields": page.get("fields", []),
        "tables": page.get("tables", []),
        "actions": [
            {
                "label": action.get("label", ""),
                "icon": action.get("icon", ""),
            }
            for action in page.get("actions", [])
        ],
    }
    encoded = json.dumps(
        _normalize_structure_value(structure),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _tab_group_fingerprint(pages):
    hasher = hashlib.sha256()
    summary = [
        {
            "language": page.get("language"),
            "category": page.get("category"),
            "page": page.get("page"),
            "tab": page.get("tab"),
            "signature": get_tab_structure_signature(page),
        }
        for page in pages
    ]
    hasher.update(
        json.dumps(summary, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )

    # The first two segments are sufficient for semantic comparison. Including
    # their bytes also prevents a stale decision after the UI changes.
    for page in pages:
        for screenshot_path in get_screenshot_paths(page)[:2]:
            _update_hash_from_file(hasher, screenshot_path)

    return hasher.hexdigest()


def _tab_group_cache_file(pages):
    page_name = pages[0].get("page") or "unknown"
    fingerprint = _tab_group_fingerprint(pages)[:16]
    filename = sanitize_filename(
        f"TAB_GROUP_V1_{MODEL_NAME}_{page_name}_{fingerprint}.json"
    )
    return TAB_GROUP_CACHE_DIR / filename


def _load_or_assess_tab_group(pages):
    cache_file = _tab_group_cache_file(pages)

    if cache_file.is_file():
        cached = load_cache(cache_file)
        if isinstance(cached, dict):
            print(f"📂 Tab Group Cache Hit: {cache_file.name}")
            return cached

    print(f"🤖 Assess equivalent tabs: {cache_file.name}")
    result = assess_tab_equivalence(pages)
    save_cache(cache_file, result)
    return result


def _split_bilingual_tab(tab):
    match = re.fullmatch(r"\s*(.*?)\s*（(.*?)）\s*", str(tab or ""))
    return match.groups() if match else (str(tab or "").strip(), "")


def _collapse_numbered_names(names, language="zh-TW"):
    """Collapse Rule 1/2/3-style names without inventing translated terms."""

    parsed = []
    for name in names:
        match = re.fullmatch(r"(.*?)(\d+)\s*", name)
        if not match:
            return ("、" if str(language).lower().startswith("zh") else ", ").join(names)
        parsed.append((match.group(1).rstrip(), int(match.group(2))))

    prefixes = {prefix.casefold() for prefix, _ in parsed}
    numbers = [number for _, number in parsed]
    if len(prefixes) != 1 or numbers != list(range(min(numbers), max(numbers) + 1)):
        return ("、" if str(language).lower().startswith("zh") else ", ").join(names)

    separator = "～" if str(language).lower().startswith("zh") else "–"
    return f"{parsed[0][0]} {min(numbers)}{separator}{max(numbers)}".strip()


def build_merged_tab_title(pages):
    tabs = [str(page.get("tab") or "").strip() for page in pages]
    local_names, english_names = zip(*[_split_bilingual_tab(tab) for tab in tabs])
    language = pages[0].get("language") or "zh-TW"
    local_title = _collapse_numbered_names(list(local_names), language)

    if all(english_names):
        english_title = _collapse_numbered_names(list(english_names), "en")
        if english_title.casefold() != local_title.casefold():
            return f"{local_title}（{english_title}）"

    return local_title


def collapse_equivalent_tabs(items):
    """Merge semantically equivalent tabs, defaulting safely to no merge."""

    signature_groups = {}
    for index, page in enumerate(items):
        tab = str(page.get("tab") or "").strip()
        if not tab:
            signature_groups.setdefault(("single", index), []).append((index, page))
            continue
        signature_groups.setdefault(get_tab_structure_signature(page), []).append(
            (index, page)
        )

    merged_by_first_index = {}
    consumed = set()

    for candidates in signature_groups.values():
        if len(candidates) < 2:
            continue

        candidate_pages = [page for _, page in candidates]
        candidate_tabs = [
            str(page.get("tab") or "").strip()
            for page in candidate_pages
        ]

        # Repeated crawler records for one tab are not separate UI instances.
        if len(set(candidate_tabs)) != len(candidate_tabs):
            continue

        try:
            decision = _load_or_assess_tab_group(candidate_pages)
            equivalent = decision.get("equivalent") is True
            confidence = float(decision.get("confidence", 0))
        except Exception as exc:
            print(f"頁籤等價判斷失敗，維持分開輸出：{exc}")
            continue

        if not equivalent or confidence < 0.80:
            continue

        first_index, representative = candidates[0]
        representative = dict(representative)
        representative["equivalent_tabs"] = [
            page.get("tab") for page in candidate_pages
        ]
        representative["equivalence_note"] = str(
            decision.get("difference_note") or ""
        ).strip()
        representative["tab"] = build_merged_tab_title(candidate_pages)
        merged_by_first_index[first_index] = representative
        consumed.update(index for index, _ in candidates[1:])

    result = []
    for index, page in enumerate(items):
        if index in consumed:
            continue
        result.append(merged_by_first_index.get(index, page))

    return result


def get_internal_field_mapping(page):

    mapping = {}

    for detail in page.get("field_details") or []:
        internal_name = str(detail.get("internal_name") or "").strip()
        section = str(detail.get("section") or "").strip()
        label = str(detail.get("label") or "").strip()

        if not internal_name or not label:
            continue

        # Avoid replacing ordinary words such as "action" inside prose, while
        # still catching camelCase names such as pwdComplexity and ntpStatus.
        is_code_name = (
            "_" in internal_name
            or internal_name.endswith("[]")
            or bool(re.search(r"[a-z][A-Z]", internal_name))
            or any(char in internal_name for char in ".{}[]/\\")
        )
        if not is_code_name:
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


def normalize_grounded_result(result, page):
    """Reject model output that cannot be tied back to public UI evidence."""

    if not isinstance(result, dict):
        raise ValueError("AI 結果必須是 JSON object")

    allowed_fields = set()
    for detail in page.get("field_details") or []:
        section = str(detail.get("section") or "").strip()
        label = str(detail.get("label") or "").strip()
        if not is_public_field_label(label):
            continue
        allowed_fields.add(f"{section}－{label}" if section else label)

    filtered_fields = []
    for item in result.get("field_descriptions") or []:
        text = str(item or "").strip()
        name = re.split(r"[：:]", text, maxsplit=1)[0].strip()
        if text and name in allowed_fields:
            filtered_fields.append(text)
    result["field_descriptions"] = filtered_fields

    allowed_sections = {
        str(value or "").strip()
        for value in page.get("headings") or []
        if str(value or "").strip()
    }
    allowed_sections.update(
        str(detail.get("section") or "").strip()
        for detail in page.get("field_details") or []
        if str(detail.get("section") or "").strip()
    )
    filtered_sections = []
    for item in result.get("page_sections") or []:
        text = str(item or "").strip()
        name = re.split(r"[：:]", text, maxsplit=1)[0].strip()
        if text and name in allowed_sections:
            filtered_sections.append(text)
    result["page_sections"] = filtered_sections

    valid_action_ids = {
        str(action.get("action_id") or f"button-{index}")
        for index, action in enumerate(page.get("actions") or [])
        if action.get("image")
    }
    filtered_buttons = []
    for item in result.get("button_descriptions") or []:
        if not isinstance(item, dict):
            continue
        action_id = str(item.get("action_id") or "").strip()
        description = str(item.get("description") or "").strip()
        try:
            confidence = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0
        if (
            item.get("include") is True
            and action_id in valid_action_ids
            and confidence >= 0.8
            and description
        ):
            filtered_buttons.append({
                "action_id": action_id,
                "include": True,
                "confidence": confidence,
                "description": description,
            })
    result["button_descriptions"] = filtered_buttons

    flows_by_id = {
        str(flow.get("action_id") or ""): flow
        for flow in page.get("interaction_flows") or []
        if flow.get("action_id")
    }
    model_interactions = {}
    for item in result.get("interaction_sections") or []:
        if not isinstance(item, dict):
            continue
        action_id = str(item.get("action_id") or "").strip()
        flow = flows_by_id.get(action_id)
        if not flow:
            continue
        model_interactions[action_id] = item

    interaction_sections = []
    for action_id, flow in flows_by_id.items():
        item = model_interactions.get(action_id, {})
        allowed_labels = {
            str(field.get("label") or "").strip()
            for field in flow.get("fields") or []
            if is_public_field_label(field.get("label"))
        }
        descriptions_by_label = {}
        for description in item.get("field_descriptions") or []:
            text = str(description or "").strip()
            name = re.split(r"[：:]", text, maxsplit=1)[0].strip()
            if text and name in allowed_labels:
                descriptions_by_label.setdefault(name, text)

        field_descriptions = []
        emitted_labels = set()
        for field in flow.get("fields") or []:
            label = str(field.get("label") or "").strip()
            if label not in allowed_labels or label in emitted_labels:
                continue
            emitted_labels.add(label)
            field_descriptions.append(
                descriptions_by_label.get(label)
                or _fallback_interaction_field_description(
                    field,
                    page.get("language", "zh-TW"),
                )
            )
        interaction_sections.append({
            "action_id": action_id,
            "title": str(item.get("title") or flow.get("title") or "").strip(),
            "overview": str(item.get("overview") or "").strip(),
            "field_descriptions": field_descriptions,
        })
    result["interaction_sections"] = interaction_sections

    # These sections are interpretations rather than UI facts. The review file
    # showed repeated unsupported claims about licensing, restart behavior,
    # system load, compliance and security effects. Without an authoritative
    # product specification there is no deterministic way to validate them.
    result["business_value"] = ""
    result["best_practices"] = []
    result["restrictions"] = []

    return result


def _fallback_interaction_field_description(field, language="zh-TW"):
    """Guarantee one conservative instruction for every captured form field."""

    label = str(field.get("label") or "").strip()
    field_type = str(field.get("type") or "").strip().lower()
    options = [
        str(option).strip()
        for option in field.get("options") or []
        if str(option).strip()
    ]
    placeholder = str(field.get("placeholder") or "").strip()
    minimum = str(field.get("min") or "").strip()
    maximum = str(field.get("max") or "").strip()
    accept = str(field.get("accept") or "").strip()
    required = field.get("required") is True
    english = str(language).lower().startswith("en")

    if english:
        if options:
            if len(options) <= 12:
                instruction = f"Select a value for {label}. Available options: {', '.join(options)}."
            else:
                instruction = f"Select a value for {label} from the options shown by the interface."
        elif field_type == "file":
            instruction = f"Select the file to upload for {label}."
        elif field_type in {"checkbox", "radio"}:
            instruction = f"Select the applicable setting for {label}."
        elif field_type in {"number", "range"} or minimum or maximum:
            instruction = f"Enter the numeric value for {label}."
        else:
            instruction = f"Enter the value for {label}."
        if placeholder:
            instruction += f" The interface hint is: {placeholder}."
        if minimum or maximum:
            bounds = " to ".join(value for value in (minimum, maximum) if value)
            instruction += f" Allowed range: {bounds}."
        if accept:
            instruction += f" Accepted file type: {accept}."
        if required:
            instruction += " This field is required."
        return f"{label}: {instruction}"

    if options:
        if len(options) <= 12:
            instruction = f"選擇「{label}」；可用選項包括：{'、'.join(options)}。"
        else:
            instruction = f"從畫面提供的選項中選擇「{label}」。"
    elif field_type == "file":
        instruction = f"選擇要上傳的「{label}」檔案。"
    elif field_type in {"checkbox", "radio"}:
        instruction = f"選擇「{label}」適用的設定。"
    elif field_type in {"number", "range"} or minimum or maximum:
        instruction = f"輸入「{label}」的數值。"
    else:
        instruction = f"輸入「{label}」的設定值。"
    if placeholder:
        instruction += f"畫面提示為：{placeholder}。"
    if minimum or maximum:
        bounds = " 至 ".join(value for value in (minimum, maximum) if value)
        instruction += f"允許範圍為 {bounds}。"
    if accept:
        instruction += f"可接受的檔案類型為 {accept}。"
    if required:
        instruction += "此欄位為必填。"
    return f"{label}：{instruction}"


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

        if cached_result and cached_result.get("status") != "error":
            internal_field_mapping = get_internal_field_mapping(page)
            cached_result = sanitize_internal_field_names(
                cached_result,
                internal_field_mapping
            )
            cached_result = normalize_grounded_result(cached_result, page)
            cached_result = apply_ai_content_corrections(
                cached_result,
                page.get("language", "zh-TW"),
            )
            assert_no_internal_field_names(
                cached_result,
                internal_field_mapping
            )
            return cached_result

        if cached_result and cached_result.get("status") == "error":
            print(
                f"⚠️ 忽略先前失敗的 AI Cache，重新產生: {cache_file.name}"
            )

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

        result = normalize_grounded_result(result, page)
        result = apply_ai_content_corrections(
            result,
            page.get("language", "zh-TW"),
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

        return result
