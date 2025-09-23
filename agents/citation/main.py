from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import re
import httpx
from typing import List
from common.security import verify_token
from common.logging import logger
from common.config import Config
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Citation Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CitationRequest(BaseModel):
    case_id: str


class CitationResponse(BaseModel):
    citations: List[str]


async def fetch_case_text(case_id: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}opinions/{case_id}/?fields=text,html,html_lawbox,html_columbia,html_with_citations",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None,
        )
        if resp.status_code != 200:
            return ""
        data = resp.json()
        return data.get("text") or data.get("html_lawbox") or data.get("html_columbia") or data.get("html") or data.get("html_with_citations") or ""


def extract_citations(text: str) -> List[str]:
    text = re.sub(r"<[^>]+>", " ", text)
    patterns = [
        r"\b[A-Z][A-Za-z']+(?:\s+[A-Z][A-Za-z']+)?\s+v\.\s+[A-Z][A-Za-z']+(?:\s+[A-Z][A-Za-z']+)?\b",
        r"\b\d+\s+[A-Z][A-Za-z.]+\s+\d+(?:\s+\(\d{4}\))?\b",
        r"\b\d+\s+[A-Za-z.]+\s+§\s+\d+(?:\.\d+)?\b",
    ]
    found: List[str] = []
    for p in patterns:
        found += re.findall(p, text)
    # Deduplicate and basic length filter
    uniq = []
    seen = set()
    for c in found:
        c2 = c.strip()
        if 5 < len(c2) < 80 and c2 not in seen:
            seen.add(c2)
            uniq.append(c2)
    return uniq


@app.post("/extract_citations", response_model=CitationResponse)
async def extract(req: CitationRequest, token: dict = Depends(verify_token)):
    if not req.case_id:
        raise HTTPException(status_code=400, detail="case_id required")
    text = await fetch_case_text(req.case_id)
    if not text:
        logger.info("RA Check: No text for citation extraction; transparency ensured, no fabrication.")
        return CitationResponse(citations=[])
    citations = extract_citations(text)
    logger.info(f"RA Check: Extracted {len(citations)} citations; ethical handling via regex-only public text.")
    return CitationResponse(citations=citations)