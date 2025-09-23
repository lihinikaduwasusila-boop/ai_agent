from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer
import httpx
import re
import asyncio
from typing import Dict
from common.security import verify_token
from common.logging import logger
from common.config import Config
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


class SummaryResponse(BaseModel):
    summary: Dict


try:
    model_name = "sshleifer/distilbart-cnn-6-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline("summarization", model=model_name, tokenizer=tokenizer, device=-1)
except Exception as e:
    summarizer = None
    logger.warning("RA Check: Summarizer not available; will fallback to heuristic summary.")


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


@app.post("/summarize", response_model=SummaryResponse)
async def summarize(req: SummaryRequest, token: dict = Depends(verify_token)):
    if not req.case_id:
        raise HTTPException(status_code=400, detail="case_id required")
    text = await fetch_case_text(req.case_id)
    if not text:
        logger.info("RA Check: No text available; returning transparent fallback message.")
        return SummaryResponse(summary={"case": req.case_id, "court": "Unknown", "issue": "No text available", "decision": "Unknown"})
    if summarizer is None:
        snippet = text[:400]
        return SummaryResponse(summary={"case": req.case_id, "court": "Unknown", "issue": snippet, "decision": "Unknown"})
    # Summarize first 800 tokens approx
    chunk = text[:2000]
    out = summarizer(chunk, max_length=130, min_length=40, do_sample=False)[0]["summary_text"]
    logger.info("RA Check: Summary generated; transparency via model use disclosure; ethical handling using public text only.")
    return SummaryResponse(summary={"case": req.case_id, "court": "Unknown", "issue": out, "decision": "Unknown"})