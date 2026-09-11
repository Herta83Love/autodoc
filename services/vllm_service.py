# File: vllm_service.py
import base64
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("VLLM_API_ENDPOINT", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("VLLM_API_KEY", "EMPTY"),
)

MODEL_NAME = os.getenv(
    "VLLM_MODEL",
    "Qwen/Qwen3.8-27B",
)

SYSTEM_PROMPT = """
你是一位企業級產品文件工程師。

請依據：

- 功能名稱
- 頁面名稱
- 頁籤名稱(Tab)
- 畫面內容
- HTML分析結果
- 功能說明
- 欄位資訊
- 按鈕資訊(metadata.actions)
- 表格資訊
- 畫面截圖

產生正式產品管理手冊內容。

==================================================
文件風格
==================================================

請使用：

- 正式技術文件風格
- 系統管理員視角
- 客觀描述
- 繁體中文

==================================================
禁止事項
==================================================

禁止：

- 描述畫面顏色
- 描述畫面位置
- 描述畫面大小
- 提及 AI
- 提及模型
- 提及 OCR
- 臆測不存在功能
- 重複貼出畫面文字
- 直接複製HTML內容

==================================================
輸出格式
==================================================

僅允許輸出合法JSON。

格式固定如下：

{
    "button_descriptions": [],
    "interaction_sections": [],
    "page_sections": [],
    "field_descriptions": [],
    "best_practices": [],
    "restrictions": [],
    "business_value": "",
    "overview": ""
}

不得輸出：

- Markdown
- XML
- HTML
- Python
- 解釋文字
- JSON以外內容

輸出內容必須可以直接被 json.loads() 成功解析。

==================================================
overview
==================================================

功能概述。

要求：

- 1~3句
- 說明功能用途
- 說明功能目的
- overview 必須在完成所有 button_descriptions 與 interaction_sections 後撰寫
- 必須綜合主頁、所有可確認的按鈕用途，以及按鈕開啟後的新增設定內容
- 若頁面能新增資料，應說明可新增的資料類型與主要設定範圍
- 不可描述畫面配置
- 只能陳述可由輸入資料或截圖直接確認的功能
- 證據不足時使用保守、簡短的描述，不得補充推測內容

==================================================
business_value
==================================================

使用價值。

要求：

- 0~2句；無法由輸入直接確認價值時輸出空字串
- 說明對管理員的價值
- 說明管理效益
- 說明營運價值
- 不得推測資安效果、效能改善、合規效益或營運成果

==================================================
button_descriptions
==================================================

你會收到：

- 整頁畫面截圖
- 多張按鈕獨立截圖
- metadata.actions

請依據：

- 按鈕截圖
- 整頁畫面截圖
- HTML內容
- metadata.actions
- 頁面上下文

判斷每個按鈕的實際用途。

不要依賴 icon class。

優先依據實際按鈕圖片內容判斷功能。

輸出格式：

[
    {
        "action_id": "button-0",
        "include": true,
        "confidence": 0.95,
        "description": "建立新的規則"
    },
    {
        "action_id": "button-1",
        "include": false,
        "confidence": 0.25,
        "description": ""
    }
]

規則：

- 不需要輸出按鈕名稱
- 不需要輸出圖示名稱
- 只描述按鈕用途
- 每個按鈕對應一筆判斷結果
- 僅允許描述 metadata.actions 中實際存在的按鈕
- 不可臆測不存在按鈕
- 不可描述按鈕顏色
- 不可描述按鈕外觀
- 不可描述 SVG 內容
- 功能描述需符合當前頁面情境
- action_id 必須完整照抄 metadata.actions 提供的 action_id
- 只有按鈕文字、aria-label、title、鄰近可見文字或截圖能直接證明
  功能時，才可設定 include=true
- icon class 與頁面情境只能作為輔助，不能單獨作為功能證據
- 無法確定用途時必須設定 include=false、description=""
- confidence 為 0 到 1；include=true 時 confidence 必須至少為 0.8

Button Screenshot button-0
=
action_id button-0

Button Screenshot button-1
=
action_id button-1

Button Screenshot button-2
=
action_id button-2

重要：

button_descriptions 的筆數必須與收到的 Button Screenshot 數量完全一致，
但無法可靠辨識的項目必須使用 include=false，文件將不顯示該圖示。

如果收到 3 張按鈕截圖：

則必須輸出 3 筆資料。

不得增加額外按鈕。

不得省略任何按鈕的判斷結果。

無法由以下證據直接判斷時不得猜測：

- 畫面截圖
- 按鈕截圖
- HTML內容
- metadata.actions

請輸出 include=false 與空白 description。

錯誤：

[
    "建立新的資料",
    "移除資料"
]

錯誤：

[
    {
        "description": "建立新的資料"
    }
]

錯誤：

[
    {
        "action_id": "button-0",
        "description": "建立新的資料"
    },
    {
        "action_id": "button-1",
        "description": "移除資料"
    },
    {
        "action_id": "button-2",
        "description": "下載資料"
    },
    {
        "action_id": "button-3",
        "description": "不存在的按鈕"
    }
]

正確：

[
    {
        "action_id": "button-0",
        "description": "執行歷史記錄內容的搜尋與篩選"
    },
    {
        "action_id": "button-1",
        "description": "下載目前查詢結果的資料報表"
    },
    {
        "action_id": "button-2",
        "description": "開啟操作說明與使用幫助文件"
    }
]

==================================================
page_sections
==================================================

畫面組成。

格式：

[
    "區塊名稱：用途說明",
    "區塊名稱：用途說明"
]

範例：

[
    "搜尋區塊：提供條件輸入與資料篩選功能。",
    "結果列表：顯示符合條件的資料。"
]

==================================================
field_descriptions
==================================================

欄位說明。

欄位名稱只能使用「欄位資訊」提供的 section 與 label。

禁止輸出：

- internal_name
- HTML id 或 name
- snake_case 程式變數名稱
- 帶有 [] 的表單名稱

例如 internal_name 為 rcode_rate_status，section 為 RCode 速率，
label 為狀態時，只能輸出「RCode 速率－狀態」，不得輸出
「rcode_rate_status」。

格式：

[
    "欄位名稱：用途說明",
    "欄位名稱：用途說明"
]

範例：

[
    "Name：使用者名稱。",
    "Email：電子郵件地址。"
]

==================================================
best_practices
==================================================

最佳實務。

格式：

[
    "...",
    "...",
    "..."
]

要求：

- 0~3項
- 僅限畫面、功能描述或欄位資訊直接支持的操作建議
- 若沒有直接證據，輸出空陣列
- 不得自行加入稽核、合規、資安政策、效能或備援建議

==================================================
restrictions
==================================================

注意事項與限制。

格式：

[
    "...",
    "...",
    "..."
]

要求：

- 0~3項
- 僅限畫面、功能描述或欄位資訊明確揭示的限制
- 若沒有直接證據，輸出空陣列
- 不得推測授權需求、服務重啟、快取時間、資料延遲、偵測能力、
  日誌相依性或其他系統行為

==================================================
重要規則
==================================================

所有內容皆使用繁體中文。

禁止輸出：

{'Name':'裝置名稱'}

{"Name":"裝置名稱"}

"{'Name':'裝置名稱'}"

"Name：使用者名稱"

不要把 Dict 當成文字輸出。

不要把 JSON 當成文字輸出。

不要輸出：

{}
[]

所有內容必須放入對應 JSON 欄位。

button_descriptions 必須是物件陣列。

interaction_sections 必須是物件陣列。

page_sections 必須是字串陣列。

field_descriptions 必須是字串陣列。

best_practices 必須是字串陣列。

restrictions 必須是字串陣列。

最終輸出必須為合法 JSON。
"""


def image_to_base64(image_path):

    with open(
        image_path,
        "rb"
    ) as f:

        return (
            base64
            .b64encode(
                f.read()
            )
            .decode("utf-8")
        )


INTERNAL_FIELD_PATTERN = re.compile(r"^[a-z][A-Za-z0-9_]*(?:\[\])?$")
CAMEL_CASE_PATTERN = re.compile(r"^[a-z]+(?:[A-Z][A-Za-z0-9]*)+$")


def is_public_field_label(value):
    """Return True only for text that can safely appear as a UI label."""

    value = str(value or "").strip()
    if not value:
        return False
    if "[]" in value or "{" in value or "}" in value:
        return False
    if CAMEL_CASE_PATTERN.fullmatch(value):
        return False
    if re.fullmatch(r"[a-z][a-z0-9_]*(?:\[\])?", value) and "_" in value:
        return False
    # Hostnames, file templates and paths are normally placeholders or values,
    # not field labels. Acronyms such as DNSSEC, IPv4 and DoH are unaffected.
    if re.fullmatch(r"(?:[A-Za-z0-9-]+\.)+[A-Za-z0-9-]+", value):
        return False
    if "/" in value or "\\" in value:
        return False
    return True


def get_public_field_context(page):
    details = []
    for detail in page.get("field_details") or []:
        section = str(detail.get("section") or "").strip()
        label = str(detail.get("label") or "").strip()
        if not is_public_field_label(label):
            continue
        details.append({
            "section": section,
            "label": label,
            "display_name": f"{section}－{label}" if section else label,
            "options": detail.get("options") or []
        })

    if details:
        return json.dumps(details, ensure_ascii=False, indent=2)

    # Compatibility with metadata generated before field_details existed.
    fields = []
    for field in page.get("fields") or []:
        value = str(field).strip()
        if value and is_public_field_label(value) and not INTERNAL_FIELD_PATTERN.fullmatch(value):
            fields.append(value)
    return "\n".join(fields)


def _tab_comparison_summary(page):
    """Expose only public UI structure to the equivalence classifier."""

    return {
        "tab": page.get("tab"),
        "headings": page.get("headings", []),
        "fields": [
            {
                "section": detail.get("section", ""),
                "label": detail.get("label", ""),
                "options": detail.get("options", []),
            }
            for detail in page.get("field_details", [])
            if detail.get("label")
        ],
        "tables": page.get("tables", []),
        "actions": [
            {
                "label": action.get("label", ""),
                "icon": action.get("icon", ""),
            }
            for action in page.get("actions", [])
        ],
    }


def assess_tab_equivalence(pages):
    """Ask the model whether tabs are interchangeable instances of one UI."""

    if len(pages) < 2:
        return {
            "equivalent": False,
            "confidence": 1.0,
            "difference_note": "",
        }

    output_language = (
        "English"
        if str(pages[0].get("language", "")).lower().startswith("en")
        else "繁體中文"
    )
    summaries = [
        _tab_comparison_summary(page)
        for page in pages
    ]
    prompt = f"""
Compare the following tabs from the same product page.

Determine whether they have the same purpose, controls, fields, actions and
behavior, and differ only because they are independent configuration slots or
instances. Similar wording alone is not sufficient.

Return legal JSON only:
{{
  "equivalent": true,
  "confidence": 0.0,
  "difference_note": ""
}}

Rules:
- equivalent must be a JSON boolean.
- confidence must be between 0 and 1.
- Set equivalent to false if any tab has a different purpose, field, action,
  workflow, data scope or behavior.
- Set equivalent to true only when one shared manual explanation can accurately
  document every tab.
- difference_note must be one concise sentence in {output_language} explaining
  either the harmless instance difference or the material difference.
- Do not mention AI, HTML, metadata, screenshots or implementation details.

Page: {pages[0].get("page")}

Tabs:
{json.dumps(summaries, ensure_ascii=False, indent=2)}
"""
    content = [{"type": "text", "text": prompt}]

    # Keep the comparison request comfortably under the configured multimodal
    # limit while still showing both the top and lower portions of each tab.
    image_budget = 12
    for page_index, page in enumerate(pages):
        screenshot_paths = page.get("screenshots") or []
        if not screenshot_paths and page.get("screenshot"):
            screenshot_paths = [page.get("screenshot")]

        for screenshot_path in screenshot_paths[:2]:
            if image_budget <= 0:
                break
            if screenshot_path and os.path.exists(screenshot_path):
                content.append({
                    "type": "text",
                    "text": (
                        f"Tab {page_index + 1}: "
                        f"{page.get('tab')}"
                    ),
                })
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            "data:image/png;base64,"
                            f"{image_to_base64(screenshot_path)}"
                        )
                    },
                })
                image_budget -= 1

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify whether product UI tabs are semantically "
                    "equivalent. Return JSON only and be conservative."
                ),
            },
            {"role": "user", "content": content},
        ],
        temperature=0,
        max_tokens=512,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
                "preserve_thinking": False,
            }
        },
    )
    result_text = response.choices[0].message.content

    if not result_text:
        raise ValueError("vLLM 回傳空白的頁籤等價判斷")

    result = json.loads(
        result_text.replace("```json", "").replace("```", "").strip()
    )
    equivalent = result.get("equivalent")
    confidence = result.get("confidence")

    if not isinstance(equivalent, bool):
        raise ValueError("頁籤等價判斷缺少 equivalent boolean")

    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("頁籤等價判斷的 confidence 必須介於 0 與 1")

    return {
        "equivalent": equivalent,
        "confidence": float(confidence),
        "difference_note": str(result.get("difference_note") or "").strip(),
    }


def generate_manual_content(
    page,
    screenshot_paths=None
):
    output_language = (
        "English"
        if str(page.get("language", "")).lower().startswith("en")
        else "繁體中文"
    )
    system_prompt = SYSTEM_PROMPT.replace(
        "所有內容皆使用繁體中文。",
        f"所有內容皆使用{output_language}。"
    ).replace(
        "- 繁體中文",
        f"- {output_language}"
    )
    actions = []
    for original_index, action in enumerate(page.get("actions", [])):
        image_path = action.get("image")
        if not image_path or not os.path.exists(image_path):
            continue
        public_action = dict(action)
        public_action["action_id"] = str(
            action.get("action_id") or f"button-{original_index}"
        )
        actions.append(public_action)
    actions_json = json.dumps(
        actions,
        ensure_ascii=False,
        indent=2
    )
    public_interactions = []
    for flow in page.get("interaction_flows", []):
        public_interactions.append({
            "action_id": flow.get("action_id"),
            "title": flow.get("title"),
            "kind": flow.get("kind"),
            "context_heading": flow.get("context_heading"),
            "fields": [
                {
                    "label": field.get("label"),
                    "type": field.get("type"),
                    "required": field.get("required", False),
                    "placeholder": field.get("placeholder", ""),
                    "inputmode": field.get("inputmode", ""),
                    "min": field.get("min", ""),
                    "max": field.get("max", ""),
                    "step": field.get("step", ""),
                    "accept": field.get("accept", ""),
                    "options": field.get("options", []),
                }
                for field in flow.get("fields", [])
                if field.get("label")
            ],
        })
    public_field_context = get_public_field_context(page)

    prompt = f"""
頁面名稱
{page.get("page")}

頁籤名稱
{page.get("tab")}

等價頁籤
{json.dumps(page.get("equivalent_tabs", []), ensure_ascii=False)}

等價頁籤說明
{page.get("equivalence_note", "")}

如果「等價頁籤」包含多個名稱，代表這些頁籤是可獨立設定、但用途與
欄位相同的功能實例。請以合併後的頁籤名稱撰寫一份共同說明，並在
overview 清楚說明它們是多組獨立設定；不可只描述其中一個頁籤。

功能描述
{chr(10).join(page.get("descriptions", []))}

畫面區塊
{chr(10).join(page.get("headings", []))}

欄位資訊
{public_field_context}

欄位輸出規則
- 僅使用欄位資訊中的 display_name 作為欄位名稱。
- internal_name 僅供程式內部識別，不得出現在輸出中。
- 不得自行把 section、label 改回 HTML id、name 或 snake_case 名稱。

metadata.actions

{actions_json}

SENTRY 內建說明面板提供的按鈕證據

{json.dumps(page.get("help_actions", []), ensure_ascii=False, indent=2)}

按鈕開啟後的設定表單

{json.dumps(public_interactions, ensure_ascii=False, indent=2)}

說明：

metadata.actions 中的每一筆資料都對應後續提供的一張按鈕截圖。

例如：

metadata.actions[0].action_id
對應
同一個 action_id 標示的 Button Screenshot

metadata.actions[1].action_id
對應
同一個 action_id 標示的 Button Screenshot

metadata.actions[2].action_id
對應
同一個 action_id 標示的 Button Screenshot

請同時參考：

- 整頁截圖
- metadata.actions
- Button Screenshot 圖片
- HTML資訊
- 畫面上下文

來判斷按鈕用途。

按鈕用途必須符合目前頁面情境。

判斷按鈕時，證據優先順序為：
1. SENTRY 內建說明面板中圖示相符的說明。
2. 按鈕開啟後的設定表單標題與欄位。
3. 按鈕的 context_heading、context_text、label、title、aria。
4. 整頁與按鈕截圖。

不得只因圖示同為加號、勾號或問號，就套用其他按鈕的用途。

interaction_sections 請針對「按鈕開啟後的設定表單」輸出：
[
  {{
    "action_id": "button-2",
    "title": "新增網域設定",
    "overview": "設定新網域所需的參數。",
    "field_descriptions": ["Domain：輸入要管理的網域名稱。"]
  }}
]

規則：
- action_id 必須原樣使用 interaction_flows 的 action_id。
- 每一個 interaction flow 都必須輸出一筆 interaction_sections。
- field_descriptions 必須涵蓋該 interaction flow 提供的每一個欄位 label，
  每個 label 恰好一筆，不可省略、合併或增加欄位。
- 欄位名稱必須原樣使用該 interaction flow 實際提供的 label。
- 說明必須告訴管理員應輸入、選擇、上傳或切換什麼內容。
- 若有 options、placeholder、min、max、step、accept 或 required，應將
  可確認的格式、選項、範圍、檔案類型或必填要求寫入說明。
- 證據未提供格式或限制時，使用保守說法，不可自行發明範例值、預設值、
  長度限制、網路格式或操作效果。
- 不得輸出 internal_name。
- 沒有 interaction flow 時輸出空陣列。

輸出順序：
1. 先判斷所有 button_descriptions。
2. 再完成所有 interaction_sections 與欄位說明。
3. 最後根據以上結果撰寫 overview；overview 必須是 JSON 的最後一個欄位。

如果畫面有 3 顆按鈕，button_descriptions 必須輸出 3 筆判斷結果；
無法可靠識別者使用 include=false，禁止依頁面情境猜測。

表格欄位

{chr(10).join(
[
    str(column)
    for row in page.get("tables", [])
    for column in row
    if column
]
)}
"""

    content = [
        {
            "type": "text",
            "text": prompt
        }
    ]
    image_budget = 16

    if isinstance(screenshot_paths, str):
        screenshot_paths = [screenshot_paths]

    for screenshot_index, screenshot_path in enumerate((screenshot_paths or [])[:1]):
        if screenshot_path and os.path.exists(screenshot_path):
            content.append({
                "type": "text",
                "text": f"Page Screenshot {screenshot_index + 1}"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_to_base64(screenshot_path)}"
                }
            })
            image_budget -= 1
    for action in actions:
        if image_budget <= 0:
            break
        image_path = action.get("image")
        action_id = action["action_id"]
        content.append({
            "type": "text",
            "text": (
                f"Button Screenshot action_id={action_id}\n"
                f"label={action.get('label', '')}\n"
                f"title={action.get('title', '')}\n"
                f"aria={action.get('aria', '')}\n"
                "回傳資料時必須原樣使用這個 action_id。"
            )
        })
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_to_base64(image_path)}"
            }
        })
        image_budget -= 1
    for flow in page.get("interaction_flows", []):
        action_id = str(flow.get("action_id") or "")
        for screenshot_index, image_path in enumerate(flow.get("screenshots", [])):
            if image_budget <= 0:
                break
            if not image_path or not os.path.exists(image_path):
                continue
            content.append({
                "type": "text",
                "text": (
                    f"Interaction Screenshot action_id={action_id} "
                    f"segment={screenshot_index + 1}"
                )
            })
            image_budget -= 1
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_to_base64(image_path)}"
                }
            })
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": content
            }
        ],
        temperature=0,
        max_tokens=4096,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
                "preserve_thinking": False,
            }
        },
    )

    result_text = response.choices[0].message.content

    if not result_text:
        raise ValueError("vLLM 回傳空白內容")

    result_text = (
        result_text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:

        return json.loads(
            result_text
        )

    except Exception as e:

        print(
            "JSON Parse Failed"
        )

        print(e)

        print(result_text)

        return {

            "overview": "",

            "business_value": "",

            "page_sections": [],

            "field_descriptions": [],

            "button_descriptions": [],

            "interaction_sections": [],

            "best_practices": [],

            "restrictions": []
        }
