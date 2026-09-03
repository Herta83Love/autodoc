# AutoDoc

AutoDoc 是用於產生 SENTRY 操作手冊的自動化工具。程式會登入 SENTRY、探索功能選單、擷取頁面資料與畫面，再透過 Azure OpenAI 產生說明內容，最後輸出 Word 文件。

## 主要功能

- 自動登入 SENTRY 並選擇介面語言
- 探索功能選單、頁面與頁籤
- 擷取頁面截圖及畫面操作圖示
- 匯出 HTML 與結構化 Metadata
- 使用 Azure OpenAI 分析頁面內容
- 快取 AI 產生結果，避免重複呼叫
- 自動產生 DOCX 操作手冊
- 使用既有爬蟲與 AI 紀錄快速重建文件

## 處理流程

```text
SENTRY 選單與頁面
        ↓
爬蟲與畫面擷取
        ↓
Metadata、HTML、截圖
        ↓
Azure OpenAI 分析與 AI Cache
        ↓
Word 操作手冊
```

## 安裝

建議先建立並啟用 Python 虛擬環境，再安裝相依套件：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
playwright install chromium
```

## 設定

將 `.env.example` 複製為 `.env`，填入 SENTRY 登入資料及 Azure OpenAI 連線資訊。

SENTRY 登入網址、帳號欄位、密碼欄位、登入按鈕及語言選單設定位於：

```text
config/config.yaml
```

`login.language` 用於在登入前選擇 SENTRY 介面語言。若登入頁面的元件或語言值不同，可調整其中的 `selector`、`labels`、`values` 及逾時設定。

封面、出版聲明、前言、版本與封底文字位於：

```text
config/document.yaml
```

## 完整執行：重新爬取並產生文件

需要重新擷取 SENTRY 畫面與資料時執行：

```bash
python3 main.py
```

完整流程會啟動瀏覽器、登入 SENTRY、執行爬蟲、更新 `output` 內的資料，並產生：

```text
output/SENTRY_Manual.docx
```

## 快速執行：跳過爬蟲重新產生文件

若 `output` 目錄已保留先前的爬蟲紀錄與 AI 紀錄，可以直接執行：

```bash
python3 test_docx.py
```

此模式不會開啟瀏覽器、不會登入 SENTRY，也不會重新執行爬蟲；它會直接使用下列既有資料重新產生 Word 文件：

- `output/metadata.json`：頁面、欄位、按鈕及圖片路徑等爬蟲結果
- `output/screenshots/`：頁面截圖
- `output/icons/`：畫面操作圖示
- `output/ai_cache/`：已產生的 AI 說明紀錄

適合在調整 `document/manual_generator.py`、文件樣式、封面、前言、目錄、標頭或封底時使用，可省去重新登入和爬取所有頁面的時間。

執行前請確認：

1. `output/metadata.json` 存在且包含資料。
2. Metadata 記錄的截圖與操作圖示仍位於原本路徑。
3. `output/ai_cache/` 保留先前的 AI 紀錄；若對應 Cache 不存在，文件產生器可能會再次呼叫 Azure OpenAI。
4. 已啟用安裝完成的 Python 虛擬環境。

產生完成後，文件位於：

```text
output/SENTRY_Manual.docx
```

`test_docx.py` 會先檢查 Metadata 格式及圖片是否缺漏；缺少圖片時會在終端機顯示警告。

## Output 目錄

```text
output/
├── metadata.json
├── screenshots/
├── icons/
├── html/
├── ai_cache/
├── manual.md
└── SENTRY_Manual.docx
```

請勿在調整文件版面期間刪除 `metadata.json`、`screenshots/`、`icons/` 或 `ai_cache/`，否則無法完整沿用既有資料快速重建文件。

## 文件樣式

DOCX 版面主要由 `document/manual_generator.py` 控制，相關圖片資源位於 `document/assets/`。

目前文件包含封面、文件資訊、出版聲明、修訂紀錄、目錄、前言、功能內容、標頭／頁尾與封底，並在輸出前統一套用白色背景與黑色文字。

目錄使用可點擊的內部連結產生，不需手動更新 Word 欄位即可顯示。
