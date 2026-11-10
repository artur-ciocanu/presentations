# Mem0 experiment

## Setup

- Successful trials: 2026-11-09 02:00:52–02:01:17 UTC. Raw outputs, IDs, timestamps, and history: [20261109T020052.152101Z.json](evidence/20261109T020052.152101Z.json).
- `mem0ai` 2.2.1 (latest on PyPI when installed), Python 3.12.13, `sentence-transformers` 6.2.0. Local Hugging Face embedder `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions; on-disk Qdrant with matching dimensions. Each run used a new Qdrant directory and a separate SQLite history database. An initial `get_all` returned an empty list in each run.
- Mem0 `openai` LLM provider, model `gpt-6-luna`, Azure AI Foundry OpenAI-compatible endpoint. Credentials and endpoint were read from `demo/stage/.env`; neither is recorded here. Telemetry was disabled. The initial conversation and correction were supplied as user and assistant messages with `user_id="artur"`. No custom extraction or update prompts or instructions were supplied.
- The first attempt used the default OpenAI-provider settings. Both adds in all three runs failed with `LLMError: LLM extraction failed: Error code: 400 - Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.` Its stores remained empty. The failure and empty search results are preserved in [20261109T015846.669044Z.json](evidence/20261109T015846.669044Z.json). The first dependency installation also timed out downloading PyTorch; a retry succeeded.
- For the successful trials, the only LLM-provider change was `is_reasoning_model=True`. In this Mem0 version that omits `max_tokens`, `temperature`, and `top_p` from the provider request. The prompts were not changed. Mem0 2.2.1's `get_all` and `search` require `filters={"user_id": "artur"}` rather than a top-level `user_id`; this scopes them to the same user. Search results below are from before the correction, using default search settings. Run again with `.venv/bin/python run.py` from this directory; each invocation makes new stores and a new artifact.

## Stored memories and add events

Texts below are verbatim. Each initial add returned one `ADD` event per listed initial memory. Each correction add returned one `ADD` event for the listed correction memory. All original memories remained in `get_all` after correction; no `UPDATE` or `DELETE` event was returned. History for each newly added correction memory contains an `ADD` event with `old_memory: null`; full records are in the successful artifact.

### Run 1

Initial, A (`ADD`):

> User is booking a long flight with their mother, who has diabetes, and wants to avoid in-flight food containing cinnamon.

Correction (`ADD`):

> User no longer needs to avoid cinnamon in the in-flight meal options for the long flight with their mother.

### Run 2

Initial, A (`ADD`):

> User is booking a long flight with their mother, who has diabetes, and wants to avoid any in-flight food containing cinnamon.

Initial, B (`ADD`):

> Assistant said it would look at in-flight meal options for both the user and the user's mother.

Correction (`ADD`):

> For the long flight with their mother, who has diabetes, the user has changed their food restriction: cinnamon is fine now, rather than something to avoid.

### Run 3

Initial, A (`ADD`):

> User is booking a long flight with their mother, who has diabetes, and wants to avoid food containing cinnamon.

Initial, B (`ADD`):

> The assistant planned to look into in-flight meal options for the user and their mother.

Correction (`ADD`):

> User has updated the food preference for the long flight with their mother: cinnamon is now acceptable, replacing the earlier request to avoid it.

## Attribution and inference

- All three initial A texts attribute diabetes to the mother: “their mother, who has diabetes”. Run 2's correction also says “their mother, who has diabetes”. No stored text says the user has diabetes.
- No stored text calls cinnamon an allergy or health condition. Run 1's initial text says “wants to avoid in-flight food containing cinnamon”; run 2's correction calls it a “food restriction”.

## Fields returned

Every memory in the successful `get_all` outputs had exactly these fields: `id`, `memory`, `hash`, `metadata`, `created_at`, `updated_at`, `user_id`, and `attributed_to`. In all of them `metadata` was `null`, `user_id` was `artur`, and `attributed_to` was `user` or `assistant`. Search results had those fields plus `score`. Full field values are in the artifact.

- Separate subject-of-fact field other than `user_id`: **no**. The mother is identified in the text, not a separate field. The `attributed_to` value is `user` for the text about the mother's diabetes, and `assistant` for the assistant-acknowledgement texts.
- Stated-versus-inferred field: **no**.
- Provenance: **partial**. `attributed_to` gives a coarse `user`/`assistant` attribution in these outputs; there is **no source-message ID, source text, or message reference** in the returned memory. It is not a separate subject field.
- Validity period: **no**. `created_at` and `updated_at` are present, but no validity-start, validity-end, or expiration field is returned.

These are observations of fields returned in this experiment, not claims about fields available in other Mem0 configurations.

## Correction and variation

In all three successful runs the correction produced an `ADD`, and the original cinnamon-avoidance memory was kept alongside it. For example, run 1 retained “wants to avoid in-flight food containing cinnamon” and added “User no longer needs to avoid cinnamon in the in-flight meal options for the long flight with their mother.”

The initial memory wording varied. Run 1 stored one initial memory; runs 2 and 3 stored two, including a separate assistant-acknowledgement memory. Each run added one differently worded correction. Diabetes remained attributed in the text to the mother in every run, and none of the stored texts called cinnamon an allergy. Search results and scores also varied.

## Search results before correction

Each letter refers to the verbatim initial text for that run above. Results are in returned order; scores are copied without rounding. Empty means `{"results": []}`.

| Query | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| What health conditions does the user have? | A: 0.30173120829879996 | B: 0.33911367351112337; A: 0.3034457815561029 | A: 0.3356581606339267; B: 0.27018592220492443 |
| Does Artur have diabetes? | A: 0.33881776759118426 | A: 0.3437053489660611; B: 0.179846814522926 | A: 0.3551368645390084; B: 0.13873123621502698 |
| Does Artur have any allergies? | A: 0.23842872796135028 | A: 0.2534390657763085; B: 0.11032001214187412 | A: 0.23735364721075347 |
| What should we avoid serving Artur? | A: 0.24389662931745124 | A: 0.24724193992808813; B: 0.10693434012216209 | A: 0.26308724427554814; B: 0.14227096382799415 |
| What do we know about Artur's mom? | Empty | B: 0.23288556967248908 | B: 0.24205233144412108 |

## Observations

The mother’s diabetes was preserved in the stored text, but a search asking whether Artur has diabetes still returned that text. The correction did not remove the earlier cinnamon-avoidance text in these trials. `attributed_to` supplied a speaker-like attribution, but the returned memories did not include a separate subject, exact source message, stated-versus-inferred label, or validity period.
