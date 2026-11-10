# Flight-memory demo

This is the Chainlit and Hindsight application from the presentation. It retains the flight scenario, shows extracted facts, and recalls the same question with and without a subject tag filter. Tags are assigned by a model, and the app displays a failed check if the result differs from the expected scenario. This is a demonstration, not a production privacy or erasure system.

## Setup

The original stage setup used Python 3.11, `just`, Hindsight 1.2.0 and an Azure AI Foundry OpenAI-compatible Responses endpoint. You need network access and a compatible deployed model; model results and latency can vary. Run from this directory:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cp .env.example .env
# Edit .env: set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL.
just warm-models
```

The lock file records the stage environment; a fresh installation on another platform has not been verified. `warm-models` downloads public embedding and reranking models. Normal startup uses the local model cache but still sends the input to the configured LLM provider. Never commit `.env`.

In separate terminals, from this directory:

```sh
just up       # Hindsight API
just app      # Chainlit UI
```

Open <http://127.0.0.1:8000/> (or the configured `APP_PORT`). Enter the example from `scenario.yaml`. `just architecture` runs the same walkthrough in a terminal against the running API. `just test` runs the unit tests with the isolated environment. The optional `just control` requires a separately installed stage-local Node and Hindsight control plane; it is not required for the demo.

The app and services bind to loopback; do not expose them to the Internet. Banks and source text persist in local database state, and execution can create local artifacts. These are Gitignored, not encrypted or automatically erased. Do not use real sensitive information for the sample conversation.
