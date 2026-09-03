# AutoDoc

AI-powered documentation generator for SENTRY.

## Features

- Menu Discovery
- Page Crawling
- Screenshot Capture
- HTML Export
- Metadata Extraction
- Azure OpenAI Vision Analysis
- Automated DOCX Manual Generation

## Architecture

Menu
↓
Crawler
↓
Screenshot
↓
Metadata
↓
GPT-4.1-mini Vision
↓
Structured JSON
↓
Word Manual

## Installation

```bash
python -m pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copy `.env.example` to `.env`, then configure the Azure OpenAI values and
SENTRY login credentials. Adjust the login URL and selectors in
`config/config.yaml` when the target environment differs.

The `login.language.runs` list controls the crawl order. The default setup
creates a fresh login session for English first and Traditional Chinese
second. Each run writes isolated screenshots, HTML, icons, metadata, Markdown,
and DOCX output beneath `output/`.

Chinese metadata is paired with the English crawl by stable menu/tab position.
The Chinese manual therefore renders navigation terms as
`中文（Official English UI term）` in both headings and the table of contents.
If the login-page markup differs, set `login.language.selector` to the language
dropdown CSS selector and adjust the run-specific labels or values.

## Run

```bash
python main.py
```

## Word Manual Styling

The DOCX generator uses the URMAZI/SENTRY visual system defined in
`document/manual_generator.py` and the reusable assets under
`document/assets/`. Cover, publication notice, introduction, table of
contents, running header/footer, and back-cover text can be adjusted in
`config/document.yaml`.

The table of contents is generated as visible internal links, so it remains
available without manually refreshing Word fields.

The final DOCX formatting pass explicitly applies a white page/table
background and black text to body content, styles, hyperlinks, fields,
headers, footers, and cover/back-cover text.

Screen action icons are rendered in a two-column icon/function table. The
workflow section is intentionally omitted from both AI output and DOCX output.
