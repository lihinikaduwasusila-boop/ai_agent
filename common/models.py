from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SearchRequestInput(BaseModel):
    case_type: str = Field("unknown")
    topic: str = Field("unknown")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    num_results: Optional[int] = 5
    raw_query: Optional[str] = None


class SearchRequest(BaseModel):
    case_type: str = Field("unknown")
    topic: str = Field("unknown")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    raw_query: Optional[str] = None


class SearchResponse(BaseModel):
    case_ids: List[str] = Field(default_factory=list)
    hit_count: int = 0
    cases: List[Dict[str, Any]] = Field(default_factory=list)


class SummaryRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None


class SummaryResponse(BaseModel):
    summary: Dict[str, Any]


class CitationRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None


class CitationResponse(BaseModel):
    citations: List[str]


class QueryRequest(BaseModel):
    query: str


class PrecedentRequest(BaseModel):
    case_id: str
    citations: List[str]


class PrecedentResponse(BaseModel):
    related_cases: List[Dict[str, Any]] = Field(default_factory=list)


class Case(BaseModel):
    case_id: str
    case_name: str
    court: str
    decision: str
    summary: Dict[str, Any]
    citations: List[str]
    related_precedents: List[Dict[str, Any]] = Field(default_factory=list)


class QueryResponse(BaseModel):
    cases: List[Case]


class HistoryItem(BaseModel):
    id: int
    query: str
    results: Dict[str, Any]
    timestamp: Optional[str] = None


class HistoryResponse(BaseModel):
    items: List[HistoryItem]