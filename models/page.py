# ============================================================================
# File: page.py
# ============================================================================

from typing import Optional

from pydantic import BaseModel, Field


class PageMetadata(BaseModel):

    language: str = "zh-TW"

    page_key: str = ""

    menu_index: int = 0

    tab_index: Optional[int] = None

    english_category: Optional[str] = None

    english_page: Optional[str] = None

    english_tab: Optional[str] = None

    category: str

    page: str

    tab: Optional[str] = None

    title: str

    url: str

    screenshot: str

    html: str
    
    actions: list = Field(default_factory=list)

    fields: list[str]

    buttons: list[str]

    tables: list[list[str]]

    headings: list[str] = Field(default_factory=list)

    descriptions: list[str] = Field(default_factory=list)
