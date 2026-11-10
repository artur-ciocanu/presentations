# Hindsight experiment

## Setup

- Six trials, 2026-11-09 03:04:21–03:08:40 UTC. Full requests, responses, memory details, document histories, traces and timestamps: [20261109T030421.627705Z.json](evidence/20261109T030421.627705Z.json). [Setup evidence](evidence/20261109T025747.047512Z.json). The evidence file deliberately retains the original test conversation even after the API deletion.
- Native `hindsight-api` 1.2.0, `hindsight-client` 1.2.0, `hindsight-api-slim` 1.2.0, Python 3.12.13, `pg0-embedded` 0.16.1 and `sentence-transformers` 6.2.0. The installed client was not used: `run.py` used the HTTP REST API through `httpx`. The server bound `127.0.0.1:8890`; its embedded PostgreSQL used port 55434 and this directory’s `.data/pg0`. Both were stopped after the trials.
- LLM: `gpt-6-luna`, `openai-responses`, with the three permitted values read from `demo/stage/.env` and supplied to the server process only. No LLM parameter override or built-in prompt edit was needed. Local defaults: `BAAI/bge-small-en-v1.5` embeddings, 384 dimensions, and `hindsight-ai/hs-rerank-1` reranker; both loaded on CPU.
- Initial startup did not complete within a 180-second readiness wait; both model weight downloads were observed as zero-byte incomplete files several minutes into that startup. Restarted with `HF_HUB_DISABLE_XET=1`. Separate single HTTPS transfers timed out: `curl: (28) Operation timed out after 599332 milliseconds with 91943706 out of 133466304 bytes received` and `curl: (28) Operation timed out after 599335 milliseconds with 92487001 out of 227593826 bytes received`. Parallel HTTPS range downloads completed; both model files matched the SHA-256 values published by Hugging Face. The verified reranker was put in this experiment’s cache and the server restarted. The model IDs did not change.
- All runs used bank ID `artur`, deleted and recreated between trials. Each newly created bank's initial memory and operation lists were empty. The initial text did not name the user. Each user/assistant pair was retained as one document with `async: false`; `initial`, `correction`, and `privacy` were distinct document IDs. Every retain returned HTTP 200 and `success: true`; exact responses and usage are in the artifact. `reflect` was not run.
- Config A: create bank with `{}` and no bank overrides. Resolved `enable_observations: true` and `enable_auto_consolidation: true`. Config B: the following bank overrides; each retain additionally carried `tags: ["task:flight-booking"]`. `tag: true` makes extracted label values filterable tags.

To repeat, start `.venv/bin/python server.py` and then `.venv/bin/python run.py` from this directory. The script refuses to overwrite a pre-existing `artur` bank; the last trial's post-erasure bank remains in the isolated database. The ignored model cache already contains the verified default weights.

```json
{
  "retain_mission": "Record user-declared facts with who each fact is about. Do not promote assistant suggestions or statements to facts about the user.",
  "enable_observations": false,
  "entity_labels": [
    {
      "key": "subject",
      "description": "Who the fact is about; distinguish the user from a family member.",
      "type": "value",
      "optional": true,
      "tag": true,
      "values": [
        {
          "value": "user",
          "description": "The user speaking"
        },
        {
          "value": "family_member",
          "description": "A family member of the user"
        }
      ]
    },
    {
      "key": "category",
      "description": "The category of the fact.",
      "type": "multi-values",
      "tag": true,
      "values": [
        {
          "value": "health",
          "description": "Health conditions or health information"
        },
        {
          "value": "food_preference",
          "description": "Food preferences and restrictions"
        }
      ]
    }
  ]
}
```

The input documents, exactly:

```text
user: I'm booking a long flight for me and my mom. She has diabetes. I want to avoid anything with cinnamon.
assistant: Got it. I'll look at the in-flight meal options for both of you.

user: Actually, cinnamon is fine now.
assistant: Thanks, noted.

user: Please don't keep anything about my mom's health.
assistant: Understood.
```

## Stored memories and retain events

Each run’s `F` labels are local to that run. The list prints the verbatim text, `fact_type`, entities and tags returned at the first listed snapshot for that exact ID and text, plus the entities from the corresponding individual-memory GET. A changed text on the same ID gets a new label. The snapshot lines list every returned memory in order. Complete fields, subsequent entity-order variations, and individual memory GET responses are in the artifact. Source facts and derived observations are both listed.

### Config A, run 1

- **F1** "The user is booking a long flight for themself and their mother." — type `observation`; list entities `""`; detail entities `["cinnamon","mother","long flight","user","diabetes"]`; tags `[]`; ID `2e67a64f-a1a7-4795-aa7d-556de8e7bb1f`; first seen in `initial`.
- **F2** "The user's mother has diabetes." — type `observation`; list entities `""`; detail entities `["user","diabetes","long flight","cinnamon","mother"]`; tags `[]`; ID `8b5e7402-9bf9-4ddb-ba90-00d069853d82`; first seen in `initial`.
- **F3** "The user wants to avoid food containing cinnamon during the long flight." — type `observation`; list entities `""`; detail entities `["user","diabetes","long flight","cinnamon","mother"]`; tags `[]`; ID `93a7ce7c-ecb9-4713-8ac5-81110fc8653f`; first seen in `initial`.
- **F4** "User is booking a long flight for themself and their mother, who has diabetes; user wants to avoid food containing cinnamon. | Involving: user, user's mother" — type `world`; list entities `"diabetes, long flight, mother, cinnamon, user"`; detail entities `["long flight","cinnamon","mother","user","diabetes"]`; tags `[]`; ID `d5fa8f1f-7264-4826-b125-e3a108de1d81`; first seen in `initial`.
- **F5** "Пользователю теперь подходит корица." — type `observation`; list entities `""`; detail entities `["корица","user"]`; tags `[]`; ID `7f0e1257-adab-460c-8890-e54a9d033a6f`; first seen in `corrected`.
- **F6** "Пользователю теперь подходит корица. | Involving: user" — type `world`; list entities `"user, корица"`; detail entities `["корица","user"]`; tags `[]`; ID `82516579-8fd7-4653-8b4f-5059e9faaadd`; first seen in `corrected`.
- **F7** "User requests that no information about their mother's health be retained. | Involving: user; user's mother" — type `world`; list entities `"mother, user, health"`; detail entities `["mother","user","health"]`; tags `[]`; ID `428aff30-5d8a-4a83-96f5-810129cc712f`; first seen in `privacy`.

- Initial (2026-11-09T03:04:34.617806+00:00): F1, F2, F3, F4.
- After correction (2026-11-09T03:04:43.802148+00:00): F5, F6, F1, F2, F3, F4.
- After privacy request (2026-11-09T03:05:49.860476+00:00): F7, F5, F6, F1, F2, F3, F4.
- After document deletion (2026-11-09T03:06:52.656646+00:00): F7, F5, F6.
- Initial entities `(name, mention_count)`: `[["diabetes",1],["long flight",1],["mother",1],["cinnamon",1],["user",1]]`.
- Entities immediately after deletion `(name, mention_count)`: `[["user",2],["health",1],["mother",1],["корица",1]]`.
- At the privacy snapshot, background operations were `[{"task_type":"consolidation","status":"processing","error_message":null}]`.
- At the erased snapshot, background operations were `[{"task_type":"consolidation","status":"pending","error_message":null},{"task_type":"consolidation","status":"processing","error_message":null}]`.

### Config A, run 2

- **F1** "User wants to avoid anything containing cinnamon on the flight." — type `observation`; list entities `""`; detail entities `["mother","diabetes","long flight","user","cinnamon"]`; tags `[]`; ID `621c9b06-a8c9-428c-a436-f8757ee6d514`; first seen in `initial`.
- **F2** "User is booking a long flight with their mother." — type `observation`; list entities `""`; detail entities `["long flight","cinnamon","mother","user","diabetes"]`; tags `[]`; ID `76ab5d65-6a55-4a46-ba2b-f6c5c7bbc5ad`; first seen in `initial`.
- **F3** "The user's mother has diabetes." — type `observation`; list entities `""`; detail entities `["user","long flight","mother","cinnamon","diabetes"]`; tags `[]`; ID `7d84cc37-0a9e-4daf-9564-d668624ad2ac`; first seen in `initial`.
- **F4** "User is booking a long flight with their mother, who has diabetes, and wants to avoid anything containing cinnamon. | Involving: user and user's mother | Dietary constraint for the flight." — type `world`; list entities `"diabetes, mother, cinnamon, long flight, user"`; detail entities `["mother","cinnamon","long flight","diabetes","user"]`; tags `[]`; ID `d6a88520-26b7-4c66-9bf5-877c86f04aa1`; first seen in `initial`.
- **F5** "User is now fine with cinnamon. | Involving: user" — type `world`; list entities `"cinnamon, user"`; detail entities `["user","cinnamon"]`; tags `[]`; ID `8f9012da-b642-42a6-ac12-f41f6c1a9d49`; first seen in `corrected`.
- **F6** "User wanted to avoid anything containing cinnamon on the flight until they said they were fine with cinnamon on 2026-11-09." — type `observation`; list entities `""`; detail entities `["mother","diabetes","long flight","user","cinnamon"]`; tags `[]`; ID `621c9b06-a8c9-428c-a436-f8757ee6d514`; first seen in `corrected`.
- **F7** "User requests that no information about their mother's health be retained." — type `observation`; list entities `""`; detail entities `["mother","user","health"]`; tags `[]`; ID `3017a7bd-f714-48d4-a7ba-11fd193b577e`; first seen in `privacy`.
- **F8** "User requests that no information about their mother's health be retained. | Involving: user; user's mother" — type `world`; list entities `"health, user, mother"`; detail entities `["health","mother","user"]`; tags `[]`; ID `9dc93df0-ab8a-4e32-a4d1-b146fd75ddd4`; first seen in `privacy`.
- **F9** "Information about the user's mother's health was not retained following the user's request on 2026-11-09." — type `observation`; list entities `""`; detail entities `["user","long flight","mother","cinnamon","diabetes","health"]`; tags `[]`; ID `7d84cc37-0a9e-4daf-9564-d668624ad2ac`; first seen in `privacy`.
- **F10** "User is now fine with cinnamon." — type `observation`; list entities `""`; detail entities `["cinnamon","user"]`; tags `[]`; ID `79497a99-a01c-4e61-ae5e-ae158a8fefe6`; first seen in `erased`.

- Initial (2026-11-09T03:07:02.565333+00:00): F1, F2, F3, F4.
- After correction (2026-11-09T03:07:12.070595+00:00): F5, F6, F2, F3, F4.
- After privacy request (2026-11-09T03:07:22.857338+00:00): F7, F8, F9, F5, F6, F2, F4.
- After document deletion (2026-11-09T03:07:27.264380+00:00): F7, F8, F10, F5.
- Initial entities `(name, mention_count)`: `[["diabetes",1],["mother",1],["cinnamon",1],["long flight",1],["user",1]]`.
- Entities immediately after deletion `(name, mention_count)`: `[["user",2],["mother",1],["health",1],["cinnamon",1]]`.

### Config A, run 3

- **F1** "The user wants to avoid cinnamon in in-flight meals." — type `observation`; list entities `""`; detail entities `["flight","user","mother","diabetes","cinnamon"]`; tags `[]`; ID `0ac36e8a-f95b-4d54-86d4-4ecf1b9cc4af`; first seen in `initial`.
- **F2** "The user's mother has diabetes." — type `observation`; list entities `""`; detail entities `["flight","user","cinnamon","diabetes","mother"]`; tags `[]`; ID `bb837ce4-ffa2-4fe9-92d5-ddd3caf3c91b`; first seen in `initial`.
- **F3** "User is booking a long flight with their mother." — type `observation`; list entities `""`; detail entities `["mother","diabetes","cinnamon","user","flight"]`; tags `[]`; ID `c615d6fa-a742-4a6f-8d7b-20c5232e1fed`; first seen in `initial`.
- **F4** "User is booking a long flight with their mother, who has diabetes, and wants to avoid cinnamon in the in-flight meals. | Involving: user, user's mother | The mother has diabetes, and the user wants to avoid cinnamon." — type `world`; list entities `"user, flight, cinnamon, diabetes, mother"`; detail entities `["cinnamon","user","diabetes","mother","flight"]`; tags `[]`; ID `def79eb2-7413-41fa-aebd-806bc4693090`; first seen in `initial`.
- **F5** "Пользователю теперь подходит корица." — type `observation`; list entities `""`; detail entities `["корица","user"]`; tags `[]`; ID `76aa13af-8602-4d8a-9d33-cc85ebfc1a9c`; first seen in `corrected`.
- **F6** "Пользователю теперь подходит корица. | Involving: user" — type `world`; list entities `"user, корица"`; detail entities `["user","корица"]`; tags `[]`; ID `91c886d2-134a-4588-81c2-2885135ba773`; first seen in `corrected`.
- **F7** "The user requests that no information about their mother's health be retained." — type `observation`; list entities `""`; detail entities `["health","mother","user"]`; tags `[]`; ID `9f7b5276-cf43-4fea-b659-e38121541789`; first seen in `privacy`.
- **F8** "User requests that no information about their mother's health be retained. | Involving: user; user's mother" — type `world`; list entities `"user, mother, health"`; detail entities `["health","mother","user"]`; tags `[]`; ID `9a124c47-87e0-42bf-88b3-ac773047e37f`; first seen in `privacy`.

- Initial (2026-11-09T03:07:36.975492+00:00): F1, F2, F3, F4.
- After correction (2026-11-09T03:07:45.792901+00:00): F5, F6, F1, F2, F3, F4.
- After privacy request (2026-11-09T03:07:56.707575+00:00): F7, F8, F2, F5, F6, F1, F3, F4.
- After document deletion (2026-11-09T03:08:01.303389+00:00): F7, F8, F5, F6.
- Initial entities `(name, mention_count)`: `[["user",1],["flight",1],["cinnamon",1],["diabetes",1],["mother",1]]`.
- Entities immediately after deletion `(name, mention_count)`: `[["user",2],["health",1],["mother",1],["корица",1]]`.

### Config B, run 1

- **F1** "User wants to avoid foods containing cinnamon while booking a long flight for themself and their mother. | Involving: User and user's mother" — type `world`; list entities `"cinnamon, long flight, user, subject:user, category:food_preference, mother"`; detail entities `["cinnamon","user","subject:user","category:food_preference","mother","long flight"]`; tags `["task:flight-booking","subject:user","category:food_preference"]`; ID `e3ca07f4-3cce-471a-8013-4d2bbc2f9b43`; first seen in `initial`.
- **F2** "User's mother has diabetes. | Involving: User's mother" — type `world`; list entities `"user, mother, diabetes, subject:family_member, category:health"`; detail entities `["user","category:health","mother","diabetes","subject:family_member"]`; tags `["task:flight-booking","subject:family_member","category:health"]`; ID `87071fed-f6c8-402f-addf-85281a76c41b`; first seen in `initial`.
- **F3** "User says cinnamon is fine now. | Involving: user" — type `world`; list entities `"user, subject:user, category:food_preference, cinnamon"`; detail entities `["cinnamon","user","subject:user","category:food_preference"]`; tags `["task:flight-booking","subject:user","category:food_preference"]`; ID `0ec5cf5c-2707-4bbc-ab63-085b43a82147`; first seen in `corrected`.
- **F4** "User requests that no information about their mother's health be retained. | Involving: User; user's mother" — type `world`; list entities `"category:health, user, mother, subject:user, health information"`; detail entities `["user","subject:user","health information","category:health","mother"]`; tags `["task:flight-booking","subject:user","category:health"]`; ID `40dcfcca-9d14-43fb-bba1-b925792b07f1`; first seen in `privacy`.

- Initial (2026-11-09T03:08:06.809319+00:00): F1, F2.
- After correction (2026-11-09T03:08:09.988543+00:00): F3, F1, F2.
- After privacy request (2026-11-09T03:08:12.906270+00:00): F4, F3, F1, F2.
- After document deletion (2026-11-09T03:08:13.360355+00:00): F4, F3.
- Initial entities `(name, mention_count)`: `[["user",2],["mother",2],["cinnamon",1],["subject:user",1],["category:food_preference",1],["long flight",1],["category:health",1],["diabetes",1],["subject:family_member",1]]`.
- Entities immediately after deletion `(name, mention_count)`: `[["user",2],["subject:user",2],["health information",1],["category:health",1],["mother",1],["cinnamon",1],["category:food_preference",1],["long flight",0],["diabetes",0],["subject:family_member",0]]`.
- At the erased snapshot, background operations were `[{"task_type":"graph_maintenance","status":"pending","error_message":null}]`.

### Config B, run 2

- **F1** "User wants to avoid anything containing cinnamon. | Involving: User" — type `world`; list entities `"user, subject:user, cinnamon, category:food_preference"`; detail entities `["cinnamon","category:food_preference","user","subject:user"]`; tags `["task:flight-booking","subject:user","category:food_preference"]`; ID `c7ea54fe-e76c-4e6e-a8cd-bc110b2fff21`; first seen in `initial`.
- **F2** "User's mom has diabetes. | Involving: User's mom" — type `world`; list entities `"user, diabetes, subject:family_member, mom, category:health"`; detail entities `["category:health","mom","user","diabetes","subject:family_member"]`; tags `["task:flight-booking","subject:family_member","category:health"]`; ID `ce4a95a1-8a34-4d7b-8799-a9c2de164a0f`; first seen in `initial`.
- **F3** "User is booking a long flight with their mom. | Involving: User and user's mom" — type `world`; list entities `"user, mom, flight, subject:user"`; detail entities `["flight","mom","user","subject:user"]`; tags `["task:flight-booking","subject:user"]`; ID `d1d2c26a-c73d-483a-a1a7-a7e654c2df17`; first seen in `initial`.
- **F4** "User says cinnamon is fine now. | Involving: user" — type `world`; list entities `"category:food_preference, subject:user, cinnamon, user"`; detail entities `["cinnamon","category:food_preference","user","subject:user"]`; tags `["task:flight-booking","subject:user","category:food_preference"]`; ID `e02d2956-b7a0-4f19-b45e-9e8338e92c82`; first seen in `corrected`.
- **F5** "User requests that nothing about their mother's health be retained. | Involving: user; user's mother | Privacy preference regarding the mother's health information." — type `world`; list entities `"subject:user, mother, user"`; detail entities `["mother","user","subject:user"]`; tags `["task:flight-booking","subject:user"]`; ID `d31b2243-cf80-4ea9-a764-195885989a5b`; first seen in `privacy`.

- Initial (2026-11-09T03:08:18.686715+00:00): F1, F2, F3.
- After correction (2026-11-09T03:08:21.710426+00:00): F4, F1, F2, F3.
- After privacy request (2026-11-09T03:08:24.874470+00:00): F5, F4, F1, F2, F3.
- After document deletion (2026-11-09T03:08:25.423310+00:00): F5, F4.
- Initial entities `(name, mention_count)`: `[["user",3],["mom",2],["subject:user",2],["cinnamon",1],["category:food_preference",1],["category:health",1],["diabetes",1],["subject:family_member",1],["flight",1]]`.
- Entities immediately after deletion `(name, mention_count)`: `[["user",2],["subject:user",2],["mother",1],["cinnamon",1],["category:food_preference",1],["category:health",0],["diabetes",0],["subject:family_member",0],["flight",0],["mom",0]]`.
- At the erased snapshot, background operations were `[{"task_type":"graph_maintenance","status":"pending","error_message":null}]`.

### Config B, run 3

- **F1** "Пользователь хочет избегать еды с корицей. | Involving: Пользователь" — type `world`; list entities `"subject:user, category:food_preference, user, корица"`; detail entities `["category:food_preference","user","корица","subject:user"]`; tags `["task:flight-booking","subject:user","category:food_preference"]`; ID `9d432432-1b79-4ab7-b988-b0978eafb04d`; first seen in `initial`.
- **F2** "У мамы пользователя диабет. | Involving: Мама пользователя" — type `world`; list entities `"subject:family_member, user, category:health, диабет, мама"`; detail entities `["user","category:health","диабет","мама","subject:family_member"]`; tags `["task:flight-booking","subject:family_member","category:health"]`; ID `00afec03-467f-43f5-9ddc-7d698a39f773`; first seen in `initial`.
- **F3** "Пользователь бронирует длительный перелёт для себя и мамы. | Involving: Пользователь и его/её мама" — type `world`; list entities `"мама, user, subject:user, перелёт"`; detail entities `["user","перелёт","мама","subject:user"]`; tags `["task:flight-booking","subject:user"]`; ID `8ae560e2-6692-48d9-b00d-dacc4aa9d180`; first seen in `initial`.
- **F4** "User says cinnamon is fine now. | Involving: user" — type `world`; list entities `"subject:user, cinnamon, category:food_preference, user"`; detail entities `["category:food_preference","user","cinnamon","subject:user"]`; tags `["task:flight-booking","subject:user","category:food_preference"]`; ID `65d3355d-1c59-4acf-aab2-603d05e38edf`; first seen in `corrected`.
- **F5** "User asks that information about their mom’s health not be retained. | Involving: user; user's mom" — type `world`; list entities `"subject:user, user's mom, category:health, health information, user"`; detail entities `["user","category:health","health information","user's mom","subject:user"]`; tags `["task:flight-booking","subject:user","category:health"]`; ID `fafcf703-d9a8-4cb8-89bd-2e52150cdff4`; first seen in `privacy`.

- Initial (2026-11-09T03:08:32.295468+00:00): F1, F2, F3.
- After correction (2026-11-09T03:08:35.516034+00:00): F4, F1, F2, F3.
- After privacy request (2026-11-09T03:08:38.892529+00:00): F5, F4, F1, F2, F3.
- After document deletion (2026-11-09T03:08:39.548314+00:00): F5, F4.
- Initial entities `(name, mention_count)`: `[["user",3],["мама",2],["subject:user",2],["category:food_preference",1],["корица",1],["category:health",1],["диабет",1],["subject:family_member",1],["перелёт",1]]`.
- Entities immediately after deletion `(name, mention_count)`: `[["user",2],["subject:user",2],["category:health",1],["health information",1],["user's mom",1],["category:food_preference",1],["cinnamon",1],["корица",0],["диабет",0],["subject:family_member",0],["перелёт",0],["мама",0]]`.
- At the erased snapshot, background operations were `[{"task_type":"graph_maintenance","status":"pending","error_message":null}]`.
- Follow-up at 2026-11-09T03:10:18.163783+00:00: entities `[["user",2],["subject:user",2],["category:health",1],["health information",1],["user's mom",1],["category:food_preference",1],["cinnamon",1]]`; operations `[["graph_maintenance","completed"]]`. Full follow-up responses are in `post_run_followup` in the artifact.

## Attribution and inference

- The initial world fact in every Config A run says the mother has diabetes, for example A1: “User is booking a long flight for themself and their mother, who has diabetes; user wants to avoid food containing cinnamon. | Involving: user, user's mother”. All three A runs also made the observation “The user's mother has diabetes.”
- All three Config B runs extracted a separate family-member-tagged diabetes world fact: B1 “User's mother has diabetes. | Involving: User's mother”; B2 “User's mom has diabetes. | Involving: User's mom”; B3 “У мамы пользователя диабет. | Involving: Мама пользователя” (Russian: the user’s mother has diabetes). The initial entity lists include `mother`, `mom`, and `мама`, respectively.
- No listed fact in any snapshot calls cinnamon an allergy, sensitivity, or health condition. The initial facts say the user wants to avoid it. The user’s name was not in the retained conversation.

## Fields returned

- Every memory-list item in these snapshots had exactly `id`, `text`, `context`, `date`, `fact_type`, `document_id`, `mentioned_at`, `occurred_start`, `occurred_end`, `entities`, `chunk_id`, `proof_count`, `tags`, `metadata`, `consolidated_at`, `consolidation_failed_at`, `state`, `invalidation_reason`, `invalidated_at`, `edited_at`, `updated_at`, and `source_memory_ids`. All `context` values were empty strings, all `metadata` objects were `{}`, and all states were `valid` in these snapshots. Recall entries have their own fields, including a `scores` object; every field is preserved in the artifact.
- Individual GETs of world facts returned `id`, `text`, `context`, `date`, `type`, `mentioned_at`, `occurred_start`, `occurred_end`, `entities`, `document_id`, `chunk_id`, `tags`, `metadata`, `observation_scopes`, `state`, `invalidation_reason`, `invalidated_at`, `edited_at`, `consolidated_at`, and `consolidation_failed_at`. Observation GETs additionally returned `history`, `source_memory_ids`, and `source_memories`. In every observation snapshot, the list endpoint returned an empty `entities` string, but the individual GET returned a nonempty entity array. For A1’s “The user's mother has diabetes.” observation, the individual GET included `cinnamon`, `long flight`, `user`, `mother`, and `diabetes`, not just the subject. These arrays are shown above verbatim, not treated as subject-role labels.
- Subject: **no dedicated subject-role field** in the returned records. A’s entity lists can include both `user` and `mother` without specifying their roles. B’s extracted `subject:user` or `subject:family_member` labels appear as entities and tags, giving a configurable subject classification; the flight fact in B2/B3 also mentions the mother but carries `subject:user`.
- Stated versus inferred: **no dedicated stated/inferred field**. `fact_type` distinguishes `world` from derived `observation`, and observations include `source_memory_ids`; it does not mark each claim as stated versus inferred.
- Provenance: **yes, document/chunk level** for raw facts: `document_id` and `chunk_id`; observations have null document/chunk fields and use `source_memory_ids`. These are not individual source-message IDs. The source document contains both turns.
- Time: **mention time present** (`mentioned_at`; also `date` and `updated_at`); `occurred_start` and `occurred_end` fields were present but null in every listed snapshot. No validity-start/end or expiry field was returned.

## Correction, privacy request and variation

- In all six runs the original world fact(s) remained valid after the separate correction document, alongside a new world fact saying cinnamon is now fine. Config B did not generate observations. In A2 the original cinnamon observation was updated in place to “User wanted to avoid anything containing cinnamon on the flight until they said they were fine with cinnamon on 2026-11-09.” In A1 and A3 a separate observation was created instead; the earlier avoidance observation remained.
- A1 and A3 stored the correction in Russian: “Пользователю теперь подходит корица.” B3 stored the initial three facts in Russian. No output language was configured. B1 stored two initial world facts; B2 and B3 stored three. Each A run stored one initial world fact and three initial observations.
- All six privacy messages produced a world fact recording the request. The original diabetes-containing world fact remained at the privacy snapshot in all six. In A2, a derived observation instead said “Information about the user's mother's health was not retained following the user's request on 2026-11-09.” The original diabetes-containing world fact was still present in that same snapshot. A1 had consolidation still processing at its privacy and deletion snapshots after the script’s bounded waits; no eventual A1 state was captured before the bank was recreated.

## Application-level erasure

Each trial called `DELETE /v1/default/banks/artur/documents/initial`. The document was chosen because reversible memory invalidation leaves the original source text intact. The successful response reported the number of source memory units deleted below. Because the original document contained the flight and cinnamon request as well as the diabetes statement, those source facts were also removed. Derived observations tied to the deleted document were absent from the immediate post-delete memory listings. The `correction` and `privacy` documents remained. `GET /documents/initial` returned 404 after deletion. This does not establish forensic removal from PostgreSQL storage, backups, client artifacts, or external LLM systems.

At every post-deletion snapshot, `GET /v1/default/banks/artur/llm-requests?limit=500` still returned a retain-extraction trace containing the original source: “user: I'm booking a long flight for me and my mom. She has diabetes. I want to avoid anything with cinnamon.” The response reported `retention_days: 1`. The per-run trace IDs and document history responses are below. The package defaults enable LLM tracing and leave `HINDSIGHT_API_LLM_TRACE_DELETE_WITH_DOCUMENT` off; the latter was not changed or tested. Hindsight documents that opt-in setting for deleting document-related traces. The audit-log list returned zero entries at both privacy and post-deletion snapshots in all runs.

### Config A, run 1

- Delete response: `{"success":true,"message":"Document 'initial' and 1 associated memory units deleted successfully","document_id":"initial","memory_units_deleted":1}`.
- Post-delete trace count `25`; original-text retain trace IDs `["2861bcfe-949f-46e2-9610-ff23657781ea"]`; retention days `1`.
- Post-delete history for `initial`: `[{"document_id":"initial","kind":"consolidation","created_at":"2026-11-09T03:04:32.966298Z","operation_id":"d50bd038-5d13-4216-9239-e0a17d831c20","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":3,"ids":["2e67a64f-a1a7-4795-aa7d-556de8e7bb1f","8b5e7402-9bf9-4ddb-ba90-00d069853d82","93a7ce7c-ecb9-4713-8ac5-81110fc8653f"]},"observations_updated":{"count":0,"ids":[]},"observations_removed":{"count":0,"ids":[]}}]` (total `1`).
- Post-delete history for `correction`: `[{"document_id":"correction","kind":"consolidation","created_at":"2026-11-09T03:04:42.334738Z","operation_id":"5bcbac8f-4608-4fb1-a8b2-66acf3f2749d","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":1,"ids":["7f0e1257-adab-460c-8890-e54a9d033a6f"]},"observations_updated":{"count":0,"ids":[]},"observations_removed":{"count":0,"ids":[]}}]` (total `1`).
- Post-delete history for `privacy`: `[]` (total `0`).

### Config A, run 2

- Delete response: `{"success":true,"message":"Document 'initial' and 1 associated memory units deleted successfully","document_id":"initial","memory_units_deleted":1}`.
- Post-delete trace count `35`; original-text retain trace IDs `["8414101d-7482-433c-a348-b68c46a9185e"]`; retention days `1`.
- Post-delete history for `initial`: `[{"document_id":"initial","kind":"consolidation","created_at":"2026-11-09T03:07:21.679386Z","operation_id":"8b187966-cd35-4ca8-bca3-4030b7870c7a","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":0,"ids":[]},"observations_updated":{"count":1,"ids":["7d84cc37-0a9e-4daf-9564-d668624ad2ac"]},"observations_removed":{"count":0,"ids":[]}},{"document_id":"initial","kind":"consolidation","created_at":"2026-11-09T03:07:10.130459Z","operation_id":"6a838b20-b47a-4e66-9b67-d3ae81828ad2","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":0,"ids":[]},"observations_updated":{"count":1,"ids":["621c9b06-a8c9-428c-a436-f8757ee6d514"]},"observations_removed":{"count":0,"ids":[]}},{"document_id":"initial","kind":"consolidation","created_at":"2026-11-09T03:07:01.717321Z","operation_id":"78c02e71-ba98-4f51-a990-3ee4c28835a1","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":3,"ids":["621c9b06-a8c9-428c-a436-f8757ee6d514","76ab5d65-6a55-4a46-ba2b-f6c5c7bbc5ad","7d84cc37-0a9e-4daf-9564-d668624ad2ac"]},"observations_updated":{"count":0,"ids":[]},"observations_removed":{"count":0,"ids":[]}}]` (total `3`).
- Post-delete history for `correction`: `[{"document_id":"correction","kind":"consolidation","created_at":"2026-11-09T03:07:26.839686Z","operation_id":"10ed39e9-1603-4f1e-82f1-916c4044369a","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":1,"ids":["79497a99-a01c-4e61-ae5e-ae158a8fefe6"]},"observations_updated":{"count":0,"ids":[]},"observations_removed":{"count":0,"ids":[]}},{"document_id":"correction","kind":"consolidation","created_at":"2026-11-09T03:07:10.130466Z","operation_id":"6a838b20-b47a-4e66-9b67-d3ae81828ad2","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":0,"ids":[]},"observations_updated":{"count":1,"ids":["621c9b06-a8c9-428c-a436-f8757ee6d514"]},"observations_removed":{"count":0,"ids":[]}}]` (total `2`).
- Post-delete history for `privacy`: `[{"document_id":"privacy","kind":"consolidation","created_at":"2026-11-09T03:07:26.839691Z","operation_id":"10ed39e9-1603-4f1e-82f1-916c4044369a","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":0,"ids":[]},"observations_updated":{"count":1,"ids":["3017a7bd-f714-48d4-a7ba-11fd193b577e"]},"observations_removed":{"count":0,"ids":[]}},{"document_id":"privacy","kind":"consolidation","created_at":"2026-11-09T03:07:21.679379Z","operation_id":"8b187966-cd35-4ca8-bca3-4030b7870c7a","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":1,"ids":["3017a7bd-f714-48d4-a7ba-11fd193b577e"]},"observations_updated":{"count":1,"ids":["7d84cc37-0a9e-4daf-9564-d668624ad2ac"]},"observations_removed":{"count":0,"ids":[]}}]` (total `2`).

### Config A, run 3

- Delete response: `{"success":true,"message":"Document 'initial' and 1 associated memory units deleted successfully","document_id":"initial","memory_units_deleted":1}`.
- Post-delete trace count `34`; original-text retain trace IDs `["af663713-7d3b-4eb5-8eb5-0a06a54e664c"]`; retention days `1`.
- Post-delete history for `initial`: `[{"document_id":"initial","kind":"consolidation","created_at":"2026-11-09T03:07:55.377140Z","operation_id":"7e9f8416-c9c8-4345-9d2d-5e27f88be07e","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":0,"ids":[]},"observations_updated":{"count":1,"ids":["bb837ce4-ffa2-4fe9-92d5-ddd3caf3c91b"]},"observations_removed":{"count":0,"ids":[]}},{"document_id":"initial","kind":"consolidation","created_at":"2026-11-09T03:07:35.614397Z","operation_id":"45641a73-f684-407c-94c1-ae9893f7bb41","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":3,"ids":["0ac36e8a-f95b-4d54-86d4-4ecf1b9cc4af","bb837ce4-ffa2-4fe9-92d5-ddd3caf3c91b","c615d6fa-a742-4a6f-8d7b-20c5232e1fed"]},"observations_updated":{"count":0,"ids":[]},"observations_removed":{"count":0,"ids":[]}}]` (total `2`).
- Post-delete history for `correction`: `[{"document_id":"correction","kind":"consolidation","created_at":"2026-11-09T03:07:45.261062Z","operation_id":"a95fc294-f460-4031-9230-661ace8f068d","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":1,"ids":["76aa13af-8602-4d8a-9d33-cc85ebfc1a9c"]},"observations_updated":{"count":0,"ids":[]},"observations_removed":{"count":0,"ids":[]}}]` (total `1`).
- Post-delete history for `privacy`: `[{"document_id":"privacy","kind":"consolidation","created_at":"2026-11-09T03:08:00.955031Z","operation_id":"337611bc-3053-4e5e-868b-cd8c03899340","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":0,"ids":[]},"observations_updated":{"count":1,"ids":["9f7b5276-cf43-4fea-b659-e38121541789"]},"observations_removed":{"count":0,"ids":[]}},{"document_id":"privacy","kind":"consolidation","created_at":"2026-11-09T03:07:55.377133Z","operation_id":"7e9f8416-c9c8-4345-9d2d-5e27f88be07e","fact_id":null,"facts_added":0,"facts_removed":0,"observations_created":{"count":1,"ids":["9f7b5276-cf43-4fea-b659-e38121541789"]},"observations_updated":{"count":1,"ids":["bb837ce4-ffa2-4fe9-92d5-ddd3caf3c91b"]},"observations_removed":{"count":0,"ids":[]}}]` (total `2`).

### Config B, run 1

- Delete response: `{"success":true,"message":"Document 'initial' and 2 associated memory units deleted successfully","document_id":"initial","memory_units_deleted":2}`.
- Post-delete trace count `26`; original-text retain trace IDs `["88594952-b773-4709-a22b-b12a62b3b375"]`; retention days `1`.
- Post-delete history for `initial`: `[]` (total `0`).
- Post-delete history for `correction`: `[]` (total `0`).
- Post-delete history for `privacy`: `[]` (total `0`).

### Config B, run 2

- Delete response: `{"success":true,"message":"Document 'initial' and 3 associated memory units deleted successfully","document_id":"initial","memory_units_deleted":3}`.
- Post-delete trace count `26`; original-text retain trace IDs `["37742dcb-d6de-4084-b3a0-e990c25eb811"]`; retention days `1`.
- Post-delete history for `initial`: `[]` (total `0`).
- Post-delete history for `correction`: `[]` (total `0`).
- Post-delete history for `privacy`: `[]` (total `0`).

### Config B, run 3

- Delete response: `{"success":true,"message":"Document 'initial' and 3 associated memory units deleted successfully","document_id":"initial","memory_units_deleted":3}`.
- Post-delete trace count `26`; original-text retain trace IDs `["2ce2c020-95b2-4bef-9478-9362ba8515ca"]`; retention days `1`.
- Post-delete history for `initial`: `[]` (total `0`).
- Post-delete history for `correction`: `[]` (total `0`).
- Post-delete history for `privacy`: `[]` (total `0`).

The immediate Config B snapshots still listed zero-mention diabetes/family-member entities with `graph_maintenance` pending. In the later B3 follow-up the maintenance operation had completed and those zero-mention entities no longer appeared; no later B1 or B2 entity snapshot was captured before bank recreation. Immediate and B3 follow-up entity listings are shown above. Config A1 also had consolidation in progress or pending at deletion, so the immediate state is not a settled-state guarantee. The histories above contained no document-deletion event; in B they were empty. Hindsight documents that synchronous retains do not create history entries, so an empty history is not proof that no retain occurred.

## Recall results

Each query is shown in returned order. `F` points to the exact text and type in that run’s list above; the number before each `F` is its rank. The score object is verbatim, unrounded, in `final`, `reranker`, `semantic`, `keyword` order as returned. Scores are ranking signals, not calibrated probabilities. All other returned fields are in the artifact. Filtered B queries used `tags: ["subject:user"]`, `tags_match: "any_strict"`; they exclude the facts tagged `subject:family_member`, not every fact mentioning a family member.

### Config A, run 1

**What health conditions does the user have?**
- 1. **F4** — `{"final":1.077083469498709,"reranker":0.979166863706415,"semantic":0.5977977514266968,"keyword":0.5}`
- 2. **F2** — `{"final":1.0745145060734893,"reranker":0.9768314422360441,"semantic":0.6809174025332156,"keyword":0.10000000149011612}`
- 3. **F1** — `{"final":0.0012278676339096371,"reranker":0.0011162433870621732,"semantic":0.49740773454858545,"keyword":0.10000000149011612}`
- 4. **F3** — `{"final":0.0009446442923438988,"reranker":0.0008587676027402349,"semantic":0.5526084899902344,"keyword":0.10000000149011612}`

**Does Artur have diabetes?**
- 1. **F2** — `{"final":0.16084343348346775,"reranker":0.14622131414411746,"semantic":0.6626930434314326,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.006187898991366721,"reranker":0.005625363141739329,"semantic":0.5753419399261475,"keyword":0.20000000298023224}`
- 3. **F1** — `{"final":1.2035663917617696e-05,"reranker":1.0941513473796147e-05,"semantic":0.39973873497612933,"keyword":null}`
- 4. **F3** — `{"final":1.1108294140791255e-05,"reranker":1.0098449977025935e-05,"semantic":0.45472681522369385,"keyword":null}`

**Does Artur have any allergies?**
- 1. **F2** — `{"final":0.0002827553128714224,"reranker":0.0002570503038131061,"semantic":0.46989597649312753,"keyword":null}`
- 2. **F4** — `{"final":2.6743368565229475e-05,"reranker":2.4312155074532968e-05,"semantic":0.4598950493460867,"keyword":null}`
- 3. **F3** — `{"final":2.5415849639330882e-05,"reranker":2.3105319596343195e-05,"semantic":0.46872663870732656,"keyword":null}`
- 4. **F1** — `{"final":1.1122572868928813e-05,"reranker":1.0111430643362186e-05,"semantic":0.35748141572211756,"keyword":null}`

**What should we avoid serving Artur?**
- 1. **F3** — `{"final":0.0022171093966798475,"reranker":0.0020155541495063645,"semantic":0.6429130264624371,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.0002744478845708018,"reranker":0.00024949809576302144,"semantic":0.5500462591592996,"keyword":0.10000000149011612}`
- 3. **F2** — `{"final":1.9584139279479183e-05,"reranker":1.7803764328623595e-05,"semantic":0.49578090049795764,"keyword":null}`
- 4. **F1** — `{"final":1.0316719612737963e-05,"reranker":9.378836721312383e-06,"semantic":0.4078797862744721,"keyword":null}`

**What do we know about Artur's mom?**
- 1. **F2** — `{"final":0.00362938536165168,"reranker":0.0032994414885724782,"semantic":0.573693948200165,"keyword":null}`
- 2. **F4** — `{"final":9.430339296814419e-05,"reranker":8.573036375796972e-05,"semantic":0.4945089519023895,"keyword":null}`
- 3. **F1** — `{"final":5.087205942514144e-05,"reranker":4.62473302642215e-05,"semantic":0.5027326641838163,"keyword":null}`
- 4. **F3** — `{"final":2.8280973691068127e-06,"reranker":2.5709978036356065e-06,"semantic":0.3416777551174164,"keyword":null}`

**What should we avoid serving Artur?** (after correction)
- 1. **F3** — `{"final":0.002217109280525589,"reranker":0.0020155541495063645,"semantic":0.6429130264624371,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.0002744478701924898,"reranker":0.00024949809576302144,"semantic":0.5500462591592996,"keyword":0.10000000149011612}`
- 3. **F5** — `{"final":6.0870236084833355e-05,"reranker":5.533658113853612e-05,"semantic":0.41028649684352014,"keyword":null}`
- 4. **F6** — `{"final":5.2130771303222115e-05,"reranker":4.7391612741814096e-05,"semantic":0.43129033669348826,"keyword":null}`
- 5. **F2** — `{"final":1.9584138253467032e-05,"reranker":1.7803764328623595e-05,"semantic":0.49578090049795764,"keyword":null}`
- 6. **F1** — `{"final":1.0316719072245501e-05,"reranker":9.378836721312383e-06,"semantic":0.4078797862744721,"keyword":null}`

**What do we know about Artur's mom?** (after erasure)
- 1. **F7** — `{"final":0.00036420581872162575,"reranker":0.000331096445013235,"semantic":0.5157197713851929,"keyword":null}`
- 2. **F6** — `{"final":1.7468321187998794e-05,"reranker":1.5880304623436566e-05,"semantic":0.4112550914287567,"keyword":null}`
- 3. **F5** — `{"final":1.7414297036685904e-05,"reranker":1.5831191719532514e-05,"semantic":0.39090263843536377,"keyword":null}`

**What health conditions does the user have?** (after erasure)
- 1. **F7** — `{"final":0.16841290426984426,"reranker":0.15310275412214722,"semantic":0.665276825428009,"keyword":0.6000000238418579}`
- 2. **F6** — `{"final":0.0009055125554876274,"reranker":0.0008231938874220299,"semantic":0.557671844959259,"keyword":0.20000000298023224}`
- 3. **F5** — `{"final":0.00015614039599330461,"reranker":0.0001419459275107752,"semantic":0.4578988254070282,"keyword":null}`

### Config A, run 2

**What health conditions does the user have?**
- 1. **F3** — `{"final":1.0745145265470475,"reranker":0.9768314422360441,"semantic":0.6809174025332156,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":1.0703442461841972,"reranker":0.9730402780584295,"semantic":0.6035784842716755,"keyword":0.4000000059604645}`
- 3. **F2** — `{"final":0.0003294234027507589,"reranker":0.00029947583738063077,"semantic":0.5006334334800673,"keyword":0.10000000149011612}`
- 4. **F1** — `{"final":0.0002988043132014135,"reranker":0.0002716402998746312,"semantic":0.5941398497903269,"keyword":0.10000000149011612}`

**Does Artur have diabetes?**
- 1. **F3** — `{"final":0.16084343654138958,"reranker":0.14622131414411746,"semantic":0.6626930434314326,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.006266494929282622,"reranker":0.005696813891447568,"semantic":0.5725527747006888,"keyword":0.20000000298023224}`
- 3. **F1** — `{"final":1.1961162568818939e-05,"reranker":1.0873784763073448e-05,"semantic":0.4570990477263368,"keyword":null}`
- 4. **F2** — `{"final":7.714897081530709e-06,"reranker":7.013543194581951e-06,"semantic":0.40525658146311605,"keyword":null}`

**Does Artur have any allergies?**
- 1. **F3** — `{"final":0.00028275531825505473,"reranker":0.0002570503038131061,"semantic":0.469896036097767,"keyword":null}`
- 2. **F1** — `{"final":3.0128420467010486e-05,"reranker":2.7389474695815392e-05,"semantic":0.5133069447692151,"keyword":null}`
- 3. **F4** — `{"final":2.2392837437644768e-05,"reranker":2.0357126090876576e-05,"semantic":0.47058186110366973,"keyword":null}`
- 4. **F2** — `{"final":7.18038784747574e-06,"reranker":6.527625683859541e-06,"semantic":0.3708943095003727,"keyword":null}`

**What should we avoid serving Artur?**
- 1. **F1** — `{"final":0.0023996471718368334,"reranker":0.0021814975525597893,"semantic":0.6701269942446462,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.000335582288819342,"reranker":0.00030507482530501987,"semantic":0.5585503245264187,"keyword":0.10000000149011612}`
- 3. **F3** — `{"final":1.9584139651726785e-05,"reranker":1.7803764328623595e-05,"semantic":0.49578101970723654,"keyword":null}`
- 4. **F2** — `{"final":7.0944674385162186e-06,"reranker":6.449516218666247e-06,"semantic":0.42861213428270095,"keyword":null}`

**What do we know about Artur's mom?**
- 1. **F3** — `{"final":0.003629385430627459,"reranker":0.0032994414885724782,"semantic":0.573693948200165,"keyword":null}`
- 2. **F4** — `{"final":0.00013978064853610106,"reranker":0.00012707332409163453,"semantic":0.48072931055601387,"keyword":null}`
- 3. **F2** — `{"final":3.892244683863613e-05,"reranker":3.5384044596759925e-05,"semantic":0.5399937790630396,"keyword":null}`
- 4. **F1** — `{"final":3.4940376347381586e-06,"reranker":3.1763980307530115e-06,"semantic":0.33982141851314474,"keyword":null}`

**What should we avoid serving Artur?** (after correction)
- 1. **F6** — `{"final":0.009849964118177955,"reranker":0.008892872619508985,"semantic":0.4856596606183491,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.0003355822706704662,"reranker":0.00030507482530501987,"semantic":0.5585503245264187,"keyword":0.10000000149011612}`
- 3. **F5** — `{"final":0.0001099401164255251,"reranker":9.994556575143227e-05,"semantic":0.5017711667623128,"keyword":null}`
- 4. **F3** — `{"final":1.9584138592582337e-05,"reranker":1.7803764328623595e-05,"semantic":0.49578101970723654,"keyword":null}`
- 5. **F2** — `{"final":7.094467054835039e-06,"reranker":6.449516218666247e-06,"semantic":0.42861213428270095,"keyword":null}`

**What do we know about Artur's mom?** (after erasure)
- 1. **F8** — `{"final":0.00036420605752390995,"reranker":0.000331096445013235,"semantic":0.5157197713851929,"keyword":null}`
- 2. **F7** — `{"final":0.0002733773943135595,"reranker":0.00024852492575101856,"semantic":0.5004972517194011,"keyword":null}`
- 3. **F5** — `{"final":6.716517767017944e-06,"reranker":6.105926107363182e-06,"semantic":0.37013883501705047,"keyword":null}`
- 4. **F10** — `{"final":5.364900132121827e-06,"reranker":4.8771826289179725e-06,"semantic":0.3702124577887338,"keyword":null}`

**What health conditions does the user have?** (after erasure)
- 1. **F8** — `{"final":0.168413014690679,"reranker":0.15310275412214722,"semantic":0.665276825428009,"keyword":0.6000000238418579}`
- 2. **F7** — `{"final":0.14655378250798906,"reranker":0.13323072311366405,"semantic":0.6772296025020134,"keyword":0.20000000298023224}`
- 3. **F5** — `{"final":0.0005739275579578209,"reranker":0.0005217523994556061,"semantic":0.6171515171871044,"keyword":0.30000001192092896}`
- 4. **F10** — `{"final":0.00026016798954232265,"reranker":0.00023651638769230164,"semantic":0.6134130128272194,"keyword":0.10000000149011612}`

### Config A, run 3

**What health conditions does the user have?**
- 1. **F4** — `{"final":1.0863262712019617,"reranker":0.9875693911476994,"semantic":0.602075833144064,"keyword":0.5}`
- 2. **F2** — `{"final":1.0745145280413122,"reranker":0.9768314422360441,"semantic":0.6809174025332156,"keyword":0.10000000149011612}`
- 3. **F1** — `{"final":0.0006206276023925099,"reranker":0.0005642069419402629,"semantic":0.5677754878997803,"keyword":0.10000000149011612}`
- 4. **F3** — `{"final":0.0003294234032088688,"reranker":0.00029947583738063077,"semantic":0.5006334334800673,"keyword":0.10000000149011612}`

**Does Artur have diabetes?**
- 1. **F2** — `{"final":0.1608434367559931,"reranker":0.14622131414411746,"semantic":0.6626930434314326,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.02487074720065573,"reranker":0.022609771419787254,"semantic":0.5851048405499711,"keyword":0.30000001192092896}`
- 3. **F1** — `{"final":1.8834829925910343e-05,"reranker":1.712257359699163e-05,"semantic":0.4841654896736145,"keyword":null}`
- 4. **F3** — `{"final":7.714897091824223e-06,"reranker":7.013543194581951e-06,"semantic":0.40525658146311605,"keyword":null}`

**Does Artur have any allergies?**
- 1. **F2** — `{"final":0.0002827553186193919,"reranker":0.0002570503038131061,"semantic":0.469896036097767,"keyword":null}`
- 2. **F1** — `{"final":3.287869578637321e-05,"reranker":2.9889725088574538e-05,"semantic":0.4878515615640244,"keyword":null}`
- 3. **F4** — `{"final":3.113559372736006e-05,"reranker":2.830508676582134e-05,"semantic":0.4674217283050712,"keyword":null}`
- 4. **F3** — `{"final":7.180387856727845e-06,"reranker":6.527625683859541e-06,"semantic":0.3708943095003727,"keyword":null}`

**What should we avoid serving Artur?**
- 1. **F1** — `{"final":0.0050546650239847194,"reranker":0.004595150276518381,"semantic":0.6472458067839422,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.0005056419128439952,"reranker":0.0004596744917020622,"semantic":0.5563855269802698,"keyword":0.20000000298023224}`
- 3. **F2** — `{"final":1.95841396759161e-05,"reranker":1.7803764328623595e-05,"semantic":0.49578101970723654,"keyword":null}`
- 4. **F3** — `{"final":7.094467447278938e-06,"reranker":6.449516218666247e-06,"semantic":0.42861213428270095,"keyword":null}`

**What do we know about Artur's mom?**
- 1. **F2** — `{"final":0.003629385434872874,"reranker":0.0032994414885724782,"semantic":0.573693948200165,"keyword":null}`
- 2. **F4** — `{"final":0.00023496108962024818,"reranker":0.00021360100248498333,"semantic":0.49528194949871174,"keyword":null}`
- 3. **F3** — `{"final":3.892244688416503e-05,"reranker":3.5384044596759925e-05,"semantic":0.5399937790630396,"keyword":null}`
- 4. **F1** — `{"final":4.871866266449354e-06,"reranker":4.428969580317593e-06,"semantic":0.34832295775413513,"keyword":null}`

**What should we avoid serving Artur?** (after correction)
- 1. **F1** — `{"final":0.005054664771188099,"reranker":0.004595150276518381,"semantic":0.6472458067839422,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":0.0005056418875555605,"reranker":0.0004596744917020622,"semantic":0.5563855269802698,"keyword":0.20000000298023224}`
- 3. **F5** — `{"final":6.087023623865241e-05,"reranker":5.533658113853612e-05,"semantic":0.41028649684352014,"keyword":null}`
- 4. **F6** — `{"final":5.213077143495655e-05,"reranker":4.7391612741814096e-05,"semantic":0.43129033669348826,"keyword":null}`
- 5. **F2** — `{"final":1.9584138696463596e-05,"reranker":1.7803764328623595e-05,"semantic":0.49578101970723654,"keyword":null}`
- 6. **F3** — `{"final":7.094467092466624e-06,"reranker":6.449516218666247e-06,"semantic":0.42861213428270095,"keyword":null}`

**What do we know about Artur's mom?** (after erasure)
- 1. **F7** — `{"final":0.0004957812292709921,"reranker":0.0004507102488155605,"semantic":0.504225104795391,"keyword":null}`
- 2. **F8** — `{"final":0.00036420605687866454,"reranker":0.000331096445013235,"semantic":0.5157197713851929,"keyword":null}`
- 3. **F6** — `{"final":1.7468332653295026e-05,"reranker":1.5880304623436566e-05,"semantic":0.4112550914287567,"keyword":null}`
- 4. **F5** — `{"final":1.7414308466523496e-05,"reranker":1.5831191719532514e-05,"semantic":0.39090263843536377,"keyword":null}`

**What health conditions does the user have?** (after erasure)
- 1. **F7** — `{"final":0.41604331641102293,"reranker":0.37822123076508457,"semantic":0.6509878247387525,"keyword":0.20000000298023224}`
- 2. **F8** — `{"final":0.16841301438258593,"reranker":0.15310275412214722,"semantic":0.665276825428009,"keyword":0.6000000238418579}`
- 3. **F6** — `{"final":0.0009055131497448367,"reranker":0.0008231938874220299,"semantic":0.557671844959259,"keyword":0.20000000298023224}`
- 4. **F5** — `{"final":0.0001561404984629561,"reranker":0.0001419459275107752,"semantic":0.4578988254070282,"keyword":null}`

### Config B, run 1

**What health conditions does the user have?**
- 1. **F2** — `{"final":0.9412602071583107,"reranker":0.8556911215081539,"semantic":0.6707367500882375,"keyword":0.4000000059604645}`
- 2. **F1** — `{"final":0.0006196913216675479,"reranker":0.0005633557627989865,"semantic":0.5637883543968201,"keyword":0.5}`

**Does Artur have diabetes?**
- 1. **F2** — `{"final":0.01897341980897828,"reranker":0.017248563953835346,"semantic":0.632432360423576,"keyword":0.20000000298023224}`
- 2. **F1** — `{"final":8.940385101251483e-06,"reranker":8.127623050273207e-06,"semantic":0.48096492886543274,"keyword":null}`

**Does Artur have any allergies?**
- 1. **F2** — `{"final":3.171130213035606e-05,"reranker":2.8828457313478077e-05,"semantic":0.4533416819565035,"keyword":null}`
- 2. **F1** — `{"final":1.3270401243769679e-05,"reranker":1.2064001477897953e-05,"semantic":0.4697233772607625,"keyword":null}`

**What should we avoid serving Artur?**
- 1. **F1** — `{"final":0.00047445733961347044,"reranker":0.00043132486675494106,"semantic":0.571603051232932,"keyword":0.10000000149011612}`
- 2. **F2** — `{"final":1.4006853699577128e-05,"reranker":1.2733503734806277e-05,"semantic":0.4610261504924811,"keyword":null}`

**What do we know about Artur's mom?**
- 1. **F2** — `{"final":0.0008930155021608751,"reranker":0.000811832298658375,"semantic":0.5460740490577835,"keyword":null}`
- 2. **F1** — `{"final":3.328824072145502e-05,"reranker":3.0262037911146667e-05,"semantic":0.48142942786216736,"keyword":null}`

**What health conditions does the user have?** (filtered)
- 1. **F1** — `{"final":0.0006196913206266509,"reranker":0.0005633557627989865,"semantic":0.5637883543968201,"keyword":0.5}`

**Does Artur have diabetes?** (filtered)
- 1. **F1** — `{"final":8.940385086308113e-06,"reranker":8.127623050273207e-06,"semantic":0.48096492886543274,"keyword":null}`

**What should we avoid serving Artur?** (after correction)
- 1. **F1** — `{"final":0.0004744573313122804,"reranker":0.00043132486675494106,"semantic":0.571603051232932,"keyword":0.10000000149011612}`
- 2. **F3** — `{"final":8.349682836256038e-05,"reranker":7.590620884485722e-05,"semantic":0.5038484330358025,"keyword":null}`
- 3. **F2** — `{"final":1.4006853454510722e-05,"reranker":1.2733503734806277e-05,"semantic":0.4610261504924811,"keyword":null}`

**What do we know about Artur's mom?** (after erasure)
- 1. **F4** — `{"final":0.00044663329367045497,"reranker":0.00040603027491233805,"semantic":0.5092501943856602,"keyword":null}`
- 2. **F3** — `{"final":1.4622628939874219e-05,"reranker":1.3293299515817822e-05,"semantic":0.39555424451828003,"keyword":null}`

**What health conditions does the user have?** (after erasure)
- 1. **F4** — `{"final":0.16978393816854045,"reranker":0.15434903776722259,"semantic":0.6721049351754758,"keyword":0.800000011920929}`
- 2. **F3** — `{"final":0.0004653677756191651,"reranker":0.0004230616296000936,"semantic":0.6065613031387329,"keyword":0.4000000059604645}`

### Config B, run 2

**What health conditions does the user have?**
- 1. **F2** — `{"final":0.9249681943734843,"reranker":0.8408801999604271,"semantic":0.6677540739701415,"keyword":0.4000000059604645}`
- 2. **F3** — `{"final":0.0004739411144526852,"reranker":0.0004308555705348941,"semantic":0.5434601306915283,"keyword":0.5}`
- 3. **F1** — `{"final":0.0004146618327078789,"reranker":0.0003769653128661685,"semantic":0.6075758337974548,"keyword":0.4000000059604645}`

**Does Artur have diabetes?**
- 1. **F2** — `{"final":0.01817093595582423,"reranker":0.016519033149419483,"semantic":0.6316695401570067,"keyword":0.20000000298023224}`
- 2. **F1** — `{"final":1.3908884479496127e-05,"reranker":1.2644440789047624e-05,"semantic":0.48868662118911743,"keyword":null}`
- 3. **F3** — `{"final":8.46980652690198e-06,"reranker":7.699824331298924e-06,"semantic":0.43916523456573486,"keyword":null}`

**Does Artur have any allergies?**
- 1. **F2** — `{"final":2.852900225089501e-05,"reranker":2.593545732715941e-05,"semantic":0.45717348541258906,"keyword":null}`
- 2. **F1** — `{"final":2.39168306299208e-05,"reranker":2.1742573915215966e-05,"semantic":0.5063157670121506,"keyword":null}`
- 3. **F3** — `{"final":8.158209605511998e-06,"reranker":7.416554397563601e-06,"semantic":0.3844685096182243,"keyword":null}`

**What should we avoid serving Artur?**
- 1. **F1** — `{"final":0.0034150697328163187,"reranker":0.003104608936945088,"semantic":0.6129166349272015,"keyword":0.10000000149011612}`
- 2. **F2** — `{"final":1.203336909893081e-05,"reranker":1.093942676755957e-05,"semantic":0.4635970476033995,"keyword":null}`
- 3. **F3** — `{"final":7.242621085611077e-06,"reranker":6.584201176280123e-06,"semantic":0.4724251958817043,"keyword":null}`

**What do we know about Artur's mom?**
- 1. **F2** — `{"final":0.0023563023763292267,"reranker":0.0021420931317018884,"semantic":0.55222894407001,"keyword":0.30000001192092896}`
- 2. **F3** — `{"final":0.0002681780225266357,"reranker":0.00024379820940288177,"semantic":0.5362737774848938,"keyword":0.30000001192092896}`
- 3. **F1** — `{"final":4.877831059864741e-06,"reranker":4.434392001341372e-06,"semantic":0.38721907138824463,"keyword":null}`

**What health conditions does the user have?** (filtered)
- 1. **F3** — `{"final":0.000473941113618378,"reranker":0.0004308555705348941,"semantic":0.5434601306915283,"keyword":0.5}`
- 2. **F1** — `{"final":0.0004146618319779246,"reranker":0.0003769653128661685,"semantic":0.6075758337974548,"keyword":0.4000000059604645}`

**Does Artur have diabetes?** (filtered)
- 1. **F1** — `{"final":1.3908884454804427e-05,"reranker":1.2644440789047624e-05,"semantic":0.48868662118911743,"keyword":null}`
- 2. **F3** — `{"final":8.469806511865984e-06,"reranker":7.699824331298924e-06,"semantic":0.43916523456573486,"keyword":null}`

**What should we avoid serving Artur?** (after correction)
- 1. **F1** — `{"final":0.003415069675708093,"reranker":0.003104608936945088,"semantic":0.6129166349272015,"keyword":0.10000000149011612}`
- 2. **F4** — `{"final":8.349682843702867e-05,"reranker":7.590620884485722e-05,"semantic":0.5038484330358025,"keyword":null}`
- 3. **F2** — `{"final":1.2033368897703771e-05,"reranker":1.093942676755957e-05,"semantic":0.4635970476033995,"keyword":null}`
- 4. **F3** — `{"final":7.242620964496934e-06,"reranker":6.584201176280123e-06,"semantic":0.4724251958817043,"keyword":null}`

**What do we know about Artur's mom?** (after erasure)
- 1. **F5** — `{"final":0.00022206017873582112,"reranker":0.00020187289408880218,"semantic":0.48869788714063933,"keyword":null}`
- 2. **F4** — `{"final":1.462262892495947e-05,"reranker":1.3293299515817822e-05,"semantic":0.39555424451828003,"keyword":null}`

**What health conditions does the user have?** (after erasure)
- 1. **F5** — `{"final":0.27687672689686027,"reranker":0.2517061208626958,"semantic":0.6559317913096087,"keyword":0.699999988079071}`
- 2. **F4** — `{"final":0.00046536777510396783,"reranker":0.0004230616296000936,"semantic":0.6065613031387329,"keyword":0.4000000059604645}`

### Config B, run 3

**What health conditions does the user have?**
- 1. **F2** — `{"final":0.0006092898873977297,"reranker":0.0005538999175492864,"semantic":0.6526517868041992,"keyword":0.20000000298023224}`
- 2. **F3** — `{"final":0.0005465225861350717,"reranker":0.0004968387325602936,"semantic":0.5116904377937317,"keyword":0.20000000298023224}`
- 3. **F1** — `{"final":0.00018414477212009628,"reranker":0.0001674043443002217,"semantic":0.5550901293754578,"keyword":0.20000000298023224}`

**Does Artur have diabetes?**
- 1. **F3** — `{"final":0.000406658076615241,"reranker":0.00036968917401793936,"semantic":0.4277026355266571,"keyword":null}`
- 2. **F2** — `{"final":6.946256628916502e-05,"reranker":6.314778983087536e-05,"semantic":0.5449221134185791,"keyword":null}`
- 3. **F1** — `{"final":4.63119571181721e-05,"reranker":4.210178072620973e-05,"semantic":0.4909246563911438,"keyword":null}`

**Does Artur have any allergies?**
- 1. **F3** — `{"final":0.00028832658754265883,"reranker":0.0002621150892373676,"semantic":0.36336349089581144,"keyword":null}`
- 2. **F2** — `{"final":5.4494515856953545e-05,"reranker":4.9540470782479125e-05,"semantic":0.49015930412301123,"keyword":null}`
- 3. **F1** — `{"final":3.396627325538474e-05,"reranker":3.08784313657933e-05,"semantic":0.4638137264473797,"keyword":null}`

**What should we avoid serving Artur?**
- 1. **F1** — `{"final":0.001655196789588043,"reranker":0.0015047244101751634,"semantic":0.49087774862316613,"keyword":null}`
- 2. **F3** — `{"final":0.0001446488102716046,"reranker":0.0001314989233381421,"semantic":0.41660226385566723,"keyword":null}`
- 3. **F2** — `{"final":3.129380987937438e-05,"reranker":2.8448919132636733e-05,"semantic":0.4778416779230059,"keyword":null}`

**What do we know about Artur's mom?**
- 1. **F3** — `{"final":0.00019230491621339947,"reranker":0.0001748226577145695,"semantic":0.38787779211997986,"keyword":null}`
- 2. **F2** — `{"final":2.8060073769051058e-05,"reranker":2.550915893510449e-05,"semantic":0.48803234100341797,"keyword":null}`
- 3. **F1** — `{"final":1.5574454766847234e-05,"reranker":1.4158595776408467e-05,"semantic":0.4090728163719177,"keyword":null}`

**What health conditions does the user have?** (filtered)
- 1. **F3** — `{"final":0.0005465225849474073,"reranker":0.0004968387325602936,"semantic":0.5116904377937317,"keyword":0.20000000298023224}`
- 2. **F1** — `{"final":0.00018414477171992577,"reranker":0.0001674043443002217,"semantic":0.5550901293754578,"keyword":0.20000000298023224}`

**Does Artur have diabetes?** (filtered)
- 1. **F3** — `{"final":0.0004066580757462909,"reranker":0.00036968917401793936,"semantic":0.4277026355266571,"keyword":null}`
- 2. **F1** — `{"final":4.631195701921235e-05,"reranker":4.210178072620973e-05,"semantic":0.4909246563911438,"keyword":null}`

**What should we avoid serving Artur?** (after correction)
- 1. **F1** — `{"final":0.0016551967601822466,"reranker":0.0015047244101751634,"semantic":0.49087774862316613,"keyword":null}`
- 2. **F3** — `{"final":0.0001446488077018114,"reranker":0.0001314989233381421,"semantic":0.41660226385566723,"keyword":null}`
- 3. **F4** — `{"final":8.349682836368877e-05,"reranker":7.590620884485722e-05,"semantic":0.5038484330358025,"keyword":null}`
- 4. **F2** — `{"final":3.129380932341668e-05,"reranker":2.8448919132636733e-05,"semantic":0.4778416779230059,"keyword":null}`

**What do we know about Artur's mom?** (after erasure)
- 1. **F5** — `{"final":0.001011951977973044,"reranker":0.000919956364729277,"semantic":0.5051069410177156,"keyword":0.30000001192092896}`
- 2. **F4** — `{"final":1.4622628889477878e-05,"reranker":1.3293299515817822e-05,"semantic":0.39555424451828003,"keyword":null}`

**What health conditions does the user have?** (after erasure)
- 1. **F5** — `{"final":0.1740526954499301,"reranker":0.1582297268279585,"semantic":0.6723165712450916,"keyword":0.9000000357627869}`
- 2. **F4** — `{"final":0.0004653677739925698,"reranker":0.0004230616296000936,"semantic":0.6065613031387329,"keyword":0.4000000059604645}`

## Observations

The diabetes claim was attributed in the stored text to the mother, but unfiltered questions about Artur still retrieved it. The Config B strict subject-tag filter excluded the family-member-tagged diabetes fact in these trials; it did not exclude all facts mentioning the mother. Original and corrected cinnamon world facts coexisted in all six trials. Document deletion removed the original facts from the immediate memory listings but did not remove the original conversation from the observed LLM traces. One default observation incorrectly claimed the health information had not been retained while its source fact was still present.
