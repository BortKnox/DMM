# DMM — DEBRID MEDIA MANAGER

**A light-first front end for TorBox: search a title, see which sources are already cached, play or cache with one click, and take it all into Stremio as a plugin.**

```
UNIT     DMM
TYPE     TOOL
STACK    REACT / FASTAPI / MONGODB / FFMPEG
STATUS   ACTIVE
```

## WHAT IT DOES

- **Discover and search.** Browse movies and TV, search titles, and explore seasons through Cinemeta without an API key. Add TMDB in Settings to switch the catalogue provider.
- **Sources.** Pulls results from seven indexers per title, merges and de-duplicates them, and marks what is
  already cached on TorBox. Sort by match, seeders, size or resolution; filter by regex, instant-only or
  resolution.
- **Cache and play.** One-tap cache for a single source or a whole season. Cached items play in an embedded
  player; an optional ffmpeg endpoint remuxes or transcodes to browser-friendly MP4 when native playback fails.
- **Library.** Your TorBox library with cover art, grid and list views, download and delete.
- **Stremio plugin.** Generates a per-user `manifest.json` serving streams, a library catalogue and metadata.
- **Keys stay with you.** No keys ship in the code. TorBox and TMDB (plus optional OMDb, RPDB, Fanart and
  TheTVDB) are entered in Settings, each with a Test button, and stored in your own MongoDB.
  "Disconnect and erase keys" wipes them.

## RUN IT

You need Python 3, Node with Yarn Classic, MongoDB, and `ffmpeg` on the path if you want Universal Playback.

```bash
git clone https://github.com/BortKnox/DMM.git
cd DMM/backend
pip install -r requirements.txt
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=dmm uvicorn server:app --reload
```

API docs: <http://localhost:8000/docs>. In a second terminal:

```bash
cd DMM/frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

App: <http://localhost:3000>. Treat this as a trusted-local setup; do not expose it to the internet as is.

## LAYOUT

```
backend/server.py      # FastAPI app, all routes under /api
backend/tests/         # API test suites
frontend/src/pages/    # Home, Detail, Library, SearchResults, Settings, Stremio
frontend/src/components/   # Layout, MediaCard, Player, SourceRow, Onboarding
design_guidelines.json # theme and typography rules (dark, metallic blue and silver)
memory/PRD.md          # product notes and iteration history
```

## NOTES

- `server.py` is one large file. Splitting it into routers is on the list.
- Trakt sync and AI search are planned, not built.
- Source indexers are third-party sites that change; expect some to break over time.
- You are responsible for how you use the services you connect and for the content you access with them.

Personal project, shared as is. Issues and pull requests may not get a reply; forking is welcome.
