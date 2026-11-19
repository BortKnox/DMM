# DMM / Debrid Media Manager

**Find a film, pick a release, and watch it where you are.** I built DMM for the evenings I use Harbor on the media center and the ones when all I have is a browser.

[Project preview](https://bortknox.github.io/DMM/) · [Local setup](#run-it) · [Playback field notes](#playback-verification)

![DMM Discover with the light bench interface](docs/screening-room.jpg)

```
UNIT     03 / BORT KNOX
TYPE     PERSONAL MEDIA WORKBENCH
CLIENT   BROWSER / HARBOR / STREMIO / VLC / MPC-HC
ENGINE   REACT / FASTAPI / MONGODB / FFMPEG
```

## WHAT IT DOES

- **Discover and search.** Browse movies and TV, search titles, and explore seasons through Cinemeta without an API key. Add TMDB in Settings to switch the catalogue provider.
- **Sources.** Pulls results from seven indexers per title, merges and de-duplicates them, and marks what is
  already cached on TorBox. Sort by match, seeders, size or resolution; filter by regex, instant-only or
  resolution.
- **Cache and play.** One-tap cache for a single source or a whole season. Cached items play in an embedded
  player; an optional ffmpeg endpoint remuxes or transcodes to browser-friendly MP4 when native playback fails.
- **Library.** Your TorBox library with cover art, grid and list views, download and delete.
- **Harbor and Stremio.** Choose sources, resolution, optional size limits and cached-only results for each installation. Paste the private manifest URL into Harbor or open it with Stremio. A separate media center needs a reachable backend address. The default loopback setup works on the backend PC.
- **Native players.** The chain-link control beside Copy magnet resolves a temporary TorBox file URL. Paste it into VLC’s Open Network Stream or MPC-HC’s Open File. Resolving can register the release in TorBox. Generate a fresh link when one expires.
- **Keys stay with you.** No keys ship in the code. TorBox and TMDB (plus optional OMDb, RPDB, Fanart and
  TheTVDB) are entered in Settings, each with a Test button, and stored in your own MongoDB.
  "Disconnect and erase keys" wipes them.

## RUN IT

You need Python 3, Node with Yarn Classic, MongoDB, and `ffmpeg` on the path if you want Universal Playback.

```bash
git clone --branch feature/discovery-desk https://github.com/BortKnox/DMM.git
cd DMM/backend
python -m pip install fastapi uvicorn httpx motor python-dotenv
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

### Instance data and client preferences

This build is for a trusted local instance. Provider credentials live in the instance MongoDB configuration. Anyone with access to that database can read them. Separate installations use separate databases. One shared deployment currently shares settings and saved titles across visitors; it needs account isolation before public multi-user hosting. Browser local storage remembers display preferences such as poster size and theme.

New add-on installations use private random installation identifiers. Older installation links can contain an encoded TorBox key and should be treated as credentials. Rated posters are served through the backend to keep the RPDB key out of browser image URLs.

Discover poster and title links open the detail page. More like this steers recommendations. Save on a title retains it before a release is chosen. Source filtering and sorting apply to the full returned set; the page renders 24 matches at a time. Fetching additional upstream results incrementally is separate work.

### Personal remote access

For an always-on home PC and your own devices, Tailscale Personal and Tailscale Serve provide private HTTPS without a hosting subscription. The PC still supplies bandwidth, storage and FFmpeg CPU. Install Tailscale on both devices and sign into the same personal network.

1. Build the frontend with `yarn build` in `frontend`. Leave `REACT_APP_BACKEND_URL` unset so the browser uses its current origin.
2. Run FastAPI and MongoDB on loopback per the local setup above. From the repo root, run Caddy with the example below saved as `Caddyfile`. Replace the Caddy hostname placeholder with the actual Tailscale DNS name.
3. Run `tailscale serve --bg http://127.0.0.1:8080` on the host. Open the private HTTPS URL it prints on the second device. Generate the Harbor installation link from that private URL and verify its hostname before installing.

```caddyfile
http://127.0.0.1:8080 {
    handle /api/* {
        reverse_proxy 127.0.0.1:8000 {
            header_up X-Forwarded-Host YOUR-HOST.YOUR-TAILNET.ts.net
            header_up X-Forwarded-Proto https
        }
    }
    handle {
        root * frontend/build
        try_files {path} /index.html
        file_server
    }
}
```

The GitHub Pages catalogue browses public metadata directly. TorBox, saved releases and server conversion run on the private instance. Keep access limited to trusted personal devices until per-user settings and authentication are implemented.
