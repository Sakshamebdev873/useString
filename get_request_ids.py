"""Fetch Ajio and Nykaa through String's API and print each request ID.

Usage (PowerShell):
    $env:STRING_API_KEY = "your-web-access-key"
    python get_request_ids.py
"""
import os
import sys

import requests

API = "https://request.usestring.ai/v1/fetch"
TARGETS = [
    "https://www.ajio.com/men-tshirts/c/830216014",
    "https://www.nykaa.com/search/result/?q=lipstick",
]

key = os.environ.get("STRING_API_KEY")
if not key:
    sys.exit("Set STRING_API_KEY first (your Web Access API key).")

for url in TARGETS:
    print(f"\n=== {url}")
    try:
        r = requests.post(
            API,
            headers={"Authorization": f"Bearer {key}"},
            json={"url": url, "format": "markdown"},
            timeout=200,  # Ajio took ~1.5 min to fail last time
        )
    except requests.RequestException as e:
        print("Request error:", e)
        continue

    print("HTTP status :", r.status_code)
    for name, value in r.headers.items():
        if "request-id" in name.lower() or "trace-id" in name.lower():
            print(f"{name:12}:", value)
    print("Body (first 300 chars):", r.text[:300].replace("\n", " "))
