"""Shared HTTP helpers for scrapers — $0 cost, no paid APIs."""
import os
import time

import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/json,*/*",
}


def get_json(url: str, *, params=None, headers=None, timeout=15, retries=2):
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=merged, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last_err = exc
            time.sleep(1 + attempt)
    raise last_err


def get_text(url: str, *, params=None, headers=None, timeout=15, retries=2) -> str:
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=merged, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.text
        except Exception as exc:
            last_err = exc
            time.sleep(1 + attempt)
    raise last_err


def github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "employer-discovery-pipeline",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers