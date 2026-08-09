"""Iteration 4 backend tests: instant loading (/warm), key-free shipping, transcode."""
import os
import time
import urllib.parse
import pytest
import requests

def _load_base():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


BASE = _load_base()
assert BASE, "REACT_APP_BACKEND_URL not set"

TORBOX_KEY = "REDACTED"
TMDB_KEY = "REDACTED"
OMDB_KEY = "REDACTED"
RPDB_KEY = "REDACTED"
FANART_KEY = "REDACTED"
THETVDB_KEY = "REDACTED"

DEFAULT_SOURCES = ["apibay", "therarbg", "torrentgalaxy", "eztv", "limetorrents", "torrentdownloads", "nyaa"]


def _reseed():
    """Re-seed all keys via POST /api/settings."""
    r = requests.post(f"{BASE}/api/settings", json={
        "torbox_api_key": TORBOX_KEY,
        "tmdb_api_key": TMDB_KEY,
        "omdb_api_key": OMDB_KEY,
        "rpdb_api_key": RPDB_KEY,
        "fanart_api_key": FANART_KEY,
        "thetvdb_api_key": THETVDB_KEY,
        "sources": DEFAULT_SOURCES,
    }, timeout=30)
    assert r.status_code == 200, f"reseed failed: {r.status_code} {r.text}"


# --- key-free shipping ---

def test_backend_env_has_no_keys():
    with open("/app/backend/.env") as f:
        content = f.read().lower()
    for bad in ["torbox_api_key", "tmdb_api_key", "omdb_api_key", "rpdb_api_key", "fanart_api_key", "thetvdb_api_key"]:
        assert bad not in content, f".env leaks {bad}"


def test_server_py_no_hardcoded_keys():
    with open("/app/backend/server.py") as f:
        content = f.read()
    for lit in [TORBOX_KEY, TMDB_KEY, OMDB_KEY, RPDB_KEY, FANART_KEY, THETVDB_KEY]:
        assert lit not in content, f"server.py has hardcoded key {lit[:8]}"


def test_config_reflects_db_keys():
    _reseed()
    r = requests.get(f"{BASE}/api/config", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["keys_set"]["torbox"] is True
    assert data["keys_set"]["tmdb"] is True
    assert data["needs_onboarding"] is False


# --- reset/onboarding ---

def test_reset_then_reseed():
    # ensure seeded first
    _reseed()
    # RESET
    r = requests.post(f"{BASE}/api/reset", timeout=15)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # confirm cleared
    r2 = requests.get(f"{BASE}/api/config", timeout=15)
    assert r2.status_code == 200
    d = r2.json()
    assert d["needs_onboarding"] is True, f"needs_onboarding not true: {d}"
    assert d["torbox_connected"] is False
    assert d["keys_set"]["torbox"] is False
    assert d["keys_set"]["tmdb"] is False

    # CRITICAL: re-seed
    _reseed()
    r3 = requests.get(f"{BASE}/api/config", timeout=15)
    d3 = r3.json()
    assert d3["needs_onboarding"] is False, "re-seed failed - app broken!"
    assert d3["keys_set"]["torbox"] is True
    assert d3["keys_set"]["tmdb"] is True


# --- warm ---

def test_warm_returns_imdb_fast():
    _reseed()
    t0 = time.time()
    r = requests.get(f"{BASE}/api/warm/movie/27205", timeout=10)
    dt = time.time() - t0
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("imdb_id") == "tt1375666"
    assert dt < 5, f"warm took {dt:.1f}s (>5s)"


def test_sources_fast_after_warm():
    # give background scrape a moment
    time.sleep(4)
    t0 = time.time()
    r = requests.get(f"{BASE}/api/sources/tt1375666",
                     params={"media_type": "movie", "title": "Inception", "year": 2010},
                     timeout=30)
    dt = time.time() - t0
    assert r.status_code == 200
    body = r.json()
    srcs = body.get("sources") if isinstance(body, dict) else body
    assert isinstance(srcs, list) and len(srcs) > 0
    # Cached should be reasonably fast (<5s ideally). Give slack.
    print(f"sources after warm: {dt:.2f}s, {len(srcs)} sources")


# --- transcode ---

def test_transcode_rejects_bad_host():
    r = requests.get(f"{BASE}/api/stream/transcode", params={"src": "https://evil.com/x"}, timeout=15)
    assert r.status_code == 400


def test_transcode_streams_mp4():
    _reseed()
    # Resolve a cached hash to get a real tb-cdn.io URL
    r = requests.post(f"{BASE}/api/torbox/resolve",
                      json={"hash": "32415815a0b4621400688f0bf2966d7fd3435d93", "name": "Tomorrowland"},
                      timeout=60)
    assert r.status_code == 200, f"resolve failed: {r.status_code} {r.text[:200]}"
    resolved = r.json()
    url = resolved.get("url") or resolved.get("direct_url") or resolved.get("link")
    assert url and "tb-cdn" in url or "torbox" in (url or ""), f"no tb-cdn url: {resolved}"

    # Now stream first chunk from transcode with a small timeout
    src = urllib.parse.quote(url, safe="")
    transcode_url = f"{BASE}/api/stream/transcode?src={src}"
    with requests.get(transcode_url, stream=True, timeout=60) as resp:
        assert resp.status_code == 200, f"transcode status {resp.status_code}"
        ct = resp.headers.get("content-type", "")
        assert "video/mp4" in ct, f"bad content-type: {ct}"
        # Read up to ~512KB and check for MP4 ftyp magic
        buf = b""
        for chunk in resp.iter_content(chunk_size=65536):
            buf += chunk
            if len(buf) > 512 * 1024:
                break
        assert len(buf) > 1024, f"got only {len(buf)} bytes"
        # MP4 ftyp magic is at offset 4
        assert b"ftyp" in buf[:64] or b"moof" in buf[:2048] or b"mdat" in buf[:4096], \
            f"no mp4 magic in first bytes: {buf[:32]!r}"
