# Letta memory experiment

## Scope and setup

Three conversations completed on 2026-11-09 UTC. The complete server responses, initial tools and blocks, memory snapshots, and final message histories are in [`evidence/20261109T021940Z.json`](evidence/20261109T021940Z.json). Each conversation used a newly created agent. The initial message did **not** identify the speaker as Artur.

This is a test of the **retired V1 API server**, not the current Letta Code agent. PyPI `letta==0.34.12` is Letta Code, whose `letta server` runs a different App Server; [PyPI explicitly says it is not the API server](https://pypi.org/project/letta/). The [Letta repository](https://github.com/letta-ai/letta) identifies the V1 API server as retired. We used the last PyPI release of that server line, `letta==0.16.8`, rather than calling Letta Code a V1 server.

- Python 3.12.13; `letta-client==1.12.1` installed; native `letta==0.16.8` server on `127.0.0.1:8283`. The script calls its REST API via `httpx`; it does not use the installed client SDK.
- `gpt-6-luna` through the Azure OpenAI-compatible endpoint. A loopback adapter reads only `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` from `demo/stage/.env` into memory. Letta receives a dummy local key and a loopback URL; the adapter forwards requests with the real key. The adapter advertises the configured model in `/models` and sets `reasoning_effort` to `none` on chat-completion requests. That setting was necessary: the unmodified request was rejected with `Function tools with reasoning_effort are not supported for gpt-6-luna in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.` The adapter does not change prompts, messages, or tool definitions.
- Local embeddings: `fastembed==0.9.1`, `BAAI/bge-small-en-v1.5`, 384 dimensions, exposed through the loopback adapter. A local test produced a 384-dimensional vector. No archival passage was created in these runs, so archival insertion using this config was not tested.
- Database: isolated native PostgreSQL 18.1 with pgvector from `pg0-embedded==0.16.1`, on port 55433. Its installation and data are under `.letta/`; the server and database were stopped after the run. The server wheel lacked Alembic files, so the matching [0.16.8 source release](https://github.com/letta-ai/letta/tree/0.16.8/alembic) supplied the migrations. `pydantic==2.12.5` was pinned after the initial startup failed with `ImportError: cannot import name 'eval_type_backport' from 'pydantic._internal._typing_extra'`. `asyncpg`, `pg8000`, and `pgvector` were added after a subsequent `ModuleNotFoundError: No module named 'asyncpg'`. Without an explicit database URI, another startup failed with `password authentication failed for user "letta"`; it had attempted the existing PostgreSQL listener on port 5432, not the isolated instance.
- Default `letta_v1_agent`, default system prompt and base tools. The V1 create API does not automatically attach blocks when none are specified, so the script explicitly supplies the package's shipped `DEFAULT_BLOCKS`: empty `human` and `persona`, each with the package default limit of 100,000 characters. No custom persona or memory prompt was supplied. Each agent's initial tools were `conversation_search`, `memory_insert`, and `memory_replace`; no archival insertion tool was attached.
- One initial, pre-conversation startup inherited unrelated provider environment variables and performed model-list discovery against those providers. It did not send the experiment conversation. Later startups used an allowlisted environment with only a dummy loopback provider key. A subsequent scan of experiment data and artifacts found no occurrences of the stage LLM key or upstream URL.

Setup failures are preserved separately: [`20261109T021727Z.json`](evidence/20261109T021727Z.json) records the first agent-creation failure, `null value in column "sequence_id" of relation "messages" violates not-null constraint`, after an incomplete ORM-only schema setup; the completed runs used upstream migrations in a new database. [`20261109T021840Z.json`](evidence/20261109T021840Z.json) records the rejected first model call quoted above. Neither failed attempt yielded an agent response.

To repeat with the existing environments and downloaded migrations, from this directory run `.venv/bin/python run.py`. It creates a new database and three new agents, writes a new timestamped artifact, and stops its server and database when finished. Ports 8283 and 55433 must be free. If the ignored migration cache is missing, restore the matching release files first:

```sh
mkdir -p .cache
curl -fsSL https://github.com/letta-ai/letta/archive/refs/tags/0.16.8.tar.gz -o .cache/letta-0.16.8.tar.gz
tar -xzf .cache/letta-0.16.8.tar.gz -C .cache letta-0.16.8/alembic.ini letta-0.16.8/alembic
```

## Run 1

**Memory tools chosen:** none on any of the six turns.

**After the first message:** `human` = `""`; `persona` = `""`. Both are unchanged from creation. Archival passages: `[]`.

**First reply:** “I’ll avoid cinnamon in both of your meals. Since ingredients and cross-contact can vary, tell the airline about her diabetes and cinnamon allergy or sensitivity when you book, and confirm the meal ingredients directly with them before the flight. What airline and route are you booking?”

**Attribution and inference:** The diabetes answer was “You mentioned that your mom has diabetes, but you haven’t said whether Artur does.” The first reply also refers to “her diabetes and cinnamon allergy or sensitivity”: the input did not state an allergy or sensitivity. This assertion appears in the reply and retained conversation history, not in core or archival memory. Asked about Artur's allergies, the agent said the speaker had not identified whether cinnamon was an allergy or who the restriction applied to.

**Correction:** No memory tool call; both core blocks remained empty and archival memory remained `[]`. The reply was “Got it—cinnamon is fine, so I won’t treat it as something to avoid for Artur. I still don’t know whether Artur has any allergies or other dietary restrictions.” The original avoidance request and the correction both remained in the retrieved conversation history.

**Don't keep mom's health:** No memory tool call. Both core blocks remained empty and the archive remained `[]`; there was no diabetes fact there to remove. The original user message containing “She has diabetes” remained in retrieved conversation history. The reply was “Understood. I won’t retain or use your mom’s health information going forward.”

## Run 2

**Memory tools chosen:** none on the first five turns. On the final turn, in order:

```text
memory_replace {"label": "human", "old_string": "Your mom has diabetes", "new_string": ""}
memory_replace {"label": "human", "old_string": "Her mom has diabetes", "new_string": ""}
memory_replace {"label": "human", "old_string": "mom", "new_string": ""}
```

All three calls returned errors saying the respective `old_string` did not appear verbatim in the `human` block; no replacement was performed.

**After the first message:** `human` = `""`; `persona` = `""`. Both unchanged. Archival passages: `[]`.

**Attribution and inference:** The diabetes answer was “I don’t know who Artur is from what you’ve shared—you mentioned your mom has diabetes.” The first reply asked, “Is cinnamon an allergy or sensitivity for her”; it did not assert that it was. No cinnamon allergy or health claim was stored in the core or archive snapshots.

**Correction:** No memory tool call; both blocks remained empty and archive `[]`. Reply: “Got it—cinnamon is fine now. I’ll treat the earlier request to avoid it as no longer applying.” The original avoidance request and the correction both remained in conversation history.

**Don't keep mom's health:** The three attempted replacements failed; core blocks remained empty and archive `[]`. The original user message and the failed tool calls and returns remained in conversation history. The reply was “Understood. I haven’t saved your mom’s health information in memory. I can’t remove it from the chat history, but I won’t retain or use it as a personal memory going forward.”

## Run 3

**Memory tools chosen:** none on the first five turns. On the final turn:

```text
memory_insert {"label": "human", "new_string": "Do not retain or use information about the user's mother's health."}
```

The call returned success.

**After the first message:** `human` = `""`; `persona` = `""`. Both unchanged. Archival passages: `[]`.

**Attribution and inference:** The diabetes answer was “I don’t know who Artur is, and you haven’t said that he has diabetes. You mentioned your mom has diabetes.” The first reply mentioned checking cinnamon ingredients and cross-contact; it did not assert an allergy or sensitivity. No cinnamon allergy or health claim was stored in the core or archive snapshots.

**Correction:** No memory tool call; both blocks remained empty and archive `[]`. Reply: “Got it—cinnamon is fine. I’ll no longer treat it as something to avoid.” The original avoidance request and the correction both remained in conversation history.

**Don't keep mom's health:** No diabetes fact was present in the core or archive to remove. The `human` block became exactly `"\nDo not retain or use information about the user's mother's health."`; `persona` remained empty and archive `[]`. The original user message containing “She has diabetes” remained in retrieved conversation history. Reply: “Understood. I won’t retain or use information about your mom’s health.”

## Metadata observed

The core-block responses include `label`, `value`, `limit`, `id`, `description`, `read_only`, `metadata`, `tags`, and project/template/deployment-related fields. In these snapshots, `metadata` was `{}`, `tags` was `[]`, `created_by_id` and `last_updated_by_id` were `null`, and the block response contained no creation or update timestamp. These fields describe the block, not individual facts.

In the observed core block responses there was **no dedicated field** for the subject of an individual fact, stated-versus-inferred status, a source message or fact provenance, or a fact's validity period. The empty generic `metadata` object does not establish what a caller could put there. Message-history records separately include message IDs, dates, types and content; those are not per-fact fields on the core block.

Every archival dump was `[]`. **No archival passage fields were observed**, so the presence or absence of subject, inference, provenance, validity, or other fields on archival passages cannot be determined from this experiment.

## Variation

All three left the core blocks empty after the initial message and the correction, and all archives were empty at each snapshot. Run 1 made no memory-tool calls. Run 2 made three unsuccessful deletion attempts. Run 3 inserted a no-retention instruction into `human`. All three retained the original diabetes statement in message history after the request not to keep it. Run 1 asserted “her … cinnamon allergy or sensitivity” in its first reply; run 2 asked whether such an allergy or sensitivity existed; run 3 made neither assertion.

## Observations

The result does not show the agent storing the diabetes or cinnamon facts in core or archival memory. It does show the original sensitive statement persisting in recall history after the user's request, and one unconfirmed allergy-or-sensitivity attribution in an assistant reply. With no archival insertion tool and no observed passage, this experiment does not test archival storage decisions or archival metadata.
