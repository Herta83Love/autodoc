# AutoDoc

AutoDoc 是用於產生 SENTRY 操作手冊的自動化工具。程式會登入 SENTRY、探索功能選單、擷取頁面資料與畫面，再透過 vLLM 的 OpenAI 相容 API 產生說明內容，最後輸出 Word 文件。

## 主要功能

- 自動登入 SENTRY 並選擇介面語言
- 探索功能選單、頁面與頁籤
- 擷取頁面截圖及畫面操作圖示
- 讀取圖表說明與可展開資料列的明細欄位
- 匯出 HTML 與結構化 Metadata
- 使用 vLLM 多模態模型分析頁面內容
- 快取 AI 產生結果，避免重複呼叫
- 自動產生 DOCX 操作手冊
- 使用既有爬蟲與 AI 紀錄快速重建文件

## 處理流程

 
SENTRY 選單與頁面
        ↓
爬蟲與畫面擷取
        ↓
Metadata、HTML、截圖
        ↓
vLLM 分析與 AI Cache
        ↓
可人工修改的頁面內容 YAML
        ↓
Word 操作手冊
   

## 安裝

建議先建立並啟用 Python 虛擬環境，再安裝相依套件：

bash:

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
playwright install chromium

### 安裝 LibreOffice 與 Poppler（目錄頁碼必要）

文件產生器不需要 Microsoft Word。它會使用免費的 LibreOffice 在背景完成文件分頁，再透過 Poppler 取得每個標題所在頁面，最後把實際頁碼寫回 DOCX。

macOS 使用 Homebrew 安裝：

bash:

brew install --cask libreoffice
brew install poppler

安裝後可確認指令是否可用：

bash:

/Applications/LibreOffice.app/Contents/MacOS/soffice --version
pdfinfo -v
pdftotext -v

Windows 使用 PowerShell 與 WinGet 安裝：

bash:

winget install --id TheDocumentFoundation.LibreOffice --exact
winget install --id oschwartz10612.Poppler --exact

LibreOffice 的 `soffice.exe` 通常位於：

 
C:\Program Files\LibreOffice\program\soffice.exe
   

安裝完成後請重新開啟 PowerShell，再確認下列指令是否可用：

bash:

soffice --version
pdfinfo -v
pdftotext -v

若 PowerShell 找不到 `soffice`，請將 `C:\Program Files\LibreOffice\program` 加入系統的 `PATH`。若找不到 `pdfinfo` 或 `pdftotext`，請將 WinGet 安裝的 Poppler `Library\bin` 目錄加入 `PATH`，再重新開啟終端機。

也可以從 LibreOffice 官方網站下載 Windows 安裝程式：

https://www.libreoffice.org/download/

Linux 可依使用的發行版安裝：

Ubuntu／Debian：

bash:

sudo apt update
sudo apt install libreoffice poppler-utils

Fedora／RHEL 系列：

bash:

sudo dnf install libreoffice poppler-utils

Arch Linux／Manjaro：

bash:

sudo pacman -S libreoffice-fresh poppler

Linux 安裝完成後可確認指令是否可用：

bash:

soffice --version
pdfinfo -v
pdftotext -v

各平台都不需要手動開啟 LibreOffice；macOS 也不需要設定自動化權限。執行 `python3 main.py` 或 `python3 test_docx.py` 時，程式會在背景建立暫存 PDF、計算目錄頁碼並寫回最終 DOCX；暫存檔完成後會自動移除。

## 設定

將 `.env.example` 複製為 `.env`，填入 SENTRY 登入資料及 vLLM 連線資訊。

vLLM 使用下列環境變數：

- `VLLM_API_ENDPOINT`：OpenAI 相容 API 位址，必須包含 `/v1`，例如 `http://127.0.0.1:8000/v1`
- `VLLM_API_KEY`：vLLM 啟用 API Key 驗證時填入實際金鑰；未啟用時可使用 `EMPTY`
- `VLLM_MODEL`：vLLM 啟動時提供的模型名稱，必須與伺服器實際載入的模型一致

可執行下列程式測試 vLLM 連線及內容產生：

bash:

python3 test_vllm.py

SENTRY 登入網址、帳號欄位、密碼欄位、登入按鈕及語言選單設定位於：

 
config/config.yaml
   

`login.language` 用於在登入前選擇 SENTRY 介面語言。若登入頁面的元件或語言值不同，可調整其中的 `selector`、`labels`、`values` 及逾時設定。

封面、出版聲明、前言、版本與封底文字位於：

 
config/document.yaml
   

### 人工修改每個頁面的文件內容

中英文每一頁的完整文件內容分別位於：


config/manual_content/en.yaml
config/manual_content/zh-TW.yaml


每個頁面以穩定的 `menu:.../tab:...` 識別碼保存，旁邊也會列出分類、頁面與頁籤名稱，方便搜尋。可直接修改各頁 `content` 內的功能概述、使用價值、按鈕說明、互動區塊、頁面區塊、欄位說明、最佳實務與限制事項。產生文件時，這些 YAML 內容會在最後套用，因此不需要編輯雜湊命名的 AI Cache。

重新爬取或增加頁面後，執行：

bash:

python3 scripts/sync_manual_content.py

此指令只會加入缺少的頁面，預設不覆蓋既有人工修改。只有確定要把所有內容重設成目前 AI／Cache 初稿時，才使用 `--overwrite`。

個別頁面的人工注意事項仍維護在 `config/page_notes.yaml`；沒有設定的頁面不會顯示注意事項區塊。

### 圖表與資料列明細

爬蟲會讀取頁面上圖表、指標卡的標題與官方說明，並寫入 Metadata 的 `visual_sections`。對於會在點選資料列後顯示明細面板的頁面，爬蟲只會開啟一筆具代表性的記錄，擷取其明細欄位與截圖，再關閉面板；結果寫入 `detail_sections`。這個流程只執行讀取與展開，不會儲存、套用或刪除資料。

新爬取的圖表與明細欄位會自動加入文件內容，同時保留 `config/manual_content/*.yaml` 中已有的人工修改。完整爬取後再執行 `python3 scripts/sync_manual_content.py`，即可將新發現的說明項目寫入 YAML，供後續直接編輯。

## 完整執行：重新爬取並產生文件

需要重新擷取 SENTRY 畫面與資料時執行：

bash:

python3 main.py
   

完整流程會啟動瀏覽器、登入 SENTRY、執行爬蟲、更新 `output` 內的資料，並產生：

 
output/SENTRY_Manual.docx
   

## 快速執行：跳過爬蟲重新產生文件

若 `output` 目錄已保留先前的爬蟲紀錄與 AI 紀錄，可以直接執行：

bash:

python3 test_docx.py
   

此模式不會開啟瀏覽器、不會登入 SENTRY，也不會重新執行爬蟲；它會直接使用下列既有資料重新產生 Word 文件：

- `output/metadata.json`：頁面、欄位、按鈕及圖片路徑等爬蟲結果
- `output/screenshots/`：頁面截圖
- `output/icons/`：畫面操作圖示
- `output/ai_cache/`：已產生的 AI 說明紀錄

適合在調整 `document/manual_generator.py`、文件樣式、封面、前言、目錄、標頭或封底時使用，可省去重新登入和爬取所有頁面的時間。

執行前請確認：

1. `output/metadata.json` 存在且包含資料。
2. Metadata 記錄的截圖與操作圖示仍位於原本路徑。
3. `output/ai_cache/` 保留先前的 AI 紀錄；若對應 Cache 不存在，文件產生器可能會再次呼叫 vLLM。
4. 已啟用安裝完成的 Python 虛擬環境。

產生完成後，文件位於：

 
output/SENTRY_Manual.docx
   

`test_docx.py` 會先檢查 Metadata 格式及圖片是否缺漏；缺少圖片時會在終端機顯示警告。

## Output 目錄

 
output/
├── metadata.json
├── screenshots/
├── icons/
├── html/
├── ai_cache/
├── manual.md
└── SENTRY_Manual.docx
   

請勿在調整文件版面期間刪除 `metadata.json`、`screenshots/`、`icons/` 或 `ai_cache/`，否則無法完整沿用既有資料快速重建文件。

## 文件樣式

DOCX 版面主要由 `document/manual_generator.py` 控制，相關圖片資源位於 `document/assets/`。

目前文件包含封面、文件資訊、出版聲明、修訂紀錄、目錄、前言、功能內容、標頭／頁尾與封底，並在輸出前統一套用白色背景與黑色文字。

目錄使用可點擊的內部連結與頁碼欄位產生。產生器會使用 LibreOffice 與 Poppler 自動計算並寫入實際頁碼，不需要安裝 Microsoft Word，也不需要手動更新欄位。
