#!/usr/bin/env python3
"""Run independent Hindsight trials against this directory's isolated server.

Start server.py separately. This client refuses to delete a pre-existing bank;
between trials it deletes only the bank this invocation created.
"""
import json
import platform
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from io import StringIO
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
BASE = "/v1/default/banks/artur"
QUERIES = [
    "What health conditions does the user have?", "Does Artur have diabetes?",
    "Does Artur have any allergies?", "What should we avoid serving Artur?",
    "What do we know about Artur's mom?",
]
DOCUMENTS = {
    "initial": "user: I'm booking a long flight for me and my mom. She has diabetes. I want to avoid anything with cinnamon.\nassistant: Got it. I'll look at the in-flight meal options for both of you.",
    "correction": "user: Actually, cinnamon is fine now.\nassistant: Thanks, noted.",
    "privacy": "user: Please don't keep anything about my mom's health.\nassistant: Understood.",
}
GUARDRAILS = {
    "retain_mission": "Record user-declared facts with who each fact is about. Do not promote assistant suggestions or statements to facts about the user.",
    "enable_observations": False,
    "entity_labels": [
        {"key": "subject", "description": "Who the fact is about; distinguish the user from a family member.", "type": "value", "optional": True, "tag": True,
         "values": [{"value": "user", "description": "The user speaking"}, {"value": "family_member", "description": "A family member of the user"}]},
        {"key": "category", "description": "The category of the fact.", "type": "multi-values", "tag": True,
         "values": [{"value": "health", "description": "Health conditions or health information"}, {"value": "food_preference", "description": "Food preferences and restrictions"}]},
    ],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    keys = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    with (ROOT.parents[1] / "stage" / ".env").open() as source:
        selected = [line for line in source if line.lstrip().removeprefix("export ").split("=", 1)[0].strip() in keys]
    values = dotenv_values(stream=StringIO("\n".join(selected)), interpolate=False)
    secrets = [values.get(k) for k in ("LLM_API_KEY", "LLM_BASE_URL") if values.get(k)]
    def redact(value):
        if isinstance(value, str):
            for secret in secrets:
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        return value
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = ROOT / "artifacts" / f"{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"started_at": now(), "versions": {p: version(p) for p in ("hindsight-api", "hindsight-client", "hindsight-api-slim")},
            "python": platform.python_version(), "llm_model": values.get("LLM_MODEL"), "provider": "openai-responses",
            "embedder": "BAAI/bge-small-en-v1.5 (local default)", "reranker": "hindsight-ai/hs-rerank-1 (local default)",
            "server_settings": {"host": "127.0.0.1", "port": 8890, "database_url": "pg0://kubecon-experiment:55434", "environment": {"HOME": ".data/home", "PG0_HOME": ".data/pg0", "XDG_CACHE_HOME": ".cache", "HF_HOME": ".cache/huggingface", "TORCH_HOME": ".cache/torch", "HINDSIGHT_API_LLM_PROVIDER": "openai-responses", "HINDSIGHT_API_LLM_BASE_URL": "[read from stage/.env]", "HINDSIGHT_API_LLM_API_KEY": "[read from stage/.env]", "HINDSIGHT_API_LLM_MODEL": values.get("LLM_MODEL")}, "other_changes": [{"setting": "HF_HUB_DISABLE_XET", "value": "1", "reason": "Default model weight downloads left zero-byte incomplete files for several minutes; direct HTTPS range requests succeeded. Restarted to use the documented non-Xet download transport; model IDs unchanged."}], "model_download_workaround": "Downloaded both default model weight files via parallel HTTPS ranges; verified against Hugging Face LFS SHA-256 and installed the reranker blob into the isolated cache, then restarted the server. Embedder blob was already present and verified."},
            "inputs": {"documents": DOCUMENTS, "queries": QUERIES}, "guardrail_config": GUARDRAILS, "runs": []}

    def save():
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    save()
    client = httpx.Client(base_url="http://127.0.0.1:8890", timeout=240, trust_env=False)
    def request(method, url, body=None):
        try:
            response = client.request(method, url, json=body)
            try:
                result = redact(response.json())
            except ValueError:
                result = redact(response.text)
            return {"at": now(), "method": method, "path": url, "request": body, "status": response.status_code, "output": result}
        except Exception as exc:
            return {"at": now(), "method": method, "path": url, "request": body, "error": redact(f"{type(exc).__name__}: {exc}")}

    probe = request("GET", BASE + "/config")
    data["preflight"] = probe
    save()
    if probe.get("status") != 404:
        data["fatal_error"] = "Bank artur already exists or server unavailable; refusing to delete unowned data."
        save()
        print(f"Preflight failed; see {path}", flush=True)
        return 1

    for config in ("A", "B"):
        for number in range(1, 4):
            run = {"config": config, "run": number, "started_at": now(), "operations": {}}
            data["runs"].append(run)
            def op(name, method, url, body=None):
                result = request(method, url, body)
                run["operations"][name] = result
                save()
                return result
            def ok(result):
                return 200 <= result.get("status", 0) < 300
            def object_output(result):
                value = result.get("output")
                return value if isinstance(value, dict) else {}
            def settle(stage):
                # Consolidation is asynchronous even after synchronous retain.
                # Record every status read, and bound the wait rather than
                # pretending an unfinished job has already produced observations.
                if config != "A":
                    return
                time.sleep(2)
                for attempt in range(30):
                    result = op(f"{stage}_settle_{attempt}", "GET", BASE + "/operations?limit=100")
                    items = object_output(result).get("operations", [])
                    if not any(item.get("status") in ("pending", "processing") for item in items):
                        break
                    time.sleep(2)
            def snap(stage):
                if stage != "empty":
                    settle(stage)
                memories = op(stage + "_memories", "GET", BASE + "/memories/list?limit=100")
                for item in object_output(memories).get("items", []):
                    mid = item.get("id")
                    if mid:
                        op(stage + "_memory_" + mid, "GET", BASE + "/memories/" + quote(str(mid), safe=""))
                        if item.get("fact_type") == "observation":
                            op(stage + "_observation_history_" + mid, "GET", BASE + "/memories/" + quote(str(mid), safe="") + "/history")
                op(stage + "_entities", "GET", BASE + "/entities?limit=100")
                op(stage + "_documents", "GET", BASE + "/documents?limit=100")
                op(stage + "_operations", "GET", BASE + "/operations?limit=100")
                op(stage + "_stats", "GET", BASE + "/stats")
                if stage in ("privacy", "erased"):
                    op(stage + "_llm_requests", "GET", BASE + "/llm-requests?limit=500")
                    audit = op(stage + "_audit_logs", "GET", BASE + "/audit-logs?limit=500")
                    for entry in object_output(audit).get("items", []):
                        if entry.get("id"):
                            op(stage + "_audit_" + str(entry["id"]), "GET", BASE + "/audit-logs/" + quote(str(entry["id"]), safe=""))
                for doc in DOCUMENTS:
                    op(stage + "_document_" + doc, "GET", BASE + "/documents/" + doc)
                    op(stage + "_history_" + doc, "GET", BASE + "/documents/" + doc + "/history")
                return memories
            def retain(doc):
                item = {"content": DOCUMENTS[doc], "document_id": doc}
                if config == "B":
                    item["tags"] = ["task:flight-booking"]
                return op("retain_" + doc, "POST", BASE + "/memories", {"items": [item], "async": False})
            def recall(name, query, filtered=False):
                body = {"query": query}
                if filtered:
                    body.update({"tags": ["subject:user"], "tags_match": "any_strict"})
                return op(name, "POST", BASE + "/memories/recall", body)
            created = op("create_bank", "PUT", BASE, {})
            if not ok(created):
                data["fatal_error"] = "Bank creation failed; experiment stopped."
                save()
                return 1
            if config == "B" and not ok(op("set_guardrails", "PATCH", BASE + "/config", {"updates": GUARDRAILS})):
                data["fatal_error"] = "Guardrail configuration failed; experiment stopped."
                save()
                return 1
            op("bank_config", "GET", BASE + "/config")
            snap("empty")
            if not ok(retain("initial")):
                data["fatal_error"] = "Initial synchronous retain failed; experiment stopped."
                save()
                return 1
            snap("initial")
            for idx, query in enumerate(QUERIES, 1):
                recall(f"recall_{idx}", query)
            if config == "B":
                for idx in (0, 1):
                    recall(f"filtered_recall_{idx+1}", QUERIES[idx], True)
            retain("correction")
            snap("corrected")
            recall("recall_after_correction", QUERIES[3])
            retain("privacy")
            snap("privacy")
            # Deleting the source document also removes its raw text/chunks; merely
            # deleting an extracted fact would leave the original health statement.
            op("erase_initial_document", "DELETE", BASE + "/documents/initial")
            snap("erased")
            recall("recall_after_erasure_mom", QUERIES[4])
            recall("recall_after_erasure_health", QUERIES[0])
            run["finished_at"] = now()
            save()
            print(f"Completed config {config} run {number}; {path.name}", flush=True)
            if not (config == "B" and number == 3):
                deleted = op("delete_bank_for_next_fresh_run", "DELETE", BASE)
                if not ok(deleted):
                    data["fatal_error"] = "Could not delete the bank created by this invocation; stopped."
                    save()
                    return 1
    data["finished_at"] = now()
    save()
    print(f"Artifact: {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
