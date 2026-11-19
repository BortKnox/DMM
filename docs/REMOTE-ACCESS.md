# DMM / PERSONAL REMOTE ACCESS

[Back to the workbench](../README.md) · [Local setup](../README.md#run-it) · [Playback and credential notes](FIELD-NOTES.md)

Use this optional setup for an always-on home PC and your own trusted phone or media center. It adds Caddy and Tailscale to the base Python, Node/Yarn and MongoDB setup. The host still supplies bandwidth, storage and FFmpeg CPU.

DMM has shared settings and saved records, without app authentication or per-user isolation. A private tailnet restricts network access; it does not add user accounts to DMM. Keep access limited to trusted personal devices, and check that your tailnet sharing and access policy match that boundary.

## BUILD FOR ONE ORIGIN

Install Tailscale on the host and client devices and sign into the same personal network. From `frontend`, build without a separate backend origin. Make sure no `.env` file or earlier environment value embeds an old server address.

PowerShell:

```powershell
$env:REACT_APP_BACKEND_URL = ""
yarn build
```

macOS / Linux shell:

```bash
REACT_APP_BACKEND_URL= yarn build
```

The browser will request `/api` on the same origin as the frontend. This is different from the two-port development setup in the [README](../README.md#run-it).

## KEEP THE BACKEND ON LOOPBACK

Keep MongoDB on loopback and start FastAPI from `backend`, with your Python virtual environment active.

PowerShell:

```powershell
$env:MONGO_URL = "mongodb://127.0.0.1:27017"
$env:DB_NAME = "dmm"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

macOS / Linux shell:

```bash
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=dmm \
  python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Unlike development, these commands do not enable `--reload`. Keep the backend running while you use the instance.

## SERVE THE APP AND API

Save this as `Caddyfile` in the repository root. Replace `YOUR-HOST.YOUR-TAILNET.ts.net` with the host's actual Tailscale DNS name. Run Caddy from that root so `frontend/build` resolves to the built app.

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

```bash
caddy run --config Caddyfile
```

In another terminal on the host:

```bash
tailscale serve --bg http://127.0.0.1:8080
```

Open the private HTTPS URL Tailscale prints on the second device. Generate the Harbor or Stremio installation link from that private URL, verify its hostname before installing, and keep the link private. A loopback-only manifest URL works on the backend PC, not a separate media center.

The `--bg` setting keeps the Tailscale Serve configuration in the background. It does not supervise Caddy, FastAPI or MongoDB; those processes must remain running. Starting the stack after a reboot needs your own service setup.

## PUBLIC PREVIEW, PRIVATE INSTANCE

The [GitHub Pages site](https://bortknox.github.io/DMM/) previews the project and browses public Cinemeta metadata. It is not the React/FastAPI deployment. TorBox actions, saved records, add-on serving and server conversion belong to your private instance.

Do not expose the local API as a public service in this form. Review the [instance and private-link notes](FIELD-NOTES.md#instance-data-and-private-links) before sharing access, even within a tailnet.
