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
## Playback and library decisions

The browser requests direct playback first. The TorBox resolver registers a torrent on the account to obtain its torrent and file IDs, then requests a temporary download link. Playing a source can therefore add a TorBox dashboard entry. DMM never automatically deletes that entry. Playing an existing TorBox download requests its file link directly.

**Save to DMM** stores the selected release, title and optional episode in the instance database. It does not contact TorBox. Saving the same release and episode twice updates one record. **Unsave** only removes the DMM record. The separate **TorBox downloads** tab reads the connected account and its delete action affects TorBox.

### Playback verification

| Path | Observation | Remaining check |
| --- | --- | --- |
| Direct | User verified playback and seeking on a 720p release. A separate H.264 release labelled DDP 5.1 had picture and silent audio. | Device and track support vary. |
| Server conversion | Local FFmpeg produced audible stereo and clear picture past five minutes on the reported release. The historical 35–45 second stall occurred during conversion. | Long-session stability and arbitrary seeking. |

Conversion selects the first audio track, encodes stereo AAC and copies supported H.264 video. Its fragmented MP4 pipe supplies data sequentially. Seeking beyond generated output requires a different delivery path, such as a seek request that restarts conversion at a source timestamp. FFmpeg and ffprobe belong on the backend host. Browser users need no yt-dlp, codec pack or external player for this workflow.

### Metadata integrations

TMDB supplies catalogue, metadata and season data when configured. Cinemeta supports keyless lookup. TMDB title enrichment uses OMDb ratings, Fanart.tv movie logos and RPDB poster URLs. TheTVDB currently has a credential test only. TorBox supplies availability, downloads and playback links. A successful credential check establishes access to that probe, not complete metadata coverage. TorBox poster matching from release filenames is best-effort.
