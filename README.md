# AgentTrace

AgentTrace is a small agent observability workbench. The Traces, Cost, Regressions, and Telemetry screens read spans persisted in DuckDB. The comparison charts are computed from paired fixture runs; the production telemetry recommendation is a human-written product judgment.

## Local setup

Requirements: Python 3.11+, Node.js 18+, a configured model provider account, and a Phoenix OTLP receiver. Copy `backend/.env.example` to `backend/.env`, fill the provider configuration, tier-to-model mapping, API key, and optional API base. Start Phoenix with its OTLP receiver on port 4317, or set `PHOENIX_OTLP_ENDPOINT`.

Install and start the UI and API with:

```sh
make dev
```

The UI is at http://localhost:5173 and the API docs are at http://localhost:8000/docs. For a single task run from the backend directory:

```sh
cd backend
python -m app.run --tasks fixtures/tasks.json --tier mid --capture-tier attrs --prompt-version verbose --run-id local-001
```

`--tier` selects the model service tier (`cheap`, `mid`, or `premium`); `--capture-tier` selects `full`, `attrs`, or `sampled`. `--prompt-version` selects the verbose or terse prompt. `--eval` tags every span in a run as evaluation data. The critique judge calls are tagged separately by default.

## Reproduce the benchmark

After configuring `backend/.env` and Phoenix, run:

```sh
make demo
```

This executes the same 28 hand-written fixture tasks for the verbose/terse comparison, the cheap/mid comparison, and all three capture tiers. It writes a data-led tier note to `reports/tier-comparison.md`. Each compared run has its own `run_id`; regression metrics are paired by `task_id`. These runs make real provider calls and use provider-reported token counts.

The fixture corpus is original project-authored material in `backend/fixtures/corpus/`. The runner applies injection wrappers from `backend/app/agent/injections.py`; graph nodes do not inspect injection labels. Retrieval misses restrict search to absent IDs, tool timeouts sleep beyond their wrapper deadline, model-hallucination cases use a synthesis prompt without the abstention instruction, orchestration cases force the critique cap, and cascade cases combine a retrieval miss with an unsupported answer.

## Cost and failure evidence

`analysis/cost_model.py` prices token usage using `backend/app/config/pricing.py`. Session latency is the root span's wall-clock duration. Spans explicitly tagged `agenttrace.is_eval = true` (with `--eval` for a run or `is_eval` on a task) are excluded from production session cost and shown separately. The agent critique loop is normal production work and remains in production cost. Cost per successful session divides all production spend, including failed attempts, by the number of successful sessions. Cost by node type is based on the model wrapper's metered spans, so nested auto-instrumentation does not double count usage.

The classifier accepts only `EvidenceSpan` records built from an allowlist of operation, status, retrieval result, critique-cap, and final-output assertion signals. It cannot inspect answer text, fixture expectations, or injection labels. The final `expected_contains` check runs after the graph and records only a boolean signal.

`agenttrace.injected_failure` is ground truth for the scorer. Injection wrappers write it to their own spans; classification receives evidence records with no arbitrary attribute map, so it cannot read the marker. The scorer reads the marker only after classification to build the 4×4 failure-class matrix. Trace-detail API responses remove this attribute. Clean fixtures contribute to overall accuracy but are excluded from the four failure-class rows.

## Capture tiers

The graph records content signals independently of the selected capture tier. `CaptureTierSpanExporter` applies policy before either DuckDB or Phoenix export:

- `full` retains all attributes and opt-in prompt/completion content events.
- `attrs` retains `gen_ai.*` and `agenttrace.*` attributes while dropping content attributes and events.
- `sampled` applies the attrs policy and keeps a deterministic 10% of traces, with an exporter tail rule that always keeps a trace whose root span has status `ERROR`.

`serialized_bytes` measures each tier-filtered serialized OTLP protobuf span. `analysis/tax_harness.py` runs the identical task list for each tier and attempts all capability questions against that tier's captured rows. The recommendation text lives separately in `backend/app/config/recommendation.py`.

## API privacy

API responses expose service tiers, prompt versions, span operations, usage totals, and calculated costs. Provider and concrete model identifiers are removed from span details; content and model names are scrubbed before those details are returned. Pricing and recommendations are project configuration, not live provider metadata.

## GenAI semantic conventions

Checked 2026-09-29 against the OpenTelemetry GenAI semantic-conventions repository. At that check there was no tagged release, so the reviewed snapshot is pinned at commit [`0c87594975195608dc91b3f702e250a7b240c151`](https://github.com/open-telemetry/semantic-conventions-genai/commit/0c87594975195608dc91b3f702e250a7b240c151). This snapshot uses `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, and `gen_ai.usage.output_tokens`.
