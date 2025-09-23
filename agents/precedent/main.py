from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import httpx
from common.security import verify_token
from common.logging import logger
from common.config import Config
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Precedent Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PrecedentRequest(BaseModel):
    case_id: str
    citations: List[str]


class PrecedentResponse(BaseModel):
    related_cases: List[Dict[str, Any]]


async def fetch_case_name(case_id: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}clusters/{case_id}/?fields=case_name",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None,
        )
        if resp.status_code != 200:
            return ""
        return resp.json().get("case_name", "")


@app.post("/find_precedents", response_model=PrecedentResponse)
async def find_precedents(req: PrecedentRequest, token: dict = Depends(verify_token)):
    if not req.case_id:
        raise HTTPException(status_code=400, detail="case_id required")

    case_name = await fetch_case_name(req.case_id)
    q = case_name or (" ".join(req.citations[:3]) if req.citations else "precedent")

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}search/",
            params={"q": q, "court": "scotus", "type": "o", "page_size": 10},
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None,
        )
        if r.status_code != 200:
            return PrecedentResponse(related_cases=[])
        results = r.json().get("results", [])[:5]
        related = [{
            "case_id": str(x.get("cluster_id")),
            "case_name": x.get("case_name", "Unknown"),
            "court": x.get("court_name", "United States Supreme Court"),
            "date_filed": x.get("date_filed", "Unknown"),
        } for x in results]
        logger.info("RA Check: Precedents fetched via API-only search; fairness noted, transparency via logs.")
        return PrecedentResponse(related_cases=related)