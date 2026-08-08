"""Backend API tests for DMM (Debrid Media Manager) — TorBox + TMDB + Stremio."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback from frontend/.env parsing
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

API = f"{BASE_URL}/api"
CACHED_HASH = "32415815a0b4621400688f0bf2966d7fd3435d93"
CACHED_NAME = "Tomorrowland"
MOVIE_IMDB = "tt1964418"
MOVIE_TMDB = 158852
SERIES_TMDB = 1396  # Breaking Bad


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------- Config ----------
def test_config(s):
    r = s.get(f"{API}/config", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("torbox_connected") is True
    assert "available_sources" in d and isinstance(d["available_sources"], list)
    assert "sources" in d
    print("account_email:", d.get("account_email"))


# ---------- TMDB ----------
def test_search(s):
    r = s.get(f"{API}/search", params={"q": "tomorrowland"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "results" in d and len(d["results"]) > 0
    item = d["results"][0]
    for k in ("title", "media_type", "id"):
        assert k in item


def test_trending(s):
    r = s.get(f"{API}/trending", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "results" in d and len(d["results"]) > 0
    assert any(item.get("backdrop_path") or item.get("backdrop") for item in d["results"])


def test_discover_movie(s):
    r = s.get(f"{API}/discover/movie", timeout=30)
    assert r.status_code == 200
    assert len(r.json().get("results", [])) > 0


def test_discover_series(s):
    r = s.get(f"{API}/discover/series", timeout=30)
    assert r.status_code == 200
    assert len(r.json().get("results", [])) > 0


def test_meta_movie(s):
    r = s.get(f"{API}/meta/movie/{MOVIE_TMDB}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("imdb_id") == MOVIE_IMDB
    assert "genres" in d and "runtime" in d


def test_meta_series(s):
    r = s.get(f"{API}/meta/series/{SERIES_TMDB}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("imdb_id")
    assert isinstance(d.get("seasons"), list) and len(d["seasons"]) > 0


def test_season(s):
    r = s.get(f"{API}/season/{SERIES_TMDB}/1", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d.get("episodes"), list) and len(d["episodes"]) > 0


# ---------- Sources ----------
def test_sources_movie(s):
    r = s.get(f"{API}/sources/{MOVIE_IMDB}", params={"media_type": "movie"}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    srcs = d.get("sources", d) if isinstance(d, dict) else d
    if isinstance(d, dict) and "sources" in d:
        srcs = d["sources"]
    assert isinstance(srcs, list) and len(srcs) > 0
    cached = [x for x in srcs if x.get("cached")]
    assert len(cached) >= 1, "expected at least 1 cached source"
    it = srcs[0]
    for k in ("hash", "name", "size_h", "cached", "quality", "seeders", "magnet"):
        assert k in it, f"missing key {k}"
    q = it["quality"]
    assert set(["resolution", "source", "codec"]).issubset(q.keys())
    # Sort check — cached first
    assert srcs[0]["cached"] is True
    print("total sources:", len(srcs), "cached:", len(cached))


def test_sources_series(s):
    # Breaking Bad imdb: tt0903747
    r = s.get(f"{API}/sources/tt0903747",
              params={"media_type": "series", "season": 1, "episode": 1}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    srcs = d["sources"] if isinstance(d, dict) and "sources" in d else d
    assert isinstance(srcs, list)
    # Series may or may not have results but must be a list
    print("series sources:", len(srcs))


# ---------- TorBox ----------
def test_torbox_add(s):
    r = s.post(f"{API}/torbox/add",
               json={"hash": CACHED_HASH, "name": CACHED_NAME}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("success") is True, d


def test_torbox_resolve(s):
    r = s.post(f"{API}/torbox/resolve",
               json={"hash": CACHED_HASH, "name": CACHED_NAME}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    url = d.get("url") or d.get("stream_url") or d.get("download_url")
    assert url and url.startswith("http"), f"no playable url: {d}"
    print("resolved url host:", url.split("/")[2] if "//" in url else url)


def test_library(s):
    r = s.get(f"{API}/library", timeout=30)
    assert r.status_code == 200
    d = r.json()
    lib = d.get("library", d) if isinstance(d, dict) else d
    if isinstance(d, dict) and "library" in d:
        lib = d["library"]
    assert isinstance(lib, list)
    if lib:
        it = lib[0]
        for k in ("id", "name", "size_h", "state"):
            assert k in it, f"lib item missing {k}"


# ---------- Stremio ----------
@pytest.fixture(scope="session")
def stremio_config(s):
    r = s.post(f"{API}/stremio/manifest-url", json={}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "config" in d and "manifest_url" in d and "install_url" in d
    return d["config"]


def test_stremio_manifest_url(stremio_config):
    assert stremio_config


def test_stremio_manifest(s, stremio_config):
    r = s.get(f"{API}/stremio/{stremio_config}/manifest.json", timeout=30)
    assert r.status_code == 200
    m = r.json()
    assert m.get("id") == "com.dmm.torbox"
    assert set(["stream", "catalog", "meta"]).issubset(set(m.get("resources", [])))
    assert set(["movie", "series"]).issubset(set(m.get("types", [])))


def test_stremio_stream(s, stremio_config):
    r = s.get(f"{API}/stremio/{stremio_config}/stream/movie/{MOVIE_IMDB}.json", timeout=60)
    assert r.status_code == 200
    d = r.json()
    streams = d.get("streams", [])
    assert isinstance(streams, list)
    if streams:
        st = streams[0]
        for k in ("name", "title", "url"):
            assert k in st


def test_stremio_catalog(s, stremio_config):
    r = s.get(f"{API}/stremio/{stremio_config}/catalog/movie/dmm_library_movie.json", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "metas" in d and isinstance(d["metas"], list)
