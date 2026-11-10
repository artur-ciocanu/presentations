# Agent-memory experiments

These are observations from specific runs, not a ranking of the projects. The reports describe the prompts, configuration, results, and limitations of each trial:

- [Mem0](mem0/REPORT.md)
- [Letta V1 API server](letta/REPORT.md) — the retired server, not current Letta Code
- [Letta Code](letta-code/REPORT.md)
- [Hindsight](hindsight/REPORT.md)

Each report links to recorded JSON under `evidence/`. The public copies retain the experimental inputs, results, timestamps and identifiers, with the original machine's home-directory prefix and corporate hostname replaced. The source recordings remain in the local, ignored archive. The experiment conversation is sample text and is intentionally retained in the evidence, including after deletion requests: it is not evidence that every copy was erased.

## Repeating the experiments

These are historical research scripts, not a turnkey benchmark. Results are model-dependent and will differ on another run. All runners read `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` from [`../stage/.env`](../stage/.env.example). They send the sample conversation to that provider and may download models. Use a disposable environment, review the scripts before running them, and avoid real personal data.

Each directory contains `run.py` and a `requirements.lock` snapshot from its original Python environment. For example, from the experiment directory:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python run.py
```

Additional requirements:

- **Mem0:** uses local Qdrant and downloads the embedding model.
- **Letta V1:** also needs a separate `.server-venv` from `requirements-server.lock` and the matching Alembic files, as described in its report; it starts a local PostgreSQL instance and API server.
- **Letta Code:** uses macOS `sandbox-exec`, starts a local App Server, and permits agent tool execution. The sandbox restricts writes and protects selected paths, but does not block all reads outside the experiment. Use a disposable machine or account without sensitive files. It is not portable as-is to other operating systems.
- **Hindsight:** start `server.py` in one terminal before `run.py` in another; it starts local PostgreSQL and downloads embedding and reranking models.

Fresh installations have not been independently verified. Reports describe the original versions and setup failures. New runs write to ignored `artifacts/` and local state directories; inspect and sanitize output before sharing it. Git ignore is not encryption.
