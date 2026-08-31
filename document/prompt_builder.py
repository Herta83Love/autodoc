def build_prompt(page):

    return f"""
你是一位資深技術文件工程師。

請根據以下資訊撰寫使用手冊。

頁面名稱:
{page.get('title')}

功能說明:
{chr(10).join(page.get('descriptions', []))}

功能區塊:
{chr(10).join(page.get('headings', []))}

欄位:
{chr(10).join(page.get('fields', []))}

按鈕:
{chr(10).join(page.get('buttons', []))}

資料表:
{chr(10).join(
    [
        item
        for row in page.get("tables", [])
        for item in row
    ]
)}

請輸出：

1. 功能說明
2. 主要功能
3. 操作步驟
4. 注意事項

請使用繁體中文。
"""