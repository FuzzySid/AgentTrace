# AgentTrace

AgentTrace is a compact observability workbench for agent runs. This scaffold includes a FastAPI API backed by mock query payloads, a DuckDB schema for spans, and a React dashboard for traces, costs, regressions, and telemetry capture tiers.

## Run locally

Requirements: Python 3.11+ and Node.js 18+.

From the repository root, start both servers with:

```sh
make dev
```

Or use two terminals:

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```sh
cd frontend
npm install
npm run dev
```

The UI is at http://localhost:5173 and the API docs are at http://localhost:8000/docs. Vite proxies `/api` requests to FastAPI. All dashboard data is served over HTTP from mock query functions in `backend/app/store/queries.py`.

