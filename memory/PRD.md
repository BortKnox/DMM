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
- Discover/home (trending hero + popular grid), Movies & TV browse.
- Global TMDB search + results grid.
- Title detail: hero, metadata, season/episode selectors, sources list with cached badges, quality parsing (res/source/codec/HDR/audio), regex filter, cached-only toggle, resolution chips. Actions: Play (Cache & Play if uncached → resolves TorBox direct link), Add to TorBox, Copy magnet.
- Library page: TorBox mylist with status/progress, Play (largest video file), Delete.
- Settings: TorBox connection status, API key override, indexer source toggles.
- Stremio Addon page: source selection, manifest generation, Install to Stremio (stremio://) + Open Stremio Web + copy URL.
- Stremio backend: manifest.json, stream (cached-first sorted, resolve-on-click redirect), catalog (TorBox library), meta.
- Verified: 100% backend (17 pytest) + 100% frontend flows.

## Backlog / Remaining (P1/P2)
- P1: Warm/prefetch source cache on trending to cut first-load latency (~5-8s cold).
- P1: Sidebar TorBox status occasionally shows "Not connected" if user/me call is slow — add short-lived cache/retry.
- P2: More indexers (YTS, Usenet via TorBox usenet API) as additional toggle sources.
- P2: Trakt/watchlist integration, "recently added" library sorting, genres browse.
- P2: Split server.py into routers (tmdb/torbox/indexers/stremio).

## Next Tasks
- Address first-load latency and connection-status flakiness if user reports it.
- Expand indexer list on request.
