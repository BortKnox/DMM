# DMM — Debrid Media Manager

DMM has a React frontend and a FastAPI backend. The backend uses MongoDB for storage and integrates with TorBox and TMDB.

## Run locally

Start a local MongoDB instance first. From `backend/`, with a Python virtual environment active:

```sh
pip install -r requirements.txt
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=dmm uvicorn server:app --reload
```

Open <http://localhost:8000/docs> to inspect the API. In a second terminal, from `frontend/`, use Yarn Classic:

```sh
yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

Open <http://localhost:3000> for the app. Use only a trusted local environment; do not expose this development setup to the internet.
