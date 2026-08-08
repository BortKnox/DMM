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

### Iteration 3
- **Rebrand**: app "Debrid Media Manager", developer "by Bort Knox". All "Stremio" wording removed from UI → "Add Plugin" / "plugin" / "player" (deep-link install still works).
- **7 indexers** (all reachable server-side): The Pirate Bay, TheRARBG, TorrentGalaxy, EZTV, LimeTorrents, TorrentDownloads, Nyaa. (YTS/1337x/EXT.to are Cloudflare-walled and excluded.)
- **Real pagination**: search/discover return page + total_pages + total_results; UI has numbered pages + prev/next (search "star wars" = 257 results / 13 pages).
- **Sources filter + sort**: sort by Best match / Seeders / Size (asc/desc) / Resolution, on top of regex filter, Instant-only toggle, resolution chips, and list/grid view.
- **Library upgraded**: TMDB cover-art matching per item, grid + list views, poster cards.
- **In-site player**: Play opens an embedded video modal (with external-open fallback); uncached "Play" now sends to TorBox to download instead of hanging.
- **Key management**: nothing shipped with keys; keys stored in DB and remembered. Settings has 6 keys each with a **Test** button + success/fail feedback; Onboarding modal on first run.
- **Enrichment**: OMDb RT/MC/IMDb badges, RPDB rating-baked posters, Fanart logos.
- Verified: 100% backend (iter1 17 + iter2 9 + iter3 10) + ~98% frontend.

## Backlog / Remaining (P1/P2)

### Iteration 4
- **Instant loading**: warm-on-hover (media cards prefetch meta + pre-scrape sources in background) + backend startup warm of trending & library, so opening a title is snappy.
- **Key-free shipping confirmed**: no keys in code or `.env` (only in DB); added Settings "Disconnect & erase keys" + first-run Onboarding. Verified reset→onboarding→re-seed cycle.
- **Universal Playback**: in-house ffmpeg transcode endpoint (`/api/stream/transcode`, host-allowlisted to tb-cdn/torbox) — remuxes h264 or transcodes HEVC→h264 720p to browser-playable fragmented MP4. Player has a Universal toggle + auto-fallback when native decode fails.
- Verified 100% backend (iter4 8/8) + 100% frontend.
- NOTE: ffmpeg is a SYSTEM dependency (installed via apt) — a deployment must include ffmpeg for Universal Playback.

## Older Backlog (P1/P2)
- P2: Trakt Sync (needs Trakt app client_id/secret — OAuth).
- P2: OpenRouter AI search (LLM integration).
- P2: Split server.py (~1160 lines) into routers.
- Note: TheTVDB key the user supplied fails v4 login (legacy/pin key); Test button reports honestly. Not wired into features.

## Next Tasks
- Address first-load latency and connection-status flakiness if user reports it.
- Expand indexer list on request.
