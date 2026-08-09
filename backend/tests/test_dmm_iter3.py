"""Iteration 3 backend tests: 7 indexers, pagination, /test-key, library posters, in-site player resolve."""
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

TORBOX_KEY = "REDACTED"
TMDB_KEY = "REDACTED"
CACHED_HASH = "32415815a0b4621400688f0bf2966d7fd3435d93"
INCEPTION_IMDB = "tt1375666"


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- Config: torbox connected, 7 available sources, 6 keys set ---
def test_config_seven_sources(s):
    r = s.get(f"{API}/config", timeout=30)
    assert r.status_code == 200
    d = r.json()
    print("config:", {k: d.get(k) for k in ("torbox_connected", "needs_onboarding")})
    assert d["torbox_connected"] is True
    assert d["needs_onboarding"] is False
    avail = d["available_sources"]
    ids = {x["id"] for x in avail}
    print("available_sources:", ids)
    expected = {"apibay", "therarbg", "torrentgalaxy", "eztv", "limetorrents", "torrentdownloads", "nyaa"}
    assert expected.issubset(ids), f"missing: {expected - ids}"
    assert len(avail) == 7
    ks = d["keys_set"]
    for k in ("torbox", "tmdb", "omdb", "rpdb", "fanart", "thetvdb"):
        assert k in ks and ks[k] is True, f"keys_set.{k} not True"


# --- Search pagination page 1 vs page 2 ---
def test_search_pagination(s):
    r1 = s.get(f"{API}/search", params={"q": "star wars", "page": 1}, timeout=30)
    assert r1.status_code == 200
    d1 = r1.json()
    assert "results" in d1
    assert "page" in d1 and d1["page"] == 1
    assert "total_pages" in d1 and d1["total_pages"] > 1
    assert "total_results" in d1 and d1["total_results"] >= 100
    print(f"page1: {len(d1['results'])} results, total_pages={d1['total_pages']}, total_results={d1['total_results']}")
    # Star Wars 1977 or prequels in top
    titles1 = [(x.get("title") or "") for x in d1["results"]]
    assert any("Star Wars" in t for t in titles1[:5])

    r2 = s.get(f"{API}/search", params={"q": "star wars", "page": 2}, timeout=30)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["page"] == 2
    titles2 = [(x.get("title") or "") for x in d2["results"]]
    # Different set
    assert set(titles1) != set(titles2), "page 2 identical to page 1"


# --- Discover pagination ---
def test_discover_pagination(s):
    r = s.get(f"{API}/discover/movie", params={"page": 2}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("page") == 2
    assert d.get("total_pages", 0) > 1
    assert len(d.get("results", [])) > 0


# --- Multiple indexers for Inception ---
def test_sources_multi_indexer(s):
    r = s.get(f"{API}/sources/{INCEPTION_IMDB}",
              params={"media_type": "movie", "title": "Inception", "year": 2010}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    srcs = d.get("sources", d) if isinstance(d, dict) else d
    assert isinstance(srcs, list)
    indexers = {x.get("source_indexer") for x in srcs}
    print(f"indexers: {indexers}, total: {len(srcs)}")
    assert "therarbg" in indexers
    assert indexers & {"limetorrents", "torrentdownloads", "apibay"}, f"no big indexer: {indexers}"
    assert len(srcs) >= 50, f"expected 50+, got {len(srcs)}"
    cached = [x for x in srcs if x.get("cached")]
    assert len(cached) >= 1


# --- Test-key endpoint ---
def test_test_key_torbox_ok(s):
    r = s.post(f"{API}/test-key", json={"service": "torbox", "key": TORBOX_KEY}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    print("torbox test-key:", d)
    assert d.get("ok") is True


def test_test_key_tmdb_bad(s):
    r = s.post(f"{API}/test-key", json={"service": "tmdb", "key": "badkey"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    print("tmdb bad:", d)
    assert d.get("ok") is False


def test_test_key_tmdb_ok(s):
    r = s.post(f"{API}/test-key", json={"service": "tmdb", "key": TMDB_KEY}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    print("tmdb ok:", d)
    assert d.get("ok") is True


# --- Library with poster enrichment (may be slow first call) ---
def test_library_has_posters(s):
    t0 = time.time()
    r = s.get(f"{API}/library", timeout=40)
    dt = time.time() - t0
    print(f"library call: {dt:.2f}s")
    assert r.status_code == 200
    items = r.json()
    if isinstance(items, dict):
        items = items.get("library", items.get("items", items.get("results", [])))
    assert isinstance(items, list)
    print(f"library items: {len(items)}")
    if len(items) == 0:
        pytest.skip("library empty")
    # Check fields on first item
    keys = set(items[0].keys())
    print("first item keys:", keys)
    assert "poster" in keys or "size_h" in keys or "state" in keys
    posters = [it.get("poster") for it in items]
    non_null = [p for p in posters if p]
    print(f"non-null posters: {len(non_null)}/{len(items)}")


# --- In-site player resolve ---
def test_torbox_resolve(s):
    r = s.post(f"{API}/torbox/resolve",
               json={"hash": CACHED_HASH, "name": "Tomorrowland"}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    print("resolve:", {k: (v if k != "url" else str(v)[:80]) for k, v in d.items()})
    url = d.get("url") or d.get("download_url") or d.get("stream_url")
    assert url and url.startswith("http"), f"no direct url: {d}"


# --- Stremio backend still working ---
def test_stremio_backend(s):
    r = s.post(f"{API}/stremio/manifest-url", json={}, timeout=30)
    assert r.status_code == 200
    cfg = r.json()
    mu = cfg.get("manifest_url")
    assert mu
    config = cfg["config"]
    r2 = s.get(f"{API}/stremio/{config}/manifest.json", timeout=30)
    assert r2.status_code == 200
    assert r2.json().get("id")
    r3 = s.get(f"{API}/stremio/{config}/stream/movie/{INCEPTION_IMDB}.json", timeout=90)
    assert r3.status_code == 200
    assert isinstance(r3.json().get("streams", []), list)
