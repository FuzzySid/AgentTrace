# AgentTrace

AgentTrace is a compact observability workbench for agent runs. The Traces screen reads real exported spans from DuckDB. Cost, regression, and telemetry views still use sample payloads while those analyses are developed.

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

The UI is at http://localhost:5173 and the API docs are at http://localhost:8000/docs. Vite proxies `/api` requests to FastAPI. The Traces API reads runs, traces, span details, and the fixture confusion matrix from DuckDB.

## Agent runner and tracing

The runner requires a provider account and Phoenix OTLP receiver. Start Phoenix in a separate terminal (install it in its own environment with `pip install arize-phoenix`, then run `phoenix serve`; the UI defaults to http://localhost:6006). Copy `backend/.env.example` to `backend/.env`, fill the provider name, three tier model identifiers and API key, and keep the gRPC receiver on port 4317 (or set `PHOENIX_OTLP_ENDPOINT`). In the backend virtual environment, run:

```sh
cd backend
python -m app.run --tasks fixtures/tasks.json --tier attrs --run-id local-001
```

Set `--tier full` to capture GenAI prompt and response bodies. `attrs` records span metadata and real provider token usage without message bodies. Run identifiers and task identifiers are attached to every span; add `--eval` or set `is_eval: true` on a task to tag its trace for evaluation.

Spans are exported to Phoenix and persisted in `backend/data/agenttrace.duckdb`. `serialized_bytes` is measured by serializing each span through the OTLP protobuf encoder at export time. The hand-written benchmark contains 28 tasks across the five failure injections and seven clean cases. Run all tasks with `python -m app.run --tasks fixtures/tasks.json --tier attrs --run-id local-fixtures`; task entries with `expected_failure_class` are automatically tagged `agenttrace.is_eval = true`.

Fixture injection is applied by wrappers around graph nodes in `app/agent/injections.py`; the graph nodes do not inspect injection labels. Retrieval miss and cascade fixtures restrict search to an absent document id, tool timeout sleeps past the configured wrapper deadline and records an ERROR tool span, model hallucination uses a synthesis prompt without the abstention instruction, and orchestration loop forces critique to its three-revision cap. The cascade additionally records a failed output assertion after the retrieval miss.

The classifier receives only `EvidenceSpan` values in `app/analysis/failure_classifier.py`. Query code builds those values from a whitelist of status, operation, retrieval count/score, critique-cap, and output-assertion signals. It does not pass answer text, fixture metadata, or `agenttrace.injected_failure`; that ground-truth attribute is removed from trace-detail responses. The scorer reads the injection marker only after classification and maps the mode to its class; it uses `expected_failure_class` as a fallback. Clean cases contribute to overall accuracy and are excluded from the 4x4 failure-class matrix.

### GenAI semantic conventions checked

Checked 2026-09-29 against the OpenTelemetry GenAI semantic conventions repository. The repository has no tagged release at this time, so this project pins the reviewed snapshot at commit [`0c87594975195608dc91b3f702e250a7b240c151`](https://github.com/open-telemetry/semantic-conventions-genai/commit/0c87594975195608dc91b3f702e250a7b240c151). GenAI spans use the snapshot's `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, and `gen_ai.usage.output_tokens` names.
