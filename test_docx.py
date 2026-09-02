# ============================================================================
# File: test_docx.py
# ============================================================================

import json

from utils.file_helper import (
    ensure_directories
)

from document.markdown_generator import (
    generate_manual
)

from document.manual_generator import (
    generate_docx
)


def run():

    ensure_directories()

    with open(
        "output/metadata.json",
        "r",
        encoding="utf-8"
    ) as f:

        metadata = json.load(f)

    print(
        f"\n載入 Metadata 成功，共 {len(metadata)} 筆"
    )

    generate_manual(
        metadata
    )

    generate_docx()

    print(
        "\n✅ manual.md 已產生"
    )

    print(
        "✅ SENTRY_Manual.docx 已產生"
    )


if __name__ == "__main__":

    run()