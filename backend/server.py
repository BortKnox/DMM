import os
import re
import time
import base64
import json
import asyncio
import logging
import html as htmllib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

import cinemeta
import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

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
DEFAULT_SOURCES = ["apibay", "therarbg", "eztv"]

AVAILABLE_SOURCES = [
    {"id": "apibay", "name": "The Pirate Bay", "types": ["movie", "series"], "desc": "Huge general index, IMDB-matched"},
    {"id": "therarbg", "name": "TheRARBG", "types": ["movie", "series"], "desc": "RARBG successor, rich releases"},
    {"id": "torrentgalaxy", "name": "TorrentGalaxy", "types": ["movie", "series"], "desc": "Broad movie & TV catalog"},
    {"id": "eztv", "name": "EZTV", "types": ["series"], "desc": "Best for TV episodes & packs"},
    {"id": "limetorrents", "name": "LimeTorrents", "types": ["movie", "series"], "desc": "Title search, wide coverage"},
    {"id": "torrentdownloads", "name": "TorrentDownloads", "types": ["movie", "series"], "desc": "Title search, older & rare"},
    {"id": "nyaa", "name": "Nyaa", "types": ["series", "movie"], "desc": "Anime & Asian media"},
]

# ------------------------- simple TTL cache -------------------------
_CACHE = {}

def cache_get(key):
    v = _CACHE.get(key)
    if v and v[0] > time.time():
        return v[1]
    return None

def cache_set(key, val, ttl=900):
    _CACHE[key] = (time.time() + ttl, val)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ------------------------- Config helpers -------------------------
async def get_config():
    doc = await db.config.find_one({"_id": CONFIG_ID})
    if not doc:
        doc = {"_id": CONFIG_ID, "torbox_api_key": "", "tmdb_api_key": "", "sources": DEFAULT_SOURCES}
        await db.config.insert_one(doc)
    return doc


async def get_keys():
    doc = await get_config()
    return {
        "torbox": (doc.get("torbox_api_key") or "").strip(),
        "tmdb": (doc.get("tmdb_api_key") or "").strip(),
        "omdb": (doc.get("omdb_api_key") or "").strip(),
        "rpdb": (doc.get("rpdb_api_key") or "").strip(),
        "fanart": (doc.get("fanart_api_key") or "").strip(),
        "thetvdb": (doc.get("thetvdb_api_key") or "").strip(),
        "paypal_client_id": (doc.get("paypal_client_id") or "").strip(),
        "paypal_secret": (doc.get("paypal_secret") or "").strip(),
        "paypal_mode": (doc.get("paypal_mode") or "sandbox").strip(),
        "sources": doc.get("sources", DEFAULT_SOURCES),
    }


PAYPAL_TIERS = [
    {"id": "coffee", "label": "Buy a Coffee", "amount": 1, "perk": "Pro unlock + supporter badge"},
    {"id": "pro", "label": "Pro Supporter", "amount": 2, "perk": "Everything + Pro badge"},
    {"id": "founder", "label": "Founder", "amount": 5, "perk": "Everything + Founder badge"},
]


def paypal_api_base(mode):
    return "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"


async def paypal_token(keys):
    ck = ("ppt", keys["paypal_client_id"], keys["paypal_mode"])
    hit = cache_get(ck)
    if hit:
        return hit
    async with httpx.AsyncClient() as http:
        r = await http.post(f"{paypal_api_base(keys['paypal_mode'])}/v1/oauth2/token",
                            auth=(keys["paypal_client_id"], keys["paypal_secret"]),
                            data={"grant_type": "client_credentials"}, timeout=20)
        r.raise_for_status()
        tok = r.json()["access_token"]
    cache_set(ck, tok, 420)
    return tok


def tier_for_amount(amt):
    try:
        amt = float(amt)
    except (TypeError, ValueError):
        amt = 0
    if amt >= 5:
        return "founder"
    if amt >= 2:
        return "pro"
    return "coffee"


async def grant_pro(email, amount, order_id):
    email = (email or "").strip().lower()
    if not email:
        return None
    existing = await db.pro_users.find_one({"_id": email})
    total = (existing.get("total", 0) if existing else 0) + float(amount)
    tier = tier_for_amount(max(total, float(amount)))
    doc = {"_id": email, "tier": tier, "total": round(total, 2),
           "since": (existing.get("since") if existing else None) or now_iso(),
           "last_order": order_id, "updated": now_iso()}
    await db.pro_users.update_one({"_id": email}, {"$set": doc}, upsert=True)
    return doc


async def pro_status(email):
    email = (email or "").strip().lower()
    if not email:
        return {"pro": False}
    d = await db.pro_users.find_one({"_id": email})
    if not d:
        return {"pro": False, "email": email}
    return {"pro": True, "email": email, "tier": d.get("tier", "pro"),
            "total": d.get("total"), "since": d.get("since")}


async def get_torbox_key() -> str:
    return (await get_keys())["torbox"]


async def get_tmdb_key() -> str:
    return (await get_keys())["tmdb"]


def tb_headers(key: str):
    return {"Authorization": f"Bearer {key}"}


# ------------------------- Quality parsing -------------------------
def parse_quality(name: str) -> dict:
    n = name.lower()
    res = None
    for r, pat in [("2160p", r"2160p|\b4k\b|uhd"), ("1080p", r"1080p|1080i"),
                   ("720p", r"720p"), ("480p", r"480p|dvdrip|xvid")]:
        if re.search(pat, n):
            res = r
            break
    source = None
    for s, pat in [("REMUX", r"remux"), ("BluRay", r"blu-?ray|bdrip|brrip|bdremux"),
                   ("WEB-DL", r"web-?dl"), ("WEBRip", r"web-?rip|\bweb\b"),
                   ("HDRip", r"hdrip"), ("HDTV", r"hdtv"), ("CAM", r"\bcam\b|hdcam|\bts\b")]:
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
async def idx_apibay(http, imdb_id, **kw):
    out = []
    try:
        r = await http.get(f"https://apibay.org/q.php?q={imdb_id}", timeout=15)
        for it in r.json():
            h = it.get("info_hash")
            if not h or h == "0" * 40:
                continue
            out.append({"hash": h.lower(), "name": it.get("name", ""),
                        "size": int(it.get("size", 0) or 0), "seeders": int(it.get("seeders", 0) or 0),
                        "tracker": "TPB", "source_indexer": "apibay"})
    except Exception as e:
        logger.warning(f"apibay failed: {e}")
    return out


async def idx_therarbg(http, imdb_id, media_type="movie", **kw):
    out = []
    cat = "TV" if media_type == "series" else "Movies"
    try:
        r = await http.get(f"https://therarbg.com/get-posts/keywords:{imdb_id}:category:{cat}/?format=json", timeout=15)
        for it in r.json().get("results", []):
            h = it.get("h")
            if not h:
                continue
            out.append({"hash": h.lower(), "name": it.get("n", ""),
                        "size": int(it.get("s", 0) or 0), "seeders": int(it.get("se", 0) or 0),
                        "tracker": "RARBG", "source_indexer": "therarbg"})
    except Exception as e:
        logger.warning(f"therarbg failed: {e}")
    return out


async def idx_eztv(http, imdb_id, season=None, episode=None, **kw):
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
                out.append({"hash": h.lower(), "name": it.get("title", ""),
                            "size": int(it.get("size_bytes", 0) or 0), "seeders": int(it.get("seeds", 0) or 0),
                            "tracker": "EZTV", "source_indexer": "eztv", "season": s, "episode": e})
            if len(torrents) < 100:
                break
            page += 1
    except Exception as e:
        logger.warning(f"eztv failed: {e}")
    return out


async def idx_nyaa(http, imdb_id, title=None, season=None, episode=None, **kw):
    out = []
    if not title:
        return out
    q = title
    if season is not None and episode is not None:
        q = f"{title} S{int(season):02d}E{int(episode):02d}"
    try:
        r = await http.get(f"https://nyaa.si/?page=rss&q={quote(q)}&c=1_2&f=0", timeout=15)
        items = re.findall(r"<item>(.*?)</item>", r.text, re.S)
        for it in items[:60]:
            h = re.search(r"<nyaa:infoHash>([^<]+)", it)
            t = re.search(r"<title>([^<]+)", it)
            sz = re.search(r"<nyaa:size>([^<]+)", it)
            se = re.search(r"<nyaa:seeders>([^<]+)", it)
            if not h:
                continue
            size_b = 0
            if sz:
                m = re.match(r"([\d.]+)\s*(\w+)", sz.group(1))
                if m:
                    mult = {"GiB": 1073741824, "MiB": 1048576, "KiB": 1024, "GB": 1e9, "MB": 1e6}.get(m.group(2), 1)
                    size_b = int(float(m.group(1)) * mult)
            out.append({"hash": h.group(1).lower(), "name": htmllib.unescape(t.group(1)) if t else q,
                        "size": size_b, "seeders": int(se.group(1)) if se else 0,
                        "tracker": "Nyaa", "source_indexer": "nyaa"})
    except Exception as e:
        logger.warning(f"nyaa failed: {e}")
    return out


INDEXERS = {"apibay": idx_apibay, "therarbg": idx_therarbg, "eztv": idx_eztv, "nyaa": idx_nyaa}


async def idx_torrentgalaxy(http, imdb_id, media_type="movie", **kw):
    out = []
    cat = "TV" if media_type == "series" else "Movies"
    try:
        r = await http.get(f"https://torrentgalaxy.one/get-posts/keywords:{imdb_id}:category:{cat}/?format=json", timeout=15)
        for it in r.json().get("results", []):
            h = it.get("h")
            if not h:
                continue
            out.append({"hash": h.lower(), "name": it.get("n", ""),
                        "size": int(it.get("s", 0) or 0), "seeders": int(it.get("se", 0) or 0),
                        "tracker": "TGx", "source_indexer": "torrentgalaxy"})
    except Exception as e:
        logger.warning(f"torrentgalaxy failed: {e}")
    return out


def _title_query(title, year, season=None, episode=None):
    if not title:
        return None
    if season is not None and episode is not None:
        return f"{title} S{int(season):02d}E{int(episode):02d}"
    if year:
        return f"{title} {year}"
    return title


async def idx_limetorrents(http, imdb_id, title=None, year=None, season=None, episode=None, **kw):
    out = []
    q = _title_query(title, year, season, episode)
    if not q:
        return out
    try:
        r = await http.get(f"https://www.limetorrents.lol/searchrss/{quote(q)}/", timeout=15)
        for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
            enc = re.search(r"itorrents\.net/torrent/([A-Fa-f0-9]{40})", it)
            t = re.search(r"<title>([^<]+)</title>", it)
            sz = re.search(r"<size>(\d+)</size>", it)
            se = re.search(r"Seeds:\s*(\d+)", it)
            if not enc:
                continue
            out.append({"hash": enc.group(1).lower(), "name": htmllib.unescape(t.group(1)) if t else q,
                        "size": int(sz.group(1)) if sz else 0, "seeders": int(se.group(1)) if se else 0,
                        "tracker": "Lime", "source_indexer": "limetorrents"})
    except Exception as e:
        logger.warning(f"limetorrents failed: {e}")
    return out


async def idx_torrentdownloads(http, imdb_id, title=None, year=None, season=None, episode=None, **kw):
    out = []
    q = _title_query(title, year, season, episode)
    if not q:
        return out
    try:
        r = await http.get(f"https://www.torrentdownloads.pro/rss.xml?type=search&search={quote(q)}", timeout=15)
        for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
            h = re.search(r"<info_hash>([A-Fa-f0-9]{40})</info_hash>", it)
            t = re.search(r"<title>\s*([^<]+?)\s*</title>", it)
            sz = re.search(r"<size>(\d+)</size>", it)
            se = re.search(r"<seeders>(\d+)</seeders>", it)
            if not h:
                continue
            out.append({"hash": h.group(1).lower(), "name": htmllib.unescape(t.group(1)) if t else q,
                        "size": int(sz.group(1)) if sz else 0, "seeders": int(se.group(1)) if se else 0,
                        "tracker": "TD", "source_indexer": "torrentdownloads"})
    except Exception as e:
        logger.warning(f"torrentdownloads failed: {e}")
    return out


INDEXERS.update({"torrentgalaxy": idx_torrentgalaxy, "limetorrents": idx_limetorrents,
                 "torrentdownloads": idx_torrentdownloads})


async def gather_sources(imdb_id, media_type, season=None, episode=None, sources=None, title=None, year=None):
    sources = sources or DEFAULT_SOURCES
    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as http:
        tasks = []
        for sid in sources:
            fn = INDEXERS.get(sid)
            if not fn:
                continue
            meta = next((s for s in AVAILABLE_SOURCES if s["id"] == sid), None)
            if meta and media_type not in meta["types"]:
                continue
            tasks.append(fn(http, imdb_id, media_type=media_type, season=season, episode=episode, title=title, year=year))
        results = await asyncio.gather(*tasks, return_exceptions=True)
    merged = {}
    for res in results:
        if isinstance(res, Exception):
            continue
        for it in res:
            if it["hash"] not in merged or it["seeders"] > merged[it["hash"]]["seeders"]:
                merged[it["hash"]] = it
    return list(merged.values())


async def check_cached(hashes, key):
    if not hashes or not key:
        return set()
    cached = set()
    async with httpx.AsyncClient() as http:
        for i in range(0, len(hashes), 80):
            chunk = hashes[i:i + 80]
            params = [("hash", h) for h in chunk] + [("format", "list"), ("list_files", "false")]
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


async def build_sources(imdb_id, media_type, season=None, episode=None, sources=None, title=None, year=None):
    ck = ("src", imdb_id, media_type, season, episode, tuple(sorted(sources or [])), title, year)
    cached_res = cache_get(ck)
    key = await get_torbox_key()
    if cached_res is not None:
        items = cached_res
    else:
        items = await gather_sources(imdb_id, media_type, season, episode, sources, title, year)
        cache_set(ck, items, 900)
    tb_cached = await check_cached([i["hash"] for i in items], key)
    out = []
    for it in items:
        q = parse_quality(it["name"])
        out.append({**it, "size_h": human_size(it["size"]), "cached": it["hash"] in tb_cached,
                    "quality": q, "res_rank": res_rank(q["resolution"]),
                    "magnet": build_magnet(it["hash"], it["name"])})
    out.sort(key=lambda x: (x["cached"], x["res_rank"], x["seeders"]), reverse=True)
    return out


# ------------------------- TorBox actions -------------------------
async def torbox_add(magnet, key, name=None):
    async with httpx.AsyncClient() as http:
        form = {"magnet": magnet, "seed": "3", "allow_zip": "true"}
        if name:
            form["name"] = name
        r = await http.post(f"{TORBOX_API}/torrents/createtorrent", data=form, headers=tb_headers(key), timeout=30)
        return r.json()


async def torbox_torrent_files(torrent_id, key):
    async with httpx.AsyncClient() as http:
        try:
            r = await http.get(f"{TORBOX_API}/torrents/mylist", params={"id": torrent_id, "bypass_cache": "true"},
                              headers=tb_headers(key), timeout=20)
            data = r.json().get("data")
            if isinstance(data, list):
                data = data[0] if data else None
            return data
        except Exception as e:
            logger.warning(f"torrent files fetch failed: {e}")
            return None


def pick_file(files, season=None, episode=None):
    vids = [f for f in files if re.search(r"\.(mkv|mp4|avi|m4v|ts|mov)$", f.get("name", ""), re.I)]
    if not vids:
        vids = files
    if season is not None and episode is not None:
        pats = [re.compile(rf"s0*{int(season)}[\s._-]*e0*{int(episode)}", re.I),
                re.compile(rf"\b{int(season)}x0*{int(episode)}\b", re.I)]
        for f in vids:
            if any(p.search(f.get("name", "")) for p in pats):
                return f.get("id", 0)
    best = max(vids, key=lambda f: f.get("size", 0)) if vids else None
    return best.get("id", 0) if best else 0


async def resolve_stream(hash_, name, key, season=None, episode=None):
    add = await torbox_add(build_magnet(hash_, name or hash_), key, name)
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
                          params={"token": key, "torrent_id": tid, "file_id": file_id}, headers=tb_headers(key), timeout=30)
        j = r.json()
        if j.get("success"):
            return j.get("data")
    return None


# ------------------------- TMDB + enrichment -------------------------
async def tmdb_get(path, params=None):
    key = await get_tmdb_key()
    if not key:
        raise HTTPException(400, "TMDB API key not configured. Add it in Settings.")
    params = params or {}
    params["api_key"] = key
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TMDB_API}{path}", params=params, timeout=20)
        return r.json()


def map_tmdb_item(it):
    mt = it.get("media_type")
    if mt not in ("movie", "tv"):
        mt = "tv" if it.get("name") and not it.get("title") else "movie"
    title = it.get("title") or it.get("name")
    date = it.get("release_date") or it.get("first_air_date") or ""
    return {
        "id": it.get("id"), "media_type": "series" if mt == "tv" else "movie",
        "title": title, "year": (date or "")[:4], "overview": it.get("overview", ""),
        "poster": f"{TMDB_IMG}/w500{it['poster_path']}" if it.get("poster_path") else None,
        "backdrop": f"{TMDB_IMG}/original{it['backdrop_path']}" if it.get("backdrop_path") else None,
        "rating": round(it.get("vote_average", 0) or 0, 1),
        "popularity": it.get("popularity", 0) or 0,
        "votes": it.get("vote_count", 0) or 0,
    }


async def enrich_meta(m, keys):
    imdb_id = m.get("imdb_id")
    if not imdb_id:
        return
    tasks = {}
    if keys.get("omdb"):
        tasks["omdb"] = ("get", f"https://www.omdbapi.com/?apikey={keys['omdb']}&i={imdb_id}&tomatoes=true")
    if keys.get("fanart") and m.get("media_type") == "movie":
        tasks["fanart"] = ("get", f"https://webservice.fanart.tv/v3/movies/{imdb_id}?api_key={keys['fanart']}")
    if not tasks:
        if keys.get("rpdb"):
            m["poster"] = f"https://api.ratingposterdb.com/{keys['rpdb']}/imdb/poster-default/{imdb_id}.jpg?fallback=true"
        return
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*[http.get(u, timeout=12) for _, u in tasks.values()], return_exceptions=True)
    for (name, _), res in zip(tasks.values() if False else tasks.items(), results):
        pass
    idx = 0
    for name in tasks:
        res = results[idx]; idx += 1
        if isinstance(res, Exception):
            continue
        try:
            j = res.json()
        except Exception:
            continue
        if name == "omdb" and j.get("Response") == "True":
            ratings = {}
            for r in j.get("Ratings", []):
                ratings[r["Source"]] = r["Value"]
            m["ratings"] = {
                "imdb": j.get("imdbRating"),
                "rotten_tomatoes": ratings.get("Rotten Tomatoes"),
                "metacritic": ratings.get("Metacritic"),
            }
            if j.get("Rated"):
                m["rated"] = j.get("Rated")
        if name == "fanart":
            logos = j.get("hdmovielogo") or j.get("movielogo") or []
            en = [l for l in logos if l.get("lang") == "en"] or logos
            if en:
                m["logo"] = en[0].get("url")
    if keys.get("rpdb"):
        m["poster"] = f"https://api.ratingposterdb.com/{keys['rpdb']}/imdb/poster-default/{imdb_id}.jpg?fallback=true"


# ------------------------- MODELS -------------------------
class SettingsIn(BaseModel):
    torbox_api_key: Optional[str] = None
    tmdb_api_key: Optional[str] = None
    omdb_api_key: Optional[str] = None
    rpdb_api_key: Optional[str] = None
    fanart_api_key: Optional[str] = None
    thetvdb_api_key: Optional[str] = None
    paypal_client_id: Optional[str] = None
    paypal_secret: Optional[str] = None
    paypal_mode: Optional[str] = None
    sources: Optional[List[str]] = None
    email: Optional[str] = None


class OrderIn(BaseModel):
    amount: float
    email: Optional[str] = None


class CaptureIn(BaseModel):
    order_id: str
    email: str


class ResolveIn(BaseModel):
    hash: str
    name: str
    season: Optional[int] = None
    episode: Optional[int] = None


class AddIn(BaseModel):
    hash: str
    name: str


class TestKeyIn(BaseModel):
    service: str
    key: str


class BulkAddIn(BaseModel):
    items: List[AddIn]


class CacheSeasonIn(BaseModel):
    imdb_id: str
    season: int
    episodes: int
    title: Optional[str] = None


# ------------------------- ROUTES -------------------------
@api_router.get("/")
async def root():
    return {"message": "DMM API online"}


@api_router.get("/config")
async def config():
    doc = await get_config()
    keys = await get_keys()
    connected = False
    account = None
    if keys["torbox"]:
        cc = cache_get(("tbconn", keys["torbox"]))
        if cc is not None:
            connected, account = cc
        else:
            try:
                async with httpx.AsyncClient() as http:
                    r = await http.get(f"{TORBOX_API}/user/me", headers=tb_headers(keys["torbox"]), timeout=20)
                    j = r.json()
                    connected = bool(j.get("success"))
                    d = j.get("data") or {}
                    account = {"email": d.get("email"), "premium": d.get("plan") not in (0, None)}
                if connected:
                    cache_set(("tbconn", keys["torbox"]), (connected, account), 300)
                    cache_set(("tbconn_last", keys["torbox"]), (connected, account), 86400)
                else:
                    last = cache_get(("tbconn_last", keys["torbox"]))
                    if last:
                        connected, account = last
            except Exception:
                last = cache_get(("tbconn_last", keys["torbox"]))
                if last:
                    connected, account = last
                else:
                    connected = False
    return {
        "torbox_connected": connected,
        "torbox_account": account,
        "tmdb_configured": bool(keys["tmdb"]),
        "keys_set": {k: bool(keys[k]) for k in ["torbox", "tmdb", "omdb", "rpdb", "fanart", "thetvdb"]},
        "needs_onboarding": not (keys["tmdb"] and keys["torbox"]),
        "sources": doc.get("sources", DEFAULT_SOURCES),
        "available_sources": AVAILABLE_SOURCES,
    }


@api_router.post("/test-key")
async def test_key(body: TestKeyIn):
    s, k = body.service, body.key.strip()
    if not k:
        return {"ok": False, "message": "Empty key"}
    try:
        async with httpx.AsyncClient() as http:
            if s == "torbox":
                r = await http.get(f"{TORBOX_API}/user/me", headers=tb_headers(k), timeout=15)
                j = r.json()
                if j.get("success"):
                    return {"ok": True, "message": f"Connected: {(j.get('data') or {}).get('email', 'ok')}"}
                return {"ok": False, "message": "Invalid TorBox key"}
            if s == "tmdb":
                r = await http.get(f"{TMDB_API}/authentication", params={"api_key": k}, timeout=15)
                if r.status_code == 200 and r.json().get("success"):
                    return {"ok": True, "message": "TMDB key valid"}
                r2 = await http.get(f"{TMDB_API}/movie/550", params={"api_key": k}, timeout=15)
                return {"ok": r2.status_code == 200, "message": "TMDB key valid" if r2.status_code == 200 else "Invalid TMDB key"}
            if s == "omdb":
                j = (await http.get(f"https://www.omdbapi.com/?apikey={k}&i=tt1375666", timeout=12)).json()
                ok = j.get("Response") == "True"
                return {"ok": ok, "message": "OMDb valid" if ok else j.get("Error", "Invalid OMDb key")}
            if s == "rpdb":
                r = await http.get(f"https://api.ratingposterdb.com/{k}/imdb/poster-default/tt1375666.jpg", timeout=12)
                return {"ok": r.status_code == 200, "message": "RPDB valid" if r.status_code == 200 else "Invalid RPDB key"}
            if s == "fanart":
                r = await http.get(f"https://webservice.fanart.tv/v3/movies/tt1375666?api_key={k}", timeout=12)
                return {"ok": r.status_code == 200, "message": "Fanart valid" if r.status_code == 200 else "Invalid Fanart key"}
            if s == "thetvdb":
                r = await http.post("https://api4.thetvdb.com/v4/login", json={"apikey": k}, timeout=15)
                ok = r.status_code == 200 and (r.json().get("status") == "success")
                return {"ok": ok, "message": "TheTVDB key valid" if ok else "Invalid TheTVDB key"}
    except Exception as e:
        return {"ok": False, "message": str(e)[:80]}
    return {"ok": False, "message": "Unknown service"}


@api_router.post("/settings")
async def update_settings(body: SettingsIn):
    update = {}
    for f in ["torbox_api_key", "tmdb_api_key", "omdb_api_key", "rpdb_api_key", "fanart_api_key", "thetvdb_api_key"]:
        v = getattr(body, f)
        if v is not None:
            update[f] = v.strip()
    if body.sources is not None:
        update["sources"] = body.sources
    if update:
        await db.config.update_one({"_id": CONFIG_ID}, {"$set": update}, upsert=True)
        _CACHE.clear()
    return await config()


@api_router.get("/search")
async def search(q: str = Query(..., min_length=1), page: int = Query(1, ge=1)):
    if not await get_tmdb_key():
        return await cinemeta.search(q, page)
    data = await tmdb_get("/search/multi", {"query": q, "page": page, "include_adult": "false"})
    seen, items = set(), []
    for it in data.get("results", []):
        if it.get("media_type") not in ("movie", "tv"):
            continue
        m = map_tmdb_item(it)
        if not m["poster"] or m["id"] in seen:
            continue
        if m["votes"] < 3 and m["popularity"] < 2:
            continue
        seen.add(m["id"])
        items.append(m)
    items.sort(key=lambda x: x["popularity"], reverse=True)
    return {"results": items, "page": page, "total_pages": min(data.get("total_pages", 1), 500),
            "total_results": data.get("total_results", len(items))}


@api_router.get("/trending")
async def trending():
    data = await tmdb_get("/trending/all/week")
    items = [map_tmdb_item(it) for it in data.get("results", []) if it.get("media_type") in ("movie", "tv")]
    return {"results": [i for i in items if i["poster"]]}


@api_router.get("/discover/{media_type}")
async def discover(media_type: str, page: int = Query(1, ge=1)):
    if not await get_tmdb_key():
        key = ("cinemeta-catalogue", media_type)
        items = cache_get(key)
        if items is None:
            items = await cinemeta.catalogue(media_type)
            cache_set(key, items)
        return cinemeta.paginate(items, page)
    mt = "tv" if media_type == "series" else "movie"
    data = await tmdb_get(f"/{mt}/popular", {"page": page})
    items = []
    for it in data.get("results", []):
        it["media_type"] = mt
        m = map_tmdb_item(it)
        if m["poster"]:
            items.append(m)
    return {"results": items, "page": page, "total_pages": min(data.get("total_pages", 1), 500)}


async def cinemeta_detail(kind, imdb):
    key = ("cinemeta-detail", kind, imdb)
    data = cache_get(key)
    if data is None:
        data = await cinemeta.details(kind, imdb)
        cache_set(key, data, 3600)
    return data


@api_router.get("/meta/{media_type}/{tmdb_id}")
async def meta(media_type: str, tmdb_id: str):
    if str(tmdb_id).startswith("tt"):
        info, _ = await cinemeta_detail(media_type, tmdb_id)
        return info
    ck = ("meta", media_type, tmdb_id)
    hit = cache_get(ck)
    if hit is not None:
        return hit
    mt = "tv" if media_type == "series" else "movie"
    data = await tmdb_get(f"/{mt}/{tmdb_id}", {"append_to_response": "external_ids"})
    ext = data.get("external_ids", {})
    m = map_tmdb_item({**data, "media_type": mt})
    seasons = []
    if mt == "tv":
        for s in data.get("seasons", []):
            if s.get("season_number", 0) == 0:
                continue
            seasons.append({"season_number": s.get("season_number"), "name": s.get("name"),
                            "episode_count": s.get("episode_count")})
    m.update({
        "imdb_id": ext.get("imdb_id"),
        "genres": [g["name"] for g in data.get("genres", [])],
        "runtime": data.get("runtime") or (data.get("episode_run_time") or [None])[0],
        "seasons": seasons, "tagline": data.get("tagline"),
    })
    try:
        await enrich_meta(m, await get_keys())
    except Exception as e:
        logger.warning(f"enrich failed: {e}")
    cache_set(ck, m, 3600)
    return m


@api_router.get("/season/{tmdb_id}/{season_number}")
async def season_eps(tmdb_id: str, season_number: int):
    if str(tmdb_id).startswith("tt"):
        _, videos = await cinemeta_detail("series", tmdb_id)
        return {"episodes": [{"episode_number": v["episode"], "name": v.get("title") or v.get("name") or f"Episode {v['episode']}"}
                             for v in sorted(videos, key=lambda v: v["episode"]) if v["season"] == season_number]}
    data = await tmdb_get(f"/tv/{tmdb_id}/season/{season_number}")
    eps = [{"episode_number": e.get("episode_number"), "name": e.get("name"),
            "overview": e.get("overview", ""),
            "still": f"{TMDB_IMG}/w300{e['still_path']}" if e.get("still_path") else None,
            "air_date": e.get("air_date")} for e in data.get("episodes", [])]
    return {"episodes": eps}


@api_router.get("/sources/{imdb_id}")
async def sources(imdb_id: str, media_type: str = "movie", season: Optional[int] = None,
                  episode: Optional[int] = None, title: Optional[str] = None, year: Optional[str] = None):
    doc = await get_config()
    out = await build_sources(imdb_id, media_type, season, episode, doc.get("sources", DEFAULT_SOURCES), title, year)
    return {"sources": out, "total": len(out), "cached_count": sum(1 for o in out if o["cached"])}


@api_router.post("/torbox/add")
async def add_to_torbox(body: AddIn):
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    return await torbox_add(build_magnet(body.hash, body.name), key, body.name)


@api_router.post("/torbox/bulk-add")
async def bulk_add(body: BulkAddIn):
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    results = []
    for it in body.items[:40]:
        try:
            r = await torbox_add(build_magnet(it.hash, it.name), key, it.name)
            results.append({"hash": it.hash, "success": bool(r.get("success")), "detail": r.get("detail")})
        except Exception as e:
            results.append({"hash": it.hash, "success": False, "detail": str(e)})
        await asyncio.sleep(0.6)
    added = sum(1 for r in results if r["success"])
    return {"added": added, "total": len(results), "results": results}


@api_router.post("/torbox/cache-season")
async def cache_season(body: CacheSeasonIn):
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    doc = await get_config()
    srcs = doc.get("sources", DEFAULT_SOURCES)
    picks = []
    for ep in range(1, min(body.episodes, 30) + 1):
        items = await build_sources(body.imdb_id, "series", body.season, ep, srcs, body.title)
        if items:
            picks.append(items[0])  # already sorted cached+quality first
    added = 0
    for p in picks:
        try:
            r = await torbox_add(p["magnet"], key, p["name"])
            if r.get("success"):
                added += 1
        except Exception:
            pass
        await asyncio.sleep(0.6)
    return {"added": added, "episodes_found": len(picks), "requested": min(body.episodes, 30)}


@api_router.post("/torbox/resolve")
async def resolve(body: ResolveIn):
    key = await get_torbox_key()
    if not key:
        raise HTTPException(400, "No TorBox API key configured")
    url = await resolve_stream(body.hash, body.name, key, body.season, body.episode)
    if not url:
        raise HTTPException(502, "Could not resolve stream from TorBox")
    return {"url": url}


_poster_sem = asyncio.Semaphore(20)

async def match_poster(name):
    ck = ("poster", (name or "")[:70])
    hit = cache_get(ck)
    if hit is not None:
        return hit
    clean = re.sub(r"[._]", " ", name or "")
    clean = re.split(r"\b(19|20)\d{2}\b|\b(1080p|720p|2160p|480p|s\d{1,2}|complete|season)\b", clean, flags=re.I)[0].strip()
    poster = None
    try:
        async with _poster_sem:
            d = await tmdb_get("/search/multi", {"query": clean[:60]})
        for c in d.get("results", []):
            if c.get("media_type") not in ("movie", "tv"):
                continue
            m = map_tmdb_item(c)
            if m["poster"]:
                poster = m["poster"]
                break
    except Exception:
        pass
    cache_set(ck, poster, 86400)
    return poster


async def match_tmdb(name):
    ck = ("tmatch", (name or "")[:70])
    hit = cache_get(ck)
    if hit is not None:
        return hit
    clean = re.sub(r"[._]", " ", name or "")
    clean = re.split(r"\b(19|20)\d{2}\b|\b(1080p|720p|2160p|480p|s\d{1,2}|complete|season)\b", clean, flags=re.I)[0].strip()
    res = None
    try:
        async with _poster_sem:
            d = await tmdb_get("/search/multi", {"query": clean[:60]})
        for c in d.get("results", []):
            if c.get("media_type") not in ("movie", "tv"):
                continue
            m = map_tmdb_item(c)
            if m["poster"]:
                res = m
                break
    except Exception:
        pass
    cache_set(ck, res, 86400)
    return res


@api_router.post("/reset")
async def reset_config():
    await db.config.update_one({"_id": CONFIG_ID}, {"$set": {k: "" for k in
        ["torbox_api_key", "tmdb_api_key", "omdb_api_key", "rpdb_api_key", "fanart_api_key", "thetvdb_api_key"]}}, upsert=True)
    _CACHE.clear()
    return {"ok": True}


@api_router.get("/warm/{media_type}/{tmdb_id}")
async def warm(media_type: str, tmdb_id: str):
    try:
        m = await meta(media_type, tmdb_id)
    except Exception:
        return {"ok": False}
    imdb = m.get("imdb_id")
    if imdb:
        doc = await get_config()
        srcs = doc.get("sources", DEFAULT_SOURCES)

        async def _bg():
            try:
                if media_type == "series":
                    await build_sources(imdb, "series", 1, 1, srcs, m.get("title"), m.get("year"))
                else:
                    await build_sources(imdb, "movie", None, None, srcs, m.get("title"), m.get("year"))
            except Exception:
                pass
        asyncio.create_task(_bg())
    return {"ok": True, "imdb_id": imdb}


ALLOWED_STREAM_HOSTS = ("tb-cdn.io", "torbox.app", "torbox.st")


def _host_allowed(host: str) -> bool:
    host = (host or "").lower()
    return any(host == a or host.endswith("." + a) for a in ALLOWED_STREAM_HOSTS)


async def probe_vcodec(src):
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=codec_name", "-of", "default=nw=1:nk=1", src,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=25)
        return (out.decode().strip() or "").lower()
    except Exception:
        return ""


@api_router.get("/stream/transcode")
async def transcode(src: str, force: int = 0):
    from urllib.parse import urlparse
    host = urlparse(src).hostname or ""
    if not _host_allowed(host):
        raise HTTPException(400, "Host not allowed")
    vcodec = await probe_vcodec(src)
    if vcodec in ("h264", "avc1") and not force:
        vargs = ["-c:v", "copy"]
    else:
        vargs = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                 "-vf", "scale=-2:720", "-maxrate", "6M", "-bufsize", "12M"]
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src,
           "-map", "0:v:0", "-map", "0:a:0?", *vargs, "-c:a", "aac", "-b:a", "192k", "-ac", "2",
           "-movflags", "frag_keyframe+empty_moov+default_base_moof", "-f", "mp4", "pipe:1"]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)

    async def gen():
        try:
            while True:
                chunk = await proc.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            if proc.returncode is None:
                try:
                    proc.kill()
                except Exception:
                    pass
    return StreamingResponse(gen(), media_type="video/mp4",
                             headers={"Cache-Control": "no-store", "Content-Disposition": "inline"})


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
        out.append({"id": it.get("id"), "name": it.get("name"), "hash": it.get("hash"),
                    "size": it.get("size"), "size_h": human_size(it.get("size")),
                    "state": it.get("download_state"), "progress": round((it.get("progress") or 0) * 100),
                    "cached": it.get("download_state") == "cached" or (it.get("progress") or 0) >= 1,
                    "download_present": it.get("download_present"), "created_at": it.get("created_at"),
                    "files": [{"id": f.get("id"), "name": f.get("name"), "size": f.get("size"),
                               "size_h": human_size(f.get("size"))} for f in (it.get("files") or [])]})
    try:
        if await get_tmdb_key():
            posters = await asyncio.gather(*[match_poster(o["name"]) for o in out], return_exceptions=True)
            for o, p in zip(out, posters):
                o["poster"] = p if not isinstance(p, Exception) else None
    except Exception as e:
        logger.warning(f"library poster enrich failed: {e}")
    return {"library": out, "total": len(out)}


@api_router.delete("/library/{torrent_id}")
async def delete_lib(torrent_id: int):
    key = await get_torbox_key()
    async with httpx.AsyncClient() as http:
        r = await http.post(f"{TORBOX_API}/torrents/controltorrent",
                          json={"torrent_id": torrent_id, "operation": "delete"}, headers=tb_headers(key), timeout=20)
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
    return f"{proto}://{host}" if host else str(request.base_url).rstrip("/")


def decode_config(cfg):
    try:
        pad = cfg + "=" * (-len(cfg) % 4)
        return json.loads(base64.urlsafe_b64decode(pad).decode())
    except Exception:
        return {}


@api_router.post("/stremio/manifest-url")
async def stremio_manifest_url(body: SettingsIn, request: Request):
    keys = await get_keys()
    key = (body.torbox_api_key or "").strip() or keys["torbox"]
    srcs = body.sources or keys["sources"]
    cfg = {"k": key, "s": srcs}
    enc = base64.urlsafe_b64encode(json.dumps(cfg).encode()).decode().rstrip("=")
    base = public_base(request)
    url = f"{base}/api/stremio/{enc}/manifest.json"
    return {"config": enc, "manifest_url": url,
            "install_url": url.replace("https://", "stremio://").replace("http://", "stremio://")}


def _manifest(cfg):
    return {
        "id": "com.dmm.torbox", "version": "1.1.0", "name": "DMM - Debrid Media Manager",
        "description": "TorBox cached streams & your library, powered by Debrid Media Manager.",
        "logo": "https://static.prod-images.emergentagent.com/jobs/4c3cfdd9-909a-42ca-a0a0-9a803d3f7427/images/3432b210e7a4ebbaf55fd5f9cd44b4b5a753aa7f65c9c60b34bdfef7085e39aa.jpeg",
        "resources": ["stream", "catalog", "meta"], "types": ["movie", "series"],
        "idPrefixes": ["tt", "dmm:"],
        "catalogs": [{"type": "movie", "id": "dmm_library_movie", "name": "DMM TorBox Library"},
                     {"type": "series", "id": "dmm_library_series", "name": "DMM TorBox Library"}],
        "behaviorHints": {"configurable": True, "configurationRequired": False},
    }


@api_router.get("/stremio/{cfg}/manifest.json")
async def stremio_manifest(cfg: str):
    return JSONResponse(_manifest(cfg))


@api_router.get("/stremio/{cfg}/stream/{type}/{video_id}.json")
async def stremio_stream(cfg: str, type: str, video_id: str, request: Request):
    conf = decode_config(cfg)
    key = conf.get("k", "")
    srcs = conf.get("s") or DEFAULT_SOURCES
    vid = video_id.replace(".json", "")
    parts = vid.split(":")
    imdb_id = parts[0]
    season = int(parts[1]) if len(parts) > 1 else None
    episode = int(parts[2]) if len(parts) > 2 else None
    media_type = "series" if type == "series" else "movie"
    items = await gather_sources(imdb_id, media_type, season, episode, srcs)
    tb_cached = await check_cached([i["hash"] for i in items], key)
    for i in items:
        i["cached"] = i["hash"].lower() in tb_cached
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
        streams.append({"name": f"DMM TorBox\n{q['resolution'] or 'SD'}",
                        "title": f"{badge} | {tags or 'Unknown'}\n{it['name']}\n💾 {human_size(it['size'])} | 👤 {it['seeders']} | {it['tracker']}",
                        "url": url, "behaviorHints": {"bingeGroup": f"dmm-{q['resolution']}", "notWebReady": True}})
    return JSONResponse({"streams": streams})


@api_router.get("/stremio/{cfg}/resolve/{hash_}/{season}/{episode}/{name}")
async def stremio_resolve(cfg: str, hash_: str, season: str, episode: str, name: str):
    conf = decode_config(cfg)
    key = conf.get("k", "")
    s = int(season) if season not in ("-", "") else None
    e = int(episode) if episode not in ("-", "") else None
    url = await resolve_stream(hash_, name, key, s, e)
    if not url:
        raise HTTPException(502, "Could not resolve")
    return RedirectResponse(url)


@api_router.get("/stremio/{cfg}/catalog/{type}/{id}.json")
async def stremio_catalog(cfg: str, type: str, id: str, request: Request):
    conf = decode_config(cfg)
    key = conf.get("k", "")
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/mylist", params={"bypass_cache": "true"},
                          headers=tb_headers(key), timeout=30)
        data = r.json().get("data") or []
    LOGO = "https://static.prod-images.emergentagent.com/jobs/4c3cfdd9-909a-42ca-a0a0-9a803d3f7427/images/3432b210e7a4ebbaf55fd5f9cd44b4b5a753aa7f65c9c60b34bdfef7085e39aa.jpeg"
    filtered = []
    for it in data:
        name = it.get("name", "")
        is_series = bool(re.search(r"s\d{1,2}e\d{1,2}|season|complete", name, re.I))
        if ("series" if is_series else "movie") == type:
            filtered.append(it)
    matches = []
    if await get_tmdb_key():
        matches = await asyncio.gather(*[match_tmdb(it.get("name", "")) for it in filtered], return_exceptions=True)
    metas = []
    for i, it in enumerate(filtered):
        name = it.get("name", "")
        q = parse_quality(name)
        m = matches[i] if i < len(matches) and not isinstance(matches[i], Exception) else None
        metas.append({
            "id": f"dmm:{it.get('id')}", "type": type,
            "name": (m or {}).get("title") or re.sub(r"[._]", " ", name)[:80],
            "poster": (m or {}).get("poster") or LOGO,
            "posterShape": "poster",
            "background": (m or {}).get("backdrop"),
            "releaseInfo": (m or {}).get("year"),
            "description": (((m or {}).get("overview") or "") + f"\n\n📁 {name}\n{q['resolution'] or ''} {q['source'] or ''} • {human_size(it.get('size'))}").strip()[:800],
        })
    return JSONResponse({"metas": metas})


@api_router.get("/stremio/{cfg}/meta/{type}/{id}.json")
async def stremio_meta(cfg: str, type: str, id: str):
    conf = decode_config(cfg)
    key = conf.get("k", "")
    idv = id.replace(".json", "")
    if not idv.startswith("dmm:"):
        return JSONResponse({"meta": {}})
    tid = int(idv.split(":")[1])
    info = await torbox_torrent_files(tid, key)
    if not info:
        return JSONResponse({"meta": {}})
    files = [f for f in (info.get("files") or []) if re.search(r"\.(mkv|mp4|avi|m4v|ts)$", f.get("name", ""), re.I)]
    videos = [{"id": f"dmm:{tid}:{f.get('id')}", "title": os.path.basename(f.get("name", "")),
               "released": info.get("created_at")} for f in files]
    raw_name = info.get("name", "")
    m = await match_tmdb(raw_name) if await get_tmdb_key() else None
    LOGO = "https://static.prod-images.emergentagent.com/jobs/4c3cfdd9-909a-42ca-a0a0-9a803d3f7427/images/3432b210e7a4ebbaf55fd5f9cd44b4b5a753aa7f65c9c60b34bdfef7085e39aa.jpeg"
    meta = {"id": idv, "type": type,
            "name": (m or {}).get("title") or re.sub(r"[._]", " ", raw_name)[:80],
            "poster": (m or {}).get("poster") or LOGO, "posterShape": "poster",
            "background": (m or {}).get("backdrop"),
            "releaseInfo": (m or {}).get("year"),
            "description": (((m or {}).get("overview") or "") + f"\n\n📁 {raw_name}\nTorBox • {human_size(info.get('size'))}").strip()}
    if type == "series" and videos:
        meta["videos"] = videos
    return JSONResponse({"meta": meta})


@api_router.get("/stremio/{cfg}/stream/dmm/{tid}/{fid}.json")
async def stremio_lib_stream(cfg: str, tid: int, fid: int, request: Request):
    base = public_base(request)
    return JSONResponse({"streams": [{"name": "DMM TorBox", "title": "Play from Library",
                                      "url": f"{base}/api/stremio/{cfg}/libresolve/{tid}/{fid}"}]})


@api_router.get("/stremio/{cfg}/libresolve/{tid}/{fid}")
async def stremio_lib_resolve(cfg: str, tid: int, fid: int):
    conf = decode_config(cfg)
    key = conf.get("k", "")
    async with httpx.AsyncClient() as http:
        r = await http.get(f"{TORBOX_API}/torrents/requestdl",
                          params={"token": key, "torrent_id": tid, "file_id": fid}, headers=tb_headers(key), timeout=30)
        j = r.json()
    if j.get("success"):
        return RedirectResponse(j.get("data"))
    raise HTTPException(502, "Could not resolve")


app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True,
                   allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def _startup_warm():
    async def bg():
        await asyncio.sleep(3)
        try:
            keys = await get_keys()
            if keys["tmdb"]:
                await trending()
            if keys["torbox"]:
                await library()
        except Exception as e:
            logger.warning(f"startup warm failed: {e}")
    asyncio.create_task(bg())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
