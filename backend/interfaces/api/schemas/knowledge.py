from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    evidence_id: str
    force: bool = False


class IngestResponse(BaseModel):
    evidence_id: str
    chunks_created: int
    model: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    chunk_id: str
    evidence_id: str
    evidence_title: str
    evidence_source: str
    text: str
    similarity: float
    chunk_index: int


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    model: str
