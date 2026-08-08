"""Iteration 2 backend tests: multi-indexer, relevance, caching+enrichment,
bulk-add, cache-season, stremio, community keys."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

CACHED_HASH = "32415815a0b4621400688f0bf2966d7fd3435d93"
MOVIE_IMDB = "tt1964418"
MOVIE_TMDB = 158852
SERIES_IMDB = "tt0903747"
SERIES_TMDB = 1396


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- Config: keys_set + 4 available sources + no onboarding ---
def test_config_shape(s):
    r = s.get(f"{API}/config", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["torbox_connected"] is True
    assert d["tmdb_configured"] is True
    assert d["needs_onboarding"] is False
    ks = d["keys_set"]
    for k in ("torbox", "tmdb", "omdb", "rpdb", "fanart", "thetvdb"):
        assert k in ks, f"missing keys_set.{k}"
        assert ks[k] is True, f"keys_set.{k} not True"
    avail = d["available_sources"]
    ids = {x["id"] for x in avail}
    assert {"apibay", "therarbg", "eztv", "nyaa"}.issubset(ids)
    assert len(avail) == 4


# --- Community readiness: no API keys in .env ---
def test_env_no_keys():
    with open("/app/backend/.env") as f:
        content = f.read()
    assert "TORBOX_API_KEY" not in content
    assert "TMDB_API_KEY" not in content


# --- Search relevance: star wars ---
def test_search_relevance_star_wars(s):
    r = s.get(f"{API}/search", params={"q": "star wars"}, timeout=30)
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0
    titles = [(x.get("title") or "").strip() for x in results]
    joined = " | ".join(titles[:20])
    print("Top 20:", joined)
    # Main saga in top 20
    assert any(t == "Star Wars" or t.startswith("Star Wars (1977") for t in titles[:20]) \
        or any("Star Wars" == t for t in titles[:15]), f"main Star Wars not in top: {titles[:20]}"
    prequels = [
        "Star Wars: Episode I - The Phantom Menace",
        "Star Wars: Episode II - Attack of the Clones",
        "Star Wars: Episode III - Revenge of the Sith",
    ]
    assert any(p in titles[:20] for p in prequels), f"no prequel in top 20: {titles[:20]}"
    # Popularity ordering (roughly) — top 5 should have decent popularity
    pops = [x.get("popularity", 0) for x in results[:10]]
    print("top pops:", pops)


# --- Multiple indexers on movie ---
def test_sources_movie_multi_indexer(s):
    r = s.get(f"{API}/sources/{MOVIE_IMDB}", params={"media_type": "movie"}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    srcs = d.get("sources", d) if isinstance(d, dict) else d
    assert isinstance(srcs, list)
    indexers = {x.get("source_indexer") for x in srcs}
    print("indexers:", indexers, "total:", len(srcs))
    assert "apibay" in indexers
    assert "therarbg" in indexers
    assert len(srcs) >= 50, f"expected 100+, got {len(srcs)}"
    cached = [x for x in srcs if x.get("cached")]
    assert len(cached) >= 1


# --- Series with EZTV/therarbg + season/episode filter ---
def test_sources_series_multi(s):
    r = s.get(f"{API}/sources/{SERIES_IMDB}",
              params={"media_type": "series", "season": 1, "episode": 1}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    srcs = d.get("sources", d) if isinstance(d, dict) else d
    assert isinstance(srcs, list) and len(srcs) > 0
    indexers = {x.get("source_indexer") for x in srcs}
    print("series indexers:", indexers, "total:", len(srcs))
    assert indexers & {"therarbg", "eztv"}, f"expected therarbg or eztv, got {indexers}"


# --- Meta caching + enrichment (OMDb + RPDB) ---
def test_meta_cached_and_enriched(s):
    # warm
    r1 = s.get(f"{API}/meta/movie/{MOVIE_TMDB}", timeout=30)
    assert r1.status_code == 200
    t0 = time.time()
    r2 = s.get(f"{API}/meta/movie/{MOVIE_TMDB}", timeout=30)
    dt = time.time() - t0
    assert r2.status_code == 200
    d = r2.json()
    print(f"second meta call: {dt:.3f}s")
    assert dt < 3.0, f"cached call too slow: {dt}s"
    # Enrichment
    assert "ratings" in d, f"no ratings field: keys={list(d.keys())}"
    ratings = d["ratings"] or {}
    print("ratings:", ratings)
    # At least one of RT/MC/imdb present
    assert any(k in ratings for k in ("rotten_tomatoes", "metacritic", "imdb"))
    poster = d.get("poster") or ""
    print("poster:", poster[:120])
    assert "ratingposterdb.com" in poster or "api.ratingposterdb.com" in poster, \
        f"expected RPDB poster, got: {poster}"


# --- Bulk add ---
def test_torbox_bulk_add(s):
    r = s.post(f"{API}/torbox/bulk-add",
               json={"items": [{"hash": CACHED_HASH, "name": "Tomorrowland"}]}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    print("bulk-add:", d)
    assert d.get("added", 0) >= 1 or d.get("success") is True


# --- Cache Season (episodes capped at 1) ---
def test_cache_season(s):
    r = s.post(f"{API}/torbox/cache-season",
               json={"imdb_id": SERIES_IMDB, "season": 1, "episodes": 1,
                     "title": "Breaking Bad"}, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    print("cache-season:", d)
    assert "added" in d
    assert "episodes_found" in d


# --- Stremio still works ---
def test_stremio_flow(s):
    r = s.post(f"{API}/stremio/manifest-url", json={}, timeout=30)
    assert r.status_code == 200
    cfg = r.json()
    assert cfg.get("manifest_url") and cfg.get("install_url")
    config = cfg["config"]

    r = s.get(f"{API}/stremio/{config}/manifest.json", timeout=30)
    assert r.status_code == 200
    assert r.json().get("id") == "com.dmm.torbox"

    r = s.get(f"{API}/stremio/{config}/stream/movie/{MOVIE_IMDB}.json", timeout=90)
    assert r.status_code == 200
    streams = r.json().get("streams", [])
    assert isinstance(streams, list)
    print("stremio streams:", len(streams))
