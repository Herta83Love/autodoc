# ============================================================================
# File: page.py
# ============================================================================

from typing import Optional

from pydantic import BaseModel, Field


class PageMetadata(BaseModel):

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
