from datetime import datetime
from pydantic import BaseModel


class Technology(BaseModel):
    id: str
    title: str
    summary: str
    sector: str
    language: str
    keywords: list[str]
    country: str
    source_id: str
    source_name: str
    url: str
    fetched_at: datetime
    # Optional source-specific detail fields
    org_name: str = ""
    transfer_type: str = ""
    dev_status: str = ""
    reg_date: str = ""
    sub_sector: str = ""


class Source(BaseModel):
    id: str
    name: str
    country: str
    institution: str
    status: str
    url: str
    ttl_seconds: int
    transfer_type: str = ""
