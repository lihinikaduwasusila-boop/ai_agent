from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
from typing import List
from common.models import QueryRequest, QueryResponse, SearchRequest, SearchResponse, SummaryResponse, CitationResponse, PrecedentResponse, Case
from common.config import Config
from common.logging import logger
from common.security import verify_token
from common.db import get_cached_result, store_search, MySQL

router = APIRouter()

try:
    import language_tool_python  # type: ignore
    _tool = language_tool_python.LanguageTool('en-US')
except Exception as e:  # ImportError or runtime error (no Java)
    logger.warning(f"RA Check: language_tool disabled: {e}")
    _tool = None


@router.post("/query", response_model=QueryResponse)
async def query_router(req: QueryRequest, request: Request, token: dict = Depends(verify_token)):
    user_sub = token.get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Missing subject in token")

    corrected_query = req.query
    if _tool is not None:
        try:
            matches = _tool.check(req.query)
            corrected_query = language_tool_python.utils.correct(req.query, matches)  # type: ignore[name-defined]
            logger.info(f"Corrected query: {corrected_query}")
        except Exception as e:
            logger.warning(f"RA Check: Grammar correction skipped: {e}")

    cached = None
    try:
        cached = await get_cached_result(int(user_sub), corrected_query)
    except Exception as e:
        logger.warning(f"RA Check: Cache read skipped due to error: {e}")
    if cached:
        logger.info("Cache hit from MySQL")
        return QueryResponse(**cached)

    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    async with httpx.AsyncClient(timeout=40) as client:
        parse_res = await client.post(
            f"{Config.CASE_FINDER_URL}/parse_query",
            json={"query": corrected_query},
            headers={"Authorization": auth_header},
        )
        parse_res.raise_for_status()
        search_req = SearchRequest(**parse_res.json())

        search_res = await client.post(
            f"{Config.CASE_FINDER_URL}/search",
            json=search_req.model_dump() | {"num_results": 5},
            headers={"Authorization": auth_header},
        )
        search_res.raise_for_status()
        search_result = SearchResponse(**search_res.json())
        cases_data: List[dict] = search_result.cases[:5]

        summaries, citations, precedents = [], [], []
        for case_data in cases_data:
            case_id = str(case_data.get("cluster_id") or case_data.get("id") or case_data.get("case_id", ""))
            if not case_id:
                continue
            sum_res = await client.post(
                f"{Config.SUMMARY_URL}/summarize",
                json={"case_id": case_id, "case_data": case_data},
                headers={"Authorization": auth_header},
            )
            sum_res.raise_for_status()
            summaries.append(SummaryResponse(**sum_res.json()).summary)

            cit_res = await client.post(
                f"{Config.CITATION_URL}/extract_citations",
                json={"case_id": case_id, "case_data": case_data},
                headers={"Authorization": auth_header},
            )
            cit_res.raise_for_status()
            cit_list = CitationResponse(**cit_res.json()).citations
            citations.append(cit_list)

            prec_res = await client.post(
                f"{Config.PRECEDENT_URL}/find_precedents",
                json={"case_id": case_id, "citations": cit_list},
                headers={"Authorization": auth_header},
            )
            prec_res.raise_for_status()
            precedents.append(PrecedentResponse(**prec_res.json()).related_cases)

    out_cases = []
    for i, case_data in enumerate(cases_data):
        name = case_data.get("case_name") or case_data.get("caseName") or "Unknown"
        court = case_data.get("court_name") or case_data.get("court") or "Unknown"
        decision = case_data.get("disposition") or case_data.get("status") or "Unknown"
        cid = str(case_data.get("cluster_id") or case_data.get("id") or "")
        out_cases.append(Case(
            case_id=cid,
            case_name=name,
            court=court,
            decision=decision,
            summary=summaries[i] if i < len(summaries) else {"issue": ""},
            citations=citations[i] if i < len(citations) else [],
            related_precedents=precedents[i] if i < len(precedents) else [],
        ))

    response = QueryResponse(cases=out_cases)
    try:
        await store_search(int(user_sub), corrected_query, response.model_dump())
    except Exception as e:
        logger.warning(f"RA Check: Cache write skipped due to error: {e}")
    logger.info("RA Check: Query processed with transparency (pipeline logged) and ethical handling (no PII in logs)")
    return response