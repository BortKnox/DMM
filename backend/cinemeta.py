"""Keyless movie and series metadata from the public Cinemeta catalogue."""
import asyncio
import re
from collections import Counter
from urllib.parse import quote

import httpx
from fastapi import HTTPException

BASE = "https://v3-cinemeta.strem.io"
PAGE_SIZE = 20


async def request(path):
    try:
        async with httpx.AsyncClient(timeout=14, follow_redirects=True) as client:
            response = await client.get(f"{BASE}/{path}.json")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(code, "Catalogue request failed") from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(502, "Catalogue is unavailable") from exc


def card(item):
    return {
        "id": item["imdb_id"] if item.get("imdb_id") else item["id"],
        "media_type": item["type"], "title": item["name"],
        "poster": item.get("poster"), "backdrop": item.get("background"),
        "year": str(item.get("releaseInfo") or item.get("year") or "")[:4],
        "rating": item.get("imdbRating"), "overview": item.get("description") or "",
    }


def paginate(items, page):
    start = (page - 1) * PAGE_SIZE
    return {"results": items[start:start + PAGE_SIZE], "page": page,
            "total_results": len(items), "total_pages": max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)}


async def catalogue(kind, query=None):
    if kind not in ("movie", "series"):
        raise HTTPException(404, "Unknown catalogue")
    extra = "/search=" + quote(query, safe="") if query else ""
    data = await request(f"catalog/{kind}/top{extra}")
    return [card(m) for m in data.get("metas", []) if m.get("name") and m.get("id")]


async def search(query, page):
    movies, series = await asyncio.gather(catalogue("movie", query), catalogue("series", query))
    items = movies + series
    items.sort(key=lambda m: m["title"].casefold() != query.casefold())
    return paginate(items, page)


async def details(kind, imdb):
    if kind not in ("movie", "series") or not re.fullmatch(r"tt\d+", imdb):
        raise HTTPException(404, "Unknown title")
    item = (await request(f"meta/{kind}/{imdb}")).get("meta")
    if not item:
        raise HTTPException(404, "Title unavailable")
    videos = [v for v in item.get("videos", []) if isinstance(v.get("season"), int) and v["season"] > 0 and isinstance(v.get("episode"), int)]
    counts = Counter(v["season"] for v in videos)
    runtime = re.match(r"\d+", str(item.get("runtime") or ""))
    info = {**card(item), "imdb_id": imdb, "genres": item.get("genres", []),
            "runtime": int(runtime.group()) if runtime else None,
            "seasons": [{"season_number": n, "episode_count": counts[n]} for n in sorted(counts)]}
    return info, videos
