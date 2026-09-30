from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PageMetadata


class KnowledgeDocumentRead(BaseModel):
    id: int
    title: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    chunk_count: int = Field(ge=1)


class KnowledgeDocumentPage(BaseModel):
    items: list[KnowledgeDocumentRead]
    pagination: PageMetadata


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResultRead(BaseModel):
    content: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = Field(ge=0.0, le=1.0)


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeSearchResultRead]
    count: int = Field(ge=0)
