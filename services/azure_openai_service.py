# File: azure_openai_service.py
import base64
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv(
        "AZURE_OPENAI_API_KEY"
    ),
    base_url=os.getenv(
        "AZURE_OPENAI_ENDPOINT"
    )
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
    "overview": "",
    "business_value": "",
    "button_descriptions": [],
    "page_sections": [],
    "field_descriptions": [],
    "workflow": [],
    "best_practices": [],
    "restrictions": []
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

- 3~5句
- 說明功能用途
- 說明功能目的
- 不可描述畫面配置

==================================================
business_value
==================================================

使用價值。

要求：

- 3~5句
- 說明對管理員的價值
- 說明管理效益
- 說明營運價值

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
        "button_index": 0,
        "description": "建立新的規則"
    },
    {
        "button_index": 1,
        "description": "移除指定規則"
    },
    {
        "button_index": 2,
        "description": "重新載入最新資料"
    }
]

規則：

- 不需要輸出按鈕名稱
- 不需要輸出圖示名稱
- 只描述按鈕用途
- 每個按鈕對應一筆說明
- 僅允許描述 metadata.actions 中實際存在的按鈕
- 不可臆測不存在按鈕
- 不可描述按鈕顏色
- 不可描述按鈕外觀
- 不可描述 SVG 內容
- 功能描述需符合當前頁面情境

Button Screenshot 1
=
button_index 0

Button Screenshot 2
=
button_index 1

Button Screenshot 3
=
button_index 2

重要：

button_descriptions 的筆數必須與收到的 Button Screenshot 數量完全一致。

如果收到 3 張按鈕截圖：

則必須輸出 3 筆資料。

不得增加額外按鈕。

不得省略任何按鈕。

即使無法由按鈕文字判斷功能，
也必須參考：

- 畫面截圖
- 按鈕截圖
- HTML內容
- metadata.actions

產生對應說明。

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
        "button_index": 0,
        "description": "建立新的資料"
    },
    {
        "button_index": 1,
        "description": "移除資料"
    },
    {
        "button_index": 2,
        "description": "下載資料"
    },
    {
        "button_index": 3,
        "description": "不存在的按鈕"
    }
]

正確：

[
    {
        "button_index": 0,
        "description": "執行歷史記錄內容的搜尋與篩選"
    },
    {
        "button_index": 1,
        "description": "下載目前查詢結果的資料報表"
    },
    {
        "button_index": 2,
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
workflow
==================================================

操作流程。

格式：

[
    "...",
    "...",
    "..."
]

要求：

- 5~10個步驟
- 每個步驟一行
- 使用自然語言
- 使用管理員角度

重要規則：

不要描述按鈕。

錯誤：

"點擊新增按鈕"

"點擊刪除按鈕"

"點擊搜尋按鈕"

"點擊重新整理按鈕"

正確：

"建立新的資料項目"

"移除指定資料"

"執行資料查詢"

"重新載入系統資料"

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

- 3~5項

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

- 3~5項

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

page_sections 必須是字串陣列。

field_descriptions 必須是字串陣列。

workflow 必須是字串陣列。

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


def generate_manual_content(
    page,
    screenshot_path=None
):
    actions = [

        action

        for action in page.get(
            "actions",
            []
        )

        if action.get(
            "image"
        )
    ]
    actions_json = json.dumps(
        actions,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
頁面名稱
{page.get("page")}

頁籤名稱
{page.get("tab")}

功能描述
{chr(10).join(page.get("descriptions", []))}

畫面區塊
{chr(10).join(page.get("headings", []))}

欄位資訊
{chr(10).join(page.get("fields", []))}

metadata.actions

{actions_json}

說明：

metadata.actions 中的每一筆資料都對應後續提供的一張按鈕截圖。

例如：

metadata.actions[0]
對應
Button Screenshot 1

metadata.actions[1]
對應
Button Screenshot 2

metadata.actions[2]
對應
Button Screenshot 3

請同時參考：

- 整頁截圖
- metadata.actions
- Button Screenshot 圖片
- HTML資訊
- 畫面上下文

來判斷按鈕用途。

按鈕用途必須符合目前頁面情境。

如果畫面有 3 顆按鈕：

button_descriptions 必須輸出 3 筆資料。

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
            "type": "input_text",
            "text": prompt
        }
    ]

    if (
        screenshot_path
        and os.path.exists(
            screenshot_path
        )
    ):

        content.append({
            "type": "input_image",
            "image_url":
            f"data:image/png;base64,{image_to_base64(screenshot_path)}"
        })
    for idx, action in enumerate(actions):

        image_path = action.get(
            "image"
        )

        if (
            image_path
            and os.path.exists(
                image_path
            )
        ):

            content.append({
                "type": "input_text",
                "text":
                f"""
Button Screenshot {idx + 1}

metadata.actions[{idx}]

label:
{action.get("label", "")}

icon:
{action.get("icon", "")}

請記住：
此張圖片對應 metadata.actions[{idx}]
"""
            })

            content.append({
                "type": "input_image",
                "image_url":
                f"data:image/png;base64,{image_to_base64(image_path)}"
            })

    response = client.responses.create(
        model=os.getenv(
            "AZURE_OPENAI_DEPLOYMENT"
        ),
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": content
            }
        ]
    )

    result_text = (
        response.output[0]
        .content[0]
        .text
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

            "workflow": [],

            "best_practices": [],

            "restrictions": []
        }