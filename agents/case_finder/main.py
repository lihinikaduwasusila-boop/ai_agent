from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Optional
import re
import httpx
from common.security import verify_token
from common.logging import logger
from common.models import SearchRequest, SearchResponse, SearchRequestInput
from common.config import Config
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Query Understanding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


CASE_TYPE_CANDIDATES: List[str] = [
    "criminal", "civil", "tax", "intellectual property", "contract", "labor", "family", "property", "bankruptcy"
]
TOPIC_CANDIDATES: List[str] = [
    "cyber fraud", "data privacy", "theft", "contract dispute", "intellectual property", "bribery", "tax evasion", "employment discrimination", "breach of contract", "consumer protection",
]


@app.on_event("startup")
async def load_labels():
    async with httpx.AsyncClient(timeout=6) as client:
        try:
            if Config.CASE_TYPE_LABELS_URL:
                r = await client.get(Config.CASE_TYPE_LABELS_URL)
                r.raise_for_status()
                values = [str(x).strip().lower() for x in r.json() if str(x).strip()]
                if values:
                    global CASE_TYPE_CANDIDATES
                    CASE_TYPE_CANDIDATES = values
        except Exception as e:
            logger.warning(f"CASE_TYPE_LABELS_URL failed: {e}. Using defaults.")
        try:
            if Config.TOPIC_LABELS_URL:
                r = await client.get(Config.TOPIC_LABELS_URL)
                r.raise_for_status()
                values = [str(x).strip().lower() for x in r.json() if str(x).strip()]
                if values:
                    global TOPIC_CANDIDATES
                    TOPIC_CANDIDATES = values
        except Exception as e:
            logger.warning(f"TOPIC_LABELS_URL failed: {e}. Using defaults.")


def parse_dates_smart(query: str) -> tuple[Optional[str], Optional[str]]:
    date_from = None
    date_to = None
    match = re.search(r"from\s+(\d{4})\s+to\s+(\d{4})", query.lower())
    if match:
        date_from = f"{match.group(1)}-01-01"
        date_to = f"{match.group(2)}-12-31"
    return date_from, date_to


@app.post("/parse_query", response_model=SearchRequest)
async def parse_query(request: QueryRequest, token: dict = Depends(verify_token)):
    q = request.query.strip()
    q_lower = q.lower()
    case_type = next((c for c in CASE_TYPE_CANDIDATES if c in q_lower), "unknown")
    topic = next((t for t in TOPIC_CANDIDATES if t in q_lower), "unknown")
    date_from, date_to = parse_dates_smart(q)

    logger.info(
        f"RA Check: Parsed query with transparency: case_type={case_type}, topic={topic}, date_from={date_from}, date_to={date_to}"
    )
    return SearchRequest(case_type=case_type, topic=topic, date_from=date_from, date_to=date_to, raw_query=q)


@app.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequestInput, token: dict = Depends(verify_token)):
    params = {
        "q": request.raw_query or f"{request.case_type} {request.topic}",
        "court": "scotus",
        "type": "o",
        "page_size": 25,
    }
    if request.date_from:
        params["date_filed_min"] = request.date_from
    if request.date_to:
        params["date_filed_max"] = request.date_to

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"{Config.COURTLISTENER_BASE_URL}search/", params=params, headers={
                "Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])[: (request.num_results or 5)]
        except Exception as e:
            logger.warning(f"RA Check: CourtListener error: {e}; returning empty results for transparency.")
            results = []
        return SearchResponse(case_ids=[str(x.get("cluster_id")) for x in results], hit_count=len(results), cases=results)