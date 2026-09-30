from pydantic import BaseModel, Field


class PageMetadata(BaseModel):
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
