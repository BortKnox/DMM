import os
import re
import base64
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

ENV_TORBOX_KEY = os.environ.get("TORBOX_API_KEY", "")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

TORBOX_API = "https://api.torbox.app/v1/api"
TMDB_API = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"

TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://explodie.org:6969/announce",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("dmm")

app = FastAPI(title="DMM - Debrid Media Manager")
api_router = APIRouter(prefix="/api")

CONFIG_ID = "app_config"
DEFAULT_SOURCES = ["apibay", "eztv"]


# ------------------------- Config helpers -------------------------
async def get_config():
    doc = await db.config.find_one({"_id": CONFIG_ID})
    if not doc:
        doc = {"_id": CONFIG_ID, "torbox_api_key": "", "sources": DEFAULT_SOURCES}
        await db.config.insert_one(doc)
    return doc


async def get_torbox_key() -> str:
    doc = await get_config()
    return (doc.get("torbox_api_key") or "").strip() or ENV_TORBOX_KEY


def tb_headers(key: str):
    return {"Authorization": f"Bearer {key}"}


# ------------------------- Quality parsing -------------------------
def parse_quality(name: str) -> dict:
    n = name.lower()
    res = None
    for r, pat in [("2160p", r"2160p|4k|uhd"), ("1080p", r"1080p|1080i"),
                   ("720p", r"720p"), ("480p", r"480p"), ("SD", r"dvdrip|xvid")]:
        if re.search(pat, n):
            res = r if r != "SD" else "480p"
            break
    source = None
    for s, pat in [("REMUX", r"remux"), ("BluRay", r"blu-?ray|bdrip|brrip|bdremux"),
                   ("WEB-DL", r"web-?dl"), ("WEBRip", r"web-?rip"),
                   ("HDRip", r"hdrip"), ("HDTV", r"hdtv"), ("CAM", r"\bcam\b|hdcam|ts\b")]:
        if re.search(pat, n):
            source = s
            break
    codec = None
    for c, pat in [("x265", r"x265|hevc|h\.?265"), ("AV1", r"av1"), ("x264", r"x264|h\.?264|avc")]:
        if re.search(pat, n):
            codec = c
            break
    hdr = []
    if re.search(r"dolby.?vision|\bdv\b|dovi", n):
        hdr.append("DV")
    if re.search(r"hdr10\+|hdr", n):
        hdr.append("HDR")
    audio = None
    for a, pat in [("Atmos", r"atmos"), ("TrueHD", r"truehd"), ("DTS-HD", r"dts-?hd"),
                   ("DTS", r"\bdts\b"), ("DDP", r"ddp|dd\+|eac3"), ("AC3", r"ac3|dd5")]:
        if re.search(pat, n):
            audio = a
            break
    return {"resolution": res, "source": source, "codec": codec, "hdr": hdr, "audio": audio}


def res_rank(res: Optional[str]) -> int:
    return {"2160p": 4, "1080p": 3, "720p": 2, "480p": 1}.get(res or "", 0)


def build_magnet(h: str, name: str) -> str:
    trk = "".join(f"&tr={quote(t)}" for t in TRACKERS)
    return f"magnet:?xt=urn:btih:{h}&dn={quote(name)}{trk}"


def human_size(b) -> str:
    try:
        b = float(b)
    except (TypeError, ValueError):
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} PB"


# ------------------------- Indexers -------------------------
async def idx_apibay(http: httpx.AsyncClient, imdb_id: str) -> List[dict]:
    out = []
    try:
        r = await http.get(f"https://apibay.org/q.php?q={imdb_id}", timeout=15)
        data = r.json()
        for it in data:
            h = it.get("info_hash")
            if not h or h == "0000000000000000000000000000000000000000":
                continue
            out.append({
                "hash": h.lower(),
                "name": it.get("name", ""),
                "size": int(it.get("size", 0) or 0),
                "seeders": int(it.get("seeders", 0) or 0),
                "tracker": "TPB",
                "source_indexer": "apibay",
            })
    except Exception as e:
        logger.warning(f"apibay failed: {e}")
    return out


async def idx_eztv(http: httpx.AsyncClient, imdb_id: str, season=None, episode=None) -> List[dict]:
    out = []
    num = imdb_id.replace("tt", "")
    try:
        page = 1
        while page <= 3:
            r = await http.get(f"https://eztvx.to/api/get-torrents?imdb_id={num}&limit=100&page={page}", timeout=15)
            data = r.json()
            torrents = data.get("torrents", []) or []
            if not torrents:
                break
            for it in torrents:
                h = it.get("hash")
                if not h:
                    continue
                s = int(it.get("season", 0) or 0)
                e = int(it.get("episode", 0) or 0)
                if season is not None and s != int(season):
                    continue
                if episode is not None and e != int(episode):
                    continue
                out.append({
                    "hash": h.lower(),
                    "name": it.get("title", ""),
                    "size": int(it.get("size_bytes", 0) or 0),
                    "seeders": int(it.get("seeds", 0) or 0),
                    "tracker": "EZTV",
                    "source_indexer": "eztv",
                    "season": s,
                    "episode": e,
                })
            if len(torrents) < 100:
                break
            page += 1
    except Exception as e:
        logger.warning(f"eztv failed: {e}")
    return out


async def gather_sources(imdb_id: str, media_type: str, season=None, episode=None,
                         sources: Optional[List[str]] = None) -> List[dict]:
    sources = sources or DEFAULT_SOURCES
    async with httpx.AsyncClient(follow_redirects=True) as http:
        tasks = []
        if "apibay" in sources:
            tasks.append(idx_apibay(http, imdb_id))
        if "eztv" in sources and media_type == "series":
            tasks.append(idx_eztv(http, imdb_id, season, episode))
        results = await asyncio.gather(*tasks, return_exceptions=True)
    merged = {}
    for res in results:
        if isinstance(res, Exception):
            continue
        for it in res:
            if it["hash"] not in merged or it["seeders"] > merged[it["hash"]]["seeders"]:
                merged[it["hash"]] = it
    return list(merged.values())


async def check_cached(hashes: List[str], key: str) -> set:
    if not hashes:
        return set()
    cached = set()
    async with httpx.AsyncClient() as http:
        for i in range(0, len(hashes), 80):
            chunk = hashes[i:i + 80]
            params = [("hash", h) for h in chunk]
            params += [("format", "list"), ("list_files", "false")]
            try:
                r = await http.get(f"{TORBOX_API}/torrents/checkcached", params=params,
                                   headers=tb_headers(key), timeout=20)
                data = r.json().get("data") or []
                if isinstance(data, dict):
                    data = list(data.values())
                for it in data:
                    h = (it.get("hash") if isinstance(it, dict) else it)
                    if h:
                        cached.add(str(h).lower())
            except Exception as e:
                logger.warning(f"checkcached failed: {e}")
    return cached


# ------------------------- TorBox actions -------------------------
async def torbox_add(magnet: str, key: str, name: str = None) -> dict:
    async with httpx.AsyncClient() as http:
        form = {"magnet": magnet, "seed": "3", "allow_zip": "true"}
        if name:
            form["name"] = name
        r = await http.post(f"{TORBOX_API}/torrents/createtorrent", data=form,
                            headers=tb_headers(key), timeout=30)
        return r.json()


async def torbox_torrent_files(torrent_id: int, key: str) -> Optional[dict]:
    async with httpx.AsyncClient() as http:
        try:
            r = await http.get(f"{TORBOX_API}/torrents/mylist",
                              params={"id": torrent_id, "bypass_cache": "true"},
                              headers=tb_headers(key), timeout=20)
            data = r.json().get("data")
            if isinstance(data, list):
                data = data[0] if data else None
            return data
        except Exception as e:
            logger.warning(f"torrent files fetch failed: {e}")
            return None


def pick_file(files: List[dict], season=None, episode=None) -> int:
    vids = [f for f in files if re.search(r"\.(mkv|mp4|avi|m4v|ts|mov)$", f.get("name", ""), re.I)]
    if not vids:
        vids = files
    if season is not None and episode is not None:
        pats = [
            re.compile(rf"s0*{int(season)}[\s._-]*e0*{int(episode)}", re.I),
            re.compile(rf"\b{int(season)}x0*{int(episode)}\b", re.I),
        ]
        for f in vids:
            nm = f.get("name", "")
            if any(p.search(nm) for p in pats):
                return f.get("id", 0)
    best = max(vids, key=lambda f: f.get("size", 0)) if vids else None
    return best.get("id", 0) if best else 0


async def resolve_stream(hash_: str, name: str, key: str, season=None, episode=None) -> Optional[str]:
    magnet = build_magnet(hash_, name or hash_)
    add = await torbox_add(magnet, key, name)
    data = add.get("data") or {}
    tid = data.get("torrent_id") or data.get("id")
    if not tid:
        return None
    file_id = 0
    for _ in range(2):
        info = await torbox_torrent_files(tid, key)
        files = (info or {}).get("files") or []
        if files:
            file_id = pick_file(files, season, episode)
            break
        await asyncio.sleep(1)
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/requestdl",
                          params={"token": key, "torrent_id": tid, "file_id": file_id},
                          headers=tb_headers(key), timeout=30)
        j = r.json()
        if j.get("success"):
            return j.get("data")
    return None


# ------------------------- TMDB -------------------------
async def tmdb_get(path: str, params: dict = None):
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TMDB_API}{path}", params=params, timeout=20)
        return r.json()


def map_tmdb_item(it: dict) -> Optional[dict]:
    mt = it.get("media_type")
    if mt not in ("movie", "tv") and "title" in it:
        mt = "movie"
    elif mt not in ("movie", "tv") and "name" in it:
        mt = "tv"
    if mt not in ("movie", "tv"):
        return None
    title = it.get("title") or it.get("name")
    date = it.get("release_date") or it.get("first_air_date") or ""
    return {
        "id": it.get("id"),
        "media_type": "series" if mt == "tv" else "movie",
        "title": title,
        "year": (date or "")[:4],
        "overview": it.get("overview", ""),
        "poster": f"{TMDB_IMG}/w500{it['poster_path']}" if it.get("poster_path") else None,
        "backdrop": f"{TMDB_IMG}/original{it['backdrop_path']}" if it.get("backdrop_path") else None,
        "rating": round(it.get("vote_average", 0) or 0, 1),
    }


# ------------------------- API MODELS -------------------------
class SettingsIn(BaseModel):
    torbox_api_key: Optional[str] = None
    sources: Optional[List[str]] = None


class ResolveIn(BaseModel):
    hash: str
    name: str
    season: Optional[int] = None
    episode: Optional[int] = None


class AddIn(BaseModel):
    hash: str
    name: str


# ------------------------- ROUTES -------------------------
@api_router.get("/")
async def root():
    return {"message": "DMM API online"}


@api_router.get("/config")
async def config():
    doc = await get_config()
    key = (doc.get("torbox_api_key") or "").strip() or ENV_TORBOX_KEY
    connected = False
    account = None
    if key:
        try:
            async with httpx.AsyncClient() as http:
                r = await http.get(f"{TORBOX_API}/user/me", headers=tb_headers(key), timeout=15)
                j = r.json()
                connected = bool(j.get("success"))
                d = j.get("data") or {}
                account = {"email": d.get("email"), "plan": d.get("plan"), "premium": d.get("plan") != 0}
        except Exception:
            connected = False
    return {
        "torbox_connected": connected,
        "torbox_account": account,
        "has_custom_key": bool((doc.get("torbox_api_key") or "").strip()),
        "sources": doc.get("sources", DEFAULT_SOURCES),
        "available_sources": [
            {"id": "apibay", "name": "The Pirate Bay", "types": ["movie", "series"]},
            {"id": "eztv", "name": "EZTV (TV Shows)", "types": ["series"]},
        ],
    }


@api_router.post("/settings")
async def update_settings(body: SettingsIn):
    update = {}
    if body.torbox_api_key is not None:
        update["torbox_api_key"] = body.torbox_api_key.strip()
    if body.sources is not None:
        update["sources"] = body.sources
    if update:
        await db.config.update_one({"_id": CONFIG_ID}, {"$set": update}, upsert=True)
    return await config()


@api_router.get("/search")
async def search(q: str = Query(...)):
    data = await tmdb_get("/search/multi", {"query": q, "page": 1})
    items = [map_tmdb_item(it) for it in data.get("results", [])]
    return {"results": [i for i in items if i and i["poster"]]}


@api_router.get("/trending")
async def trending():
    data = await tmdb_get("/trending/all/week")
    items = [map_tmdb_item(it) for it in data.get("results", [])]
    return {"results": [i for i in items if i and i["poster"]]}


@api_router.get("/discover/{media_type}")
async def discover(media_type: str):
    mt = "tv" if media_type == "series" else "movie"
    data = await tmdb_get(f"/{mt}/popular")
    items = []
    for it in data.get("results", []):
        it["media_type"] = mt
        m = map_tmdb_item(it)
        if m and m["poster"]:
            items.append(m)
    return {"results": items}


@api_router.get("/meta/{media_type}/{tmdb_id}")
async def meta(media_type: str, tmdb_id: int):
    mt = "tv" if media_type == "series" else "movie"
    data = await tmdb_get(f"/{mt}/{tmdb_id}", {"append_to_response": "external_ids,credits"})
    ext = data.get("external_ids", {})
    imdb_id = ext.get("imdb_id")
    m = map_tmdb_item({**data, "media_type": mt})
    seasons = []
    if mt == "tv":
        for s in data.get("seasons", []):
            if s.get("season_number", 0) == 0:
                continue
            seasons.append({
                "season_number": s.get("season_number"),
                "name": s.get("name"),
                "episode_count": s.get("episode_count"),
            })
    m.update({
        "imdb_id": imdb_id,
        "genres": [g["name"] for g in data.get("genres", [])],
        "runtime": data.get("runtime") or (data.get("episode_run_time") or [None])[0],
        "seasons": seasons,
        "tagline": data.get("tagline"),
    })
    return m


@api_router.get("/season/{tmdb_id}/{season_number}")
async def season_eps(tmdb_id: int, season_number: int):
    data = await tmdb_get(f"/tv/{tmdb_id}/season/{season_number}")
    eps = [{
        "episode_number": e.get("episode_number"),
        "name": e.get("name"),
        "overview": e.get("overview", ""),
        "still": f"{TMDB_IMG}/w300{e['still_path']}" if e.get("still_path") else None,
        "air_date": e.get("air_date"),
    } for e in data.get("episodes", [])]
    return {"episodes": eps}


@api_router.get("/sources/{imdb_id}")
async def sources(imdb_id: str, media_type: str = "movie",
                  season: Optional[int] = None, episode: Optional[int] = None):
    doc = await get_config()
    key = (doc.get("torbox_api_key") or "").strip() or ENV_TORBOX_KEY
    items = await gather_sources(imdb_id, media_type, season, episode, doc.get("sources", DEFAULT_SOURCES))
    cached = await check_cached([i["hash"] for i in items], key) if key else set()
    out = []
    for it in items:
        q = parse_quality(it["name"])
        out.append({
            **it,
            "size_h": human_size(it["size"]),
            "cached": it["hash"] in cached,
            "quality": q,
            "res_rank": res_rank(q["resolution"]),
            "magnet": build_magnet(it["hash"], it["name"]),
        })
    out.sort(key=lambda x: (x["cached"], x["res_rank"], x["seeders"]), reverse=True)
    return {"sources": out, "total": len(out), "cached_count": sum(1 for o in out if o["cached"])}


@api_router.post("/torbox/add")
async def add_to_torbox(body: AddIn):
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    res = await torbox_add(build_magnet(body.hash, body.name), key, body.name)
    return res


@api_router.post("/torbox/resolve")
async def resolve(body: ResolveIn):
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    url = await resolve_stream(body.hash, body.name, key, body.season, body.episode)
    if not url:
        raise HTTPException(502, "Could not resolve stream from TorBox")
    return {"url": url}


@api_router.get("/library")
async def library():
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/mylist", params={"bypass_cache": "true"},
                          headers=tb_headers(key), timeout=30)
        data = r.json().get("data") or []
    out = []
    for it in data:
        out.append({
            "id": it.get("id"),
            "name": it.get("name"),
            "hash": it.get("hash"),
            "size": it.get("size"),
            "size_h": human_size(it.get("size")),
            "state": it.get("download_state"),
            "progress": round((it.get("progress") or 0) * 100),
            "cached": it.get("download_state") == "cached" or (it.get("progress") or 0) >= 1,
            "download_present": it.get("download_present"),
            "created_at": it.get("created_at"),
            "files": [{"id": f.get("id"), "name": f.get("name"), "size": f.get("size"),
                       "size_h": human_size(f.get("size"))} for f in (it.get("files") or [])],
        })
    return {"library": out, "total": len(out)}


@api_router.delete("/library/{torrent_id}")
async def delete_lib(torrent_id: int):
    key = await get_torbox_key()
    async with httpx.AsyncClient() as http:
        r = await http.post(f"{TORBOX_API}/torrents/controltorrent",
                          json={"torrent_id": torrent_id, "operation": "delete"},
                          headers=tb_headers(key), timeout=20)
        return r.json()


@api_router.get("/library/dl/{torrent_id}/{file_id}")
async def library_dl(torrent_id: int, file_id: int):
    key = await get_torbox_key()
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/requestdl",
                          params={"token": key, "torrent_id": torrent_id, "file_id": file_id},
                          headers=tb_headers(key), timeout=30)
        j = r.json()
    if j.get("success"):
        return {"url": j.get("data")}
    raise HTTPException(502, "Could not get download link")


# ------------------------- STREMIO ADDON -------------------------
def public_base(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    proto = request.headers.get("x-forwarded-proto")
    if not proto:
        proto = "http" if host.startswith("localhost") or host.startswith("127.") else "https"
    if host:
        return f"{proto}://{host}"
    return str(request.base_url).rstrip("/")


def decode_config(cfg: str) -> dict:
    try:
        pad = cfg + "=" * (-len(cfg) % 4)
        return json.loads(base64.urlsafe_b64decode(pad).decode())
    except Exception:
        return {}


@api_router.post("/stremio/manifest-url")
async def stremio_manifest_url(body: SettingsIn, request: Request):
    doc = await get_config()
    key = (body.torbox_api_key or "").strip() or (doc.get("torbox_api_key") or "").strip() or ENV_TORBOX_KEY
    srcs = body.sources or doc.get("sources", DEFAULT_SOURCES)
    cfg = {"k": key, "s": srcs}
    enc = base64.urlsafe_b64encode(json.dumps(cfg).encode()).decode().rstrip("=")
    base = public_base(request)
    url = f"{base}/api/stremio/{enc}/manifest.json"
    return {"config": enc, "manifest_url": url,
            "install_url": url.replace("https://", "stremio://").replace("http://", "stremio://")}


def _manifest(cfg: str):
    return {
        "id": "com.dmm.torbox",
        "version": "1.0.0",
        "name": "DMM - Debrid Media Manager",
        "description": "TorBox cached streams & your library, powered by Debrid Media Manager.",
        "logo": "https://images.unsplash.com/photo-1687618049680-3b334671044c?w=256",
        "resources": ["stream", "catalog", "meta"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt", "dmm:"],
        "catalogs": [
            {"type": "movie", "id": "dmm_library_movie", "name": "DMM TorBox Library"},
            {"type": "series", "id": "dmm_library_series", "name": "DMM TorBox Library"},
        ],
        "behaviorHints": {"configurable": True, "configurationRequired": False},
    }


@api_router.get("/stremio/{cfg}/manifest.json")
async def stremio_manifest(cfg: str):
    return JSONResponse(_manifest(cfg))


@api_router.get("/stremio/{cfg}/stream/{type}/{video_id}.json")
async def stremio_stream(cfg: str, type: str, video_id: str, request: Request):
    conf = decode_config(cfg)
    key = conf.get("k") or ENV_TORBOX_KEY
    srcs = conf.get("s") or DEFAULT_SOURCES
    vid = video_id.replace(".json", "")
    parts = vid.split(":")
    imdb_id = parts[0]
    season = int(parts[1]) if len(parts) > 1 else None
    episode = int(parts[2]) if len(parts) > 2 else None
    media_type = "series" if type == "series" else "movie"
    items = await gather_sources(imdb_id, media_type, season, episode, srcs)
    cached = await check_cached([i["hash"] for i in items], key)
    for i in items:
        i["cached"] = i["hash"].lower() in cached
        i["q"] = parse_quality(i["name"])
        i["rr"] = res_rank(i["q"]["resolution"])
    items.sort(key=lambda x: (x["cached"], x["rr"], x["seeders"]), reverse=True)
    items = items[:40]
    base = public_base(request)
    streams = []
    for it in items:
        q = it["q"]
        tags = " ".join(filter(None, [q["resolution"], q["source"], q["codec"], *(q["hdr"])]))
        badge = "⚡ Cached" if it["cached"] else "⬇ Download"
        ep = f"/{season}/{episode}" if season is not None else "/-/-"
        url = f"{base}/api/stremio/{cfg}/resolve/{it['hash']}{ep}/{quote(it['name'][:120])}"
        streams.append({
            "name": f"DMM TorBox\n{q['resolution'] or 'SD'}",
            "title": f"{badge} | {tags or 'Unknown'}\n{it['name']}\n💾 {human_size(it['size'])} | 👤 {it['seeders']} | {it['tracker']}",
            "url": url,
            "behaviorHints": {"bingeGroup": f"dmm-{q['resolution']}", "notWebReady": True},
        })
    return JSONResponse({"streams": streams})


@api_router.get("/stremio/{cfg}/resolve/{hash_}/{season}/{episode}/{name}")
async def stremio_resolve(cfg: str, hash_: str, season: str, episode: str, name: str):
    conf = decode_config(cfg)
    key = conf.get("k") or ENV_TORBOX_KEY
    s = int(season) if season not in ("-", "") else None
    e = int(episode) if episode not in ("-", "") else None
    url = await resolve_stream(hash_, name, key, s, e)
    if not url:
        raise HTTPException(502, "Could not resolve")
    return RedirectResponse(url)


async def _library_catalog(key: str, media_type: str, base: str, cfg: str):
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/mylist", params={"bypass_cache": "true"},
                          headers=tb_headers(key), timeout=30)
        data = r.json().get("data") or []
    metas = []
    for it in data:
        name = it.get("name", "")
        q = parse_quality(name)
        is_series = bool(re.search(r"s\d{1,2}e\d{1,2}|season|complete", name, re.I))
        want = "series" if is_series else "movie"
        if want != media_type:
            continue
        poster = None
        try:
            clean = re.sub(r"[\._]", " ", name)
            clean = re.split(r"\b(19|20)\d{2}\b|\b(1080p|720p|2160p|s\d)", clean, flags=re.I)[0].strip()
            sd = await tmdb_get("/search/multi", {"query": clean[:60]})
            for cand in sd.get("results", []):
                m = map_tmdb_item(cand)
                if m and m["poster"]:
                    poster = m["poster"]
                    break
        except Exception:
            pass
        metas.append({
            "id": f"dmm:{it.get('id')}",
            "type": media_type,
            "name": name[:80],
            "poster": poster or "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=300",
            "description": f"{q['resolution'] or ''} {q['source'] or ''} • {human_size(it.get('size'))}",
        })
    return metas


@api_router.get("/stremio/{cfg}/catalog/{type}/{id}.json")
async def stremio_catalog(cfg: str, type: str, id: str, request: Request):
    conf = decode_config(cfg)
    key = conf.get("k") or ENV_TORBOX_KEY
    base = public_base(request)
    metas = await _library_catalog(key, type, base, cfg)
    return JSONResponse({"metas": metas})


@api_router.get("/stremio/{cfg}/meta/{type}/{id}.json")
async def stremio_meta(cfg: str, type: str, id: str, request: Request):
    conf = decode_config(cfg)
    key = conf.get("k") or ENV_TORBOX_KEY
    idv = id.replace(".json", "")
    if not idv.startswith("dmm:"):
        return JSONResponse({"meta": {}})
    tid = int(idv.split(":")[1])
    info = await torbox_torrent_files(tid, key)
    if not info:
        return JSONResponse({"meta": {}})
    base = public_base(request)
    files = [f for f in (info.get("files") or []) if re.search(r"\.(mkv|mp4|avi|m4v|ts)$", f.get("name", ""), re.I)]
    videos = []
    for f in files:
        videos.append({
            "id": f"dmm:{tid}:{f.get('id')}",
            "title": os.path.basename(f.get("name", "")),
            "released": info.get("created_at"),
        })
    meta = {
        "id": idv, "type": type, "name": info.get("name", "")[:80],
        "poster": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=300",
        "description": f"TorBox • {human_size(info.get('size'))}",
    }
    if type == "series" and videos:
        meta["videos"] = videos
    return JSONResponse({"meta": meta})


@api_router.get("/stremio/{cfg}/stream/dmm/{tid}/{fid}.json")
async def stremio_lib_stream(cfg: str, tid: int, fid: int, request: Request):
    conf = decode_config(cfg)
    key = conf.get("k") or ENV_TORBOX_KEY
    base = public_base(request)
    url = f"{base}/api/stremio/{cfg}/libresolve/{tid}/{fid}"
    return JSONResponse({"streams": [{"name": "DMM TorBox", "title": "Play from Library", "url": url}]})


@api_router.get("/stremio/{cfg}/libresolve/{tid}/{fid}")
async def stremio_lib_resolve(cfg: str, tid: int, fid: int):
    conf = decode_config(cfg)
    key = conf.get("k") or ENV_TORBOX_KEY
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/requestdl",
                          params={"token": key, "torrent_id": tid, "file_id": fid},
                          headers=tb_headers(key), timeout=30)
        j = r.json()
    if j.get("success"):
        return RedirectResponse(j.get("data"))
    raise HTTPException(502, "Could not resolve")


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
