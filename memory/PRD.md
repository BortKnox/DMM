# DMM — Debrid Media Manager (TorBox) + Stremio Addon

## Original Problem Statement
Redesign the "unprofessional" debridmediamanager.com into a sleek, premium app focused on TorBox: search everything genuinely cached, see what's available to download to the server, manage the library, and find items to cache when nothing exists. Additionally, build a Stremio addon (generated as an installable manifest.json from the site) that handles library, seeking pre-cached content, and finding items to cache — all around TorBox. Design must match the metallic blue/silver DMM logo, dark mode.

## Architecture
- **Frontend**: React 19 + Tailwind + shadcn, react-query, framer-motion, sonner. Dark premium theme, Outfit/Inter fonts, metallic blue→silver accents.
- **Backend**: FastAPI (all routes under `/api`), httpx async. MongoDB stores single `config` doc (torbox key override + enabled sources).
- **Data sources** (all reachable from container):
  - TMDB — metadata, search, posters, seasons/episodes.
  - apibay (The Pirate Bay JSON) — torrent sources by IMDB id (movies + general).
  - EZTV — series torrents by IMDB id with season/episode.
  - TorBox main API — checkcached, createtorrent, requestdl, mylist, controltorrent, user/me.
  - NOTE: `search-api.torbox.app` is NXDOMAIN / unreachable, so it is intentionally not used.

## Core Requirements (static)
- TorBox built-in default key with per-user override (Settings).
- Multi-indexer, selectable sources.
- Cached availability detection + one-click cache & stream.
- Stremio addon with per-user manifest (embeds key), streams + library catalog + meta.

## Implemented (2026-06)
### Iteration 1
- Discover/home, Movies & TV browse, global TMDB search, title detail with sources + cached badges, Library, Settings, Stremio addon (manifest/stream/catalog/meta).

### Iteration 2
- **Community-ready keys**: NO keys shipped in code/.env. All keys (TorBox, TMDB, + optional OMDb/RPDB/Fanart/TheTVDB) stored per-instance in Mongo `config`, entered via Onboarding modal (first run) or Settings. Preview DB is seeded at runtime.
- **All reachable indexers**: apibay (TPB), TheRARBG, EZTV, Nyaa (anime, toggle). Merged + deduped per source toggles.
- **Search relevance fixed**: TMDB multi (2 pages), popularity-sorted, obscure/low-vote filtered. "Star wars" now returns the full saga incl. prequels.
- **Speed**: TTL cache (sources 15min, meta 1h, TorBox connection 60s). Second loads are instant.
- **Enrichment**: OMDb RT/Metacritic/IMDb score badges, RPDB rating-baked posters, Fanart logos on hero.
- **Sources UX**: list + compact grid view toggle, all results shown (no pagination), minimal filtering (regex, cached-only, resolution chips).
- **Bulk**: one-tap "Cache Season" + /api/torbox/bulk-add.
- Verified: 100% backend (iter1 17 + iter2 9) + 100% frontend.

## Backlog / Remaining (P1/P2)
- P1: Background prefetch on trending/hero to kill first-open cold latency.
- P2: Trakt Sync (needs a Trakt app client_id/secret from user — OAuth).
- P2: OpenRouter AI-powered search (LLM via integration).
- P2: MDBList lists import; split server.py into routers.

## Next Tasks
- Address first-load latency and connection-status flakiness if user reports it.
- Expand indexer list on request.
