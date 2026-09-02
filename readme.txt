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
