THIS SHOULD BE A LINTER ERRORimport re
from typing import Dict, Any, Optional, Tuple
import httpx
from .config import Config
from .logging import logger


HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _fetch_courtlistener_text(cluster_id: str) -> Tuple[str, Dict[str, Any]]:
    if not Config.COURTLISTENER_BASE_URL:
        return "", {}
    headers = {"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(
                f"{Config.COURTLISTENER_BASE_URL}opinions/",
                params={
                    "cluster": cluster_id,
                    "fields": "id,text,html_lawbox,html_columbia,html,html_with_citations,caseName,disposition,court_citation_string",
                },
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            opinion = (data.get("results") or [{}])[0]
            raw = (
                opinion.get("text")
                or opinion.get("html_lawbox")
                or opinion.get("html_columbia")
                or opinion.get("html")
                or opinion.get("html_with_citations")
                or ""
            )
            meta = {
                "caseName": opinion.get("caseName", ""),
                "court_citation_string": opinion.get("court_citation_string", ""),
                "disposition": opinion.get("disposition", ""),
            }
            return _clean_text(raw), meta
        except Exception as e:
            logger.warning(f"CourtListener fetch failed for {cluster_id}: {e}")
            return "", {}


async def _fetch_cap_text(cluster_id: str) -> Tuple[str, Dict[str, Any]]:
    # Optional: Harvard Caselaw Access Project by citation if available in case_data; here we only try by cluster id as a placeholder
    base = Config.CAP_BASE_URL
    api_key = Config.CAP_API_KEY
    if not base or not api_key:
        return "", {}
    headers = {"Authorization": f"Token {api_key}"}
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            # This endpoint is illustrative; CAP often needs reporter citation. Keep robust: will 404 harmlessly.
            r = await client.get(f"{base}clusters/{cluster_id}/", headers=headers)
            if r.status_code != 200:
                return "", {}
            data = r.json()
            opinions = data.get("opinions", [])
            raw = opinions[0].get("text", "") if opinions else ""
            return _clean_text(raw), {}
        except Exception as e:
            logger.info(f"CAP fetch unavailable/failed for {cluster_id}: {e}")
            return "", {}


async def _fetch_oyez_text(cluster_id: str) -> Tuple[str, Dict[str, Any]]:
    # Oyez primarily by docket or slug; without mapping, we try a no-op
    base = Config. OYEZ_BASE_URL
    if not base:
        return "", {}
    try:
        # We do not have an id map; skip to avoid noisy requests.
        return "", {}
    except Exception:
        return "", {}


async def enrich_case_text(cluster_id: str, fallback_text: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate text from multiple sources and return best text and metadata.

    Returns: { text: str, source: str, meta: dict }
    """
    # 1) CourtListener (primary)
    text, meta = await _fetch_courtlistener_text(cluster_id)
    if text and len(text) >= 200:
        return {"text": text, "source": "courtlistener", "meta": meta}

    # 2) CAP (if configured)
    cap_text, cap_meta = await _fetch_cap_text(cluster_id)
    if cap_text and len(cap_text) > len(text):
        text, meta = cap_text, cap_meta
        source = "cap"
    else:
        source = "courtlistener" if text else ""

    # 3) Oyez (placeholder; not used without mapping)
    oyez_text, _ = await _fetch_oyez_text(cluster_id)
    if oyez_text and len(oyez_text) > len(text):
        text = oyez_text
        source = "oyez"

    # 4) Fallback to provided text
    if not text and fallback_text:
        text = _clean_text(fallback_text)
        source = source or "provided"

    return {"text": text or "", "source": source or "", "meta": meta or {}}

