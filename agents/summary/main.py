from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer
import httpx
import re
import asyncio
from typing import Dict, Optional
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.sources import enrich_case_text
import spacy
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Summary Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SummaryRequest(BaseModel):
    case_id: str
    case_data: Dict | None = None
    case_text: Optional[str] = None


class SummaryResponse(BaseModel):
    summary: Dict


try:
    model_name = "sshleifer/distilbart-cnn-6-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline("summarization", model=model_name, tokenizer=tokenizer, device=-1)
except Exception as e:
    summarizer = None
    logger.warning("RA Check: Summarizer not available; will fallback to heuristic summary.")

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None


def clean_text(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


async def fetch_case_text(case_id: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}opinions/?cluster={case_id}&fields=plain_text,html,html_lawbox,html_columbia,html_with_citations",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None,
        )
        if resp.status_code != 200:
            return ""
        results = resp.json().get("results", [])
        data = results[0] if results else {}
        text = (
            data.get("plain_text") or data.get("html_lawbox") or data.get("html_columbia") or data.get("html") or data.get("html_with_citations") or ""
        )
        return clean_text(text)


def extract_entities(text: str) -> Dict:
    if not nlp or not text:
        return {"persons": [], "organizations": [], "locations": []}
    doc = nlp(text[:5000])
    out = {"persons": [], "organizations": [], "locations": []}
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            out["persons"].append(ent.text)
        elif ent.label_ == "ORG":
            out["organizations"].append(ent.text)
        elif ent.label_ == "GPE":
            out["locations"].append(ent.text)
    return out


@app.post("/summarize", response_model=SummaryResponse)
async def summarize(req: SummaryRequest, token: dict = Depends(verify_token)):
    if not req.case_id:
        raise HTTPException(status_code=400, detail="case_id required")

    # Prefer provided text; otherwise enrich via multi-source
    enriched = await enrich_case_text(req.case_id, fallback_text=req.case_text or (req.case_data or {}).get("text"))
    text = enriched.get("text") or await fetch_case_text(req.case_id)

    case_name = (req.case_data or {}).get("caseName") or (req.case_data or {}).get("case_name") or req.case_id
    court = (req.case_data or {}).get("court_citation_string") or (req.case_data or {}).get("court_name") or "Unknown"
    decision = (req.case_data or {}).get("disposition") or "Unknown"

    if not text or len(text) < 80:
        logger.info("RA Check: Insufficient text; returning concise factual fallback.")
        return SummaryResponse(summary={"case": case_name, "court": court, "issue": "Insufficient text to summarize.", "decision": decision})

    # Summarize in chunks for robustness
    chunk = text[:2200]
    if summarizer is None:
        out = chunk[:400]
    else:
        out = summarizer(chunk, max_length=160, min_length=60, do_sample=False)[0]["summary_text"]

    entities = extract_entities(text)
    return SummaryResponse(summary={"case": case_name, "court": court, "issue": out, "decision": decision, "entities": entities})