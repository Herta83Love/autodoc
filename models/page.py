from typing import Optional

from pydantic import BaseModel


class PageMetadata(BaseModel):

    category: str

    page: str

    tab: Optional[str] = None

    title: str

    url: str

    screenshot: str

    html: str

    fields: list[str]

    buttons: list[str]

    tables: list[list[str]]

    headings: list[str] = []

    descriptions: list[str] = []