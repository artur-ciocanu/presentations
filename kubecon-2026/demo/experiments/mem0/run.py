#!/usr/bin/env python3
"""Run three independent Mem0 trials. Credentials are read from stage/.env only."""

import contextlib
import inspect
import io
import json
import logging
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGE_ENV = ROOT.parents[1] / "stage" / ".env"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
QUERIES = [
    "What health conditions does the user have?",
    "Does Artur have diabetes?",
    "Does Artur have any allergies?",
    "What should we avoid serving Artur?",
    "What do we know about Artur's mom?",
]
INITIAL = [
    {"role": "user", "content": "I'm booking a long flight for me and my mom. She has diabetes. I want to avoid anything with cinnamon."},
    {"role": "assistant", "content": "Got it. I'll look at the in-flight meal options for both of you."},
]
CORRECTION = [
    {"role": "user", "content": "Actually, cinnamon is fine now."},
    {"role": "assistant", "content": "Thanks, noted."},
]


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    # Avoid third-party HTTP logging, which could contain credentials or URLs.
    logging.disable(logging.CRITICAL)
    os.environ["MEM0_TELEMETRY"] = "false"
    os.environ["HF_HOME"] = str(ROOT / "model_cache" / "huggingface")
    os.environ["TORCH_HOME"] = str(ROOT / "model_cache" / "torch")
    os.environ["MEM0_DIR"] = str(ROOT / "vector_store" / "mem0_internal")
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    # A configured OpenRouter key takes precedence in Mem0's OpenAI provider.
    os.environ.pop("OPENROUTER_API_KEY", None)

    from dotenv import dotenv_values

    values = dotenv_values(STAGE_ENV, interpolate=False)
    base_url, api_key, model = (values.get(k) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
    secrets = [value for value in (api_key, base_url) if value]

    def safe_error(exc):
        text = f"{type(exc).__name__}: {exc}"
        for value in secrets:
            text = text.replace(value, "[REDACTED]")
        return text

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    artifact = ROOT / "artifacts" / f"{stamp}.json"
    store_root = ROOT / "vector_store" / f"{stamp}-{uuid.uuid4().hex[:8]}"
    data = {
        "started_at": now(),
        "versions": {"mem0ai": version("mem0ai"), "python": platform.python_version(),
                     "sentence-transformers": version("sentence-transformers"), "embedder_model": MODEL},
        "llm_model": model,
        "config": {
            "llm": {"provider": "openai", "model": model, "openai_base_url": "[read from stage/.env]", "api_key": "[read from stage/.env]", "is_reasoning_model": True},
            "llm_config_change": "After the default provider sent max_tokens and the endpoint rejected it, set is_reasoning_model=True to omit max_tokens and default sampling parameters; prompts unchanged. See earlier artifact for errors.",
            "embedder": {"provider": "huggingface", "model": MODEL, "embedding_dims": 384},
            "vector_store": {"provider": "qdrant", "embedding_model_dims": 384, "path": "separate new on-disk directory per run"},
            "history_db_path": "separate new SQLite file per run",
            "prompts": "Mem0 defaults; no custom prompt or instructions",
            "telemetry": "disabled",
        },
        "inputs": {"initial": INITIAL, "correction": CORRECTION, "queries": QUERIES, "user_id": "artur"},
        "runs": [],
    }

    def save():
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")

    save()
    if not all((base_url, api_key, model)):
        data["fatal_error"] = "Missing one or more required LLM_BASE_URL, LLM_API_KEY, LLM_MODEL in stage/.env"
        data["finished_at"] = now()
        save()
        print(f"Experiment failed; details saved in {artifact}")
        return 1

    # Capture third-party output so credentials cannot leak through diagnostics.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from mem0 import Memory
        get_all_uses_filters = "user_id" not in inspect.signature(Memory.get_all).parameters
        search_uses_filters = "user_id" not in inspect.signature(Memory.search).parameters
        data["config"]["scope_api"] = {"get_all": "filters" if get_all_uses_filters else "user_id", "search": "filters" if search_uses_filters else "user_id"}
        for number in range(1, 4):
            run = {"run": number, "started_at": now(), "operations": {}}
            data["runs"].append(run)
            run_dir = store_root / f"run-{number}"
            run_dir.mkdir(parents=True, exist_ok=False)
            config = {
                "llm": {"provider": "openai", "config": {"model": model, "api_key": api_key, "openai_base_url": base_url, "is_reasoning_model": True}},
                "embedder": {"provider": "huggingface", "config": {"model": MODEL, "embedding_dims": 384}},
                "vector_store": {"provider": "qdrant", "config": {"path": str(run_dir / "qdrant"), "embedding_model_dims": 384}},
                "history_db_path": str(run_dir / "history.db"),
            }

            def operation(name, call):
                try:
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        result = call()
                    run["operations"][name] = {"timestamp": now(), "output": result}
                    save()
                    return result
                except Exception as exc:
                    run["operations"][name] = {"timestamp": now(), "error": safe_error(exc)}
                    save()
                    return None

            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    memory = Memory.from_config(config)
                run["operations"]["initialize"] = {"timestamp": now(), "output": "ok"}
            except Exception as exc:
                memory = None
                run["operations"]["initialize"] = {"timestamp": now(), "error": safe_error(exc)}
            save()
            if memory is not None:
                def get_all():
                    return memory.get_all(**({"filters": {"user_id": "artur"}} if get_all_uses_filters else {"user_id": "artur"}))
                def search(query):
                    return memory.search(query, **({"filters": {"user_id": "artur"}} if search_uses_filters else {"user_id": "artur"}))
                operation("empty_store_get_all", get_all)
                operation("initial_add", lambda: memory.add(INITIAL, user_id="artur"))
                before = operation("initial_get_all", get_all)
                for index, query in enumerate(QUERIES, 1):
                    operation(f"search_{index}", lambda query=query: search(query))
                correction = operation("correction_add", lambda: memory.add(CORRECTION, user_id="artur"))
                after = operation("correction_get_all", get_all)
                before_by_id = {item["id"]: item for item in (before or {}).get("results", [])}
                after_by_id = {item["id"]: item for item in (after or {}).get("results", [])}
                changed = {key for key in before_by_id.keys() | after_by_id.keys() if before_by_id.get(key) != after_by_id.get(key)}
                changed.update(item["id"] for item in (correction or {}).get("results", []) if item.get("id") and item.get("event") in ("ADD", "UPDATE", "DELETE"))
                for memory_id in sorted(changed):
                    operation(f"history_{memory_id}", lambda memory_id=memory_id: memory.history(memory_id))
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    if hasattr(memory.vector_store, "client"):
                        memory.vector_store.client.close()
            run["finished_at"] = now()
            save()
            print(f"Run {number} finished; results saved.", flush=True)
    except Exception as exc:
        data["fatal_error"] = safe_error(exc)
    data["finished_at"] = now()
    save()
    print(f"Artifact: {artifact}")
    return int("fatal_error" in data or any("error" in op for run in data["runs"] for op in run["operations"].values()))


if __name__ == "__main__":
    sys.exit(main())
