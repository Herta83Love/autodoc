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
你是一位資深 DNS 與網路安全產品技術文件工程師。

你會同時取得：

1. UI截圖
2. 頁面資訊
3. 原廠說明
4. 欄位資訊
5. 按鈕資訊

你的任務：

理解畫面真正用途，
不要只是翻譯原廠說明。

請優先觀察：

- 使用情境
- 設定目的
- 主要功能
- 畫面中的圖表
- 統計資料
- 表格資訊
- 視覺呈現的重點

若畫面中出現：

- Dashboard
- Graph
- Chart
- Table
- Statistics

請將其納入摘要說明。

輸出 JSON：

{
  "summary": "",
  "features": [],
  "field_descriptions": [],
  "steps": [],
  "notes": []
}

規則：

summary:
3~5句摘要。

features:
主要功能。

field_descriptions:
根據欄位名稱推測用途。

steps:
依畫面操作流程說明。

notes:
限制條件與注意事項。

所有內容必須使用繁體中文。
"""


def image_to_base64(
    image_path
):
    with open(
        image_path,
        "rb"
    ) as f:
        return base64.b64encode(
            f.read()
        ).decode("utf-8")


def generate_manual_content(
    page,
    screenshot_path=None
):

    prompt = f"""
頁面名稱:
{page.get("page")}

頁籤:
{page.get("tab")}

原廠功能說明:
{chr(10).join(page.get("descriptions", []))}

功能區塊:
{chr(10).join(page.get("headings", []))}

設定項目:
{chr(10).join(page.get("fields", []))}

操作按鈕:
{chr(10).join(page.get("buttons", []))}
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

        image_b64 = image_to_base64(
            screenshot_path
        )

        content.append(
            {
                "type": "input_image",
                "image_url":
                    f"data:image/png;base64,{image_b64}"
            }
        )

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
    )

    return json.loads(
        result_text
    )