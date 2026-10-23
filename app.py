"""Fetch endpoint for pages String's API fails on (Ajio, Nykaa, 99acres).

These sites run Akamai-style bot checks that reject clients whose TLS
handshake doesn't look like a real browser (plain `requests` gets a 403).
curl_cffi sends a real Chrome/Safari TLS + HTTP/2 fingerprint, so the
request looks like a normal browser visit and the full page comes back.

Run:   uvicorn app:app --host 0.0.0.0 --port 8000
Use:   GET /fetch?url=https://www.ajio.com/men-tshirts/c/830216014
       add &format=json for status/title/size metadata alongside the HTML.
"""
import re
import time
from urllib.parse import urlparse

from curl_cffi import requests as cc
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

# Only these hosts, so this can't be used as an open proxy.
ALLOWED_HOSTS = {"www.ajio.com", "www.nykaa.com", "www.99acres.com"}

# Browser fingerprints to try in order; fall back if the first is challenged.
PROFILES = ["chrome", "safari", "chrome131"]

BLOCK_MARKERS = ("Access Denied", "verifycaptcha", "data-label=\"CAPTCHA\"")

app = FastAPI(title="Fetch endpoint")


def looks_blocked(status: int, body: str) -> bool:
    return status in (403, 429) or any(m in body[:20000] for m in BLOCK_MARKERS)


def fetch(url: str) -> dict:
    last = None
    for profile in PROFILES:
        start = time.time()
        r = cc.get(
            url,
            impersonate=profile,
            timeout=30,
            headers={"Accept-Language": "en-IN,en;q=0.9"},
        )
        body = r.text
        last = {
            "url": url,
            "final_url": str(r.url),
            "status": r.status_code,
            "profile": profile,
            "bytes": len(body.encode("utf-8")),
            "ms": int((time.time() - start) * 1000),
            "blocked": looks_blocked(r.status_code, body),
            "html": body,
        }
        if not last["blocked"]:
            break
    title = re.search(r"<title[^>]*>(.*?)</title>", last["html"], re.S)
    last["title"] = title.group(1).strip() if title else None
    return last


@app.get("/")
def index():
    return {
        "usage": "/fetch?url=<page url>  (add &format=json for metadata)",
        "allowed_hosts": sorted(ALLOWED_HOSTS),
    }


@app.get("/fetch")
def fetch_page(url: str = Query(...), format: str = Query("html")):
    host = urlparse(url).hostname
    if urlparse(url).scheme != "https" or host not in ALLOWED_HOSTS:
        raise HTTPException(400, f"Only https URLs on {sorted(ALLOWED_HOSTS)}")
    try:
        result = fetch(url)
    except Exception as e:  # network errors, timeouts
        raise HTTPException(502, f"Upstream fetch failed: {e}")

    if format == "json":
        return JSONResponse(result)
    status = 502 if result["blocked"] else result["status"]
    return HTMLResponse(result["html"], status_code=status)
