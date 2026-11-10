#!/usr/bin/env python3
"""Run the historical Letta V1 experiment against a native local server.

Run with .venv/bin/python. Credentials are read into this process only. The
loopback adapter forwards chat requests without altering them, and serves local
embeddings. It never writes credentials or the upstream URL to disk.
"""
import json
import io
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path

import httpx
from dotenv import dotenv_values
from fastembed import TextEmbedding
from pg0 import Pg0

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
HOME = ROOT / ".letta" / "home"
os.environ["HOME"] = str(HOME)
os.environ["HF_HOME"] = str(ROOT / ".cache" / "huggingface")
HOME.mkdir(parents=True, exist_ok=True)
CREDS = {}
with (ROOT / "../../stage/.env").open() as source:
    for line in source:
        name = line.strip().removeprefix("export ").split("=", 1)[0].strip()
        if name in {"LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"}:
            CREDS.update(dotenv_values(stream=io.StringIO(line), interpolate=False))
URL, KEY, MODEL = (CREDS[k] for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
if not all((URL, KEY, MODEL)):
    raise SystemExit("Missing required LLM_BASE_URL, LLM_API_KEY, or LLM_MODEL")
URL = URL.rstrip("/")
MESSAGES = [
    "I'm booking a long flight for me and my mom. She has diabetes. I want to avoid anything with cinnamon.",
    "Does Artur have diabetes?",
    "Does Artur have any allergies?",
    "What should we avoid serving Artur?",
    "Actually, cinnamon is fine now.",
    "Please don't keep anything about my mom's health.",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def redact(value):
    if isinstance(value, str):
        return value.replace(KEY, "[REDACTED]").replace(URL, "[REDACTED_UPSTREAM_URL]")
    if isinstance(value, list):
        return [redact(x) for x in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value


class Adapter(BaseHTTPRequestHandler):
    # Prevent the HTTP server from logging paths, headers, or request content.
    def log_message(self, *args):
        pass

    def respond(self, status, content, content_type="application/json"):
        content = content.replace(KEY.encode(), b"[REDACTED]").replace(URL.encode(), b"[REDACTED_UPSTREAM_URL]")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path.split("?")[0] == "/v1/models":
            data = {"object": "list", "data": [{"id": MODEL, "object": "model", "created": 0, "owned_by": "configured"}]}
            return self.respond(200, json.dumps(data).encode())
        self.respond(404, b'{"error":"unsupported adapter path"}')

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path.split("?")[0] == "/v1/embeddings":
            try:
                obj = json.loads(body)
                inputs = obj["input"]
                if isinstance(inputs, str):
                    inputs = [inputs]
                vectors = list(self.server.embedder.embed(inputs))
                data = [{"object": "embedding", "index": i, "embedding": v.tolist()} for i, v in enumerate(vectors)]
                result = {"object": "list", "data": data, "model": obj["model"], "usage": {"prompt_tokens": 0, "total_tokens": 0}}
                return self.respond(200, json.dumps(result).encode())
            except Exception as exc:
                return self.respond(500, json.dumps({"error": redact(str(exc))}).encode())
        if not self.path.startswith("/v1/"):
            return self.respond(404, b'{"error":"unsupported adapter path"}')
        try:
            if self.path.split("?")[0] == "/v1/chat/completions":
                # This endpoint requires the explicit setting for tool calls.
                # Do not change the prompt, messages, tools, or any other field.
                payload = json.loads(body)
                payload["reasoning_effort"] = "none"
                body = json.dumps(payload).encode()
            response = httpx.post(
                URL + self.path[3:], content=body,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "Accept": self.headers.get("Accept", "application/json")},
                timeout=300,
            )
            self.respond(response.status_code, response.content, response.headers.get("content-type", "application/json"))
        except Exception as exc:
            self.respond(502, json.dumps({"error": redact(str(exc))}).encode())


def main():
    started = datetime.now(timezone.utc)
    artifact = ROOT / "artifacts" / (started.strftime("%Y%m%dT%H%M%SZ") + ".json")
    artifact.parent.mkdir(exist_ok=True)
    result = {
        "started_at": started.isoformat(), "status": "running",
        "versions": {"letta_code_pypi": version("letta"), "letta_client": version("letta-client"), "fastembed": version("fastembed"), "pg0_embedded": version("pg0-embedded"), "python": sys.version},
        "server_version": "0.16.8",
        "llm_model": MODEL,
        "provider": {"type": "openai-compatible", "upstream": "LLM_BASE_URL from demo/stage/.env; forwarded by an in-memory loopback adapter", "credentials": "LLM_API_KEY read from demo/stage/.env in memory; Letta receives a dummy local key", "model_list": "adapter advertises the configured LLM_MODEL", "request_adjustment": "Set reasoning_effort=none on chat completions because the endpoint rejects function tools without it; prompt, messages and tools unchanged."},
        "embedding": {"provider": "local fastembed", "model": "BAAI/bge-small-en-v1.5", "dimensions": 384, "endpoint": "loopback OpenAI-compatible adapter"},
        "agent_setup": "Letta V1 default agent, system prompt, and base tools; human and persona are the package's empty DEFAULT_BLOCKS, supplied explicitly because the API creates no blocks when omitted.",
        "runs": [],
    }

    def save():
        artifact.write_text(json.dumps(redact(result), indent=2, ensure_ascii=False) + "\n")

    save()
    db_name = "letta_" + started.strftime("%Y%m%d%H%M%S")
    db_uri = f"postgresql+pg8000://postgres:postgres@127.0.0.1:55433/{db_name}"
    pg = Pg0(name="letta-experiment", port=55433, data_dir=str(ROOT / ".letta" / "postgres"))
    server = None
    adapter = None
    logs = deque(maxlen=400)
    try:
        if not pg.running:
            pg.start()
        pg.execute(f"CREATE DATABASE {db_name};")
        # Do not pass any inherited provider credentials to Letta.
        env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE") if k in os.environ}
        env.update({"HOME": str(HOME), "LETTA_DIR": str(ROOT / ".letta"), "LETTA_LOGGING_LETTA_LOG_PATH": str(ROOT / ".letta" / "Letta.log"), "TOOL_EXEC_DIR": str(ROOT / ".letta" / "tools"), "LETTA_PG_URI": db_uri, "OPENAI_API_KEY": "loopback-only", "NLTK_DATA": str(ROOT / ".cache" / "nltk")})
        init = subprocess.run([str(ROOT / ".server-venv/bin/python"), "-c", "from sqlalchemy import create_engine, text; from letta.settings import settings; e=create_engine(settings.letta_pg_uri); c=e.connect(); c.execute(text('CREATE EXTENSION IF NOT EXISTS vector')); c.commit(); c.close()"], env=env, text=True, capture_output=True, timeout=120)
        if init.returncode:
            raise RuntimeError("Database initialization failed: " + redact(init.stderr))
        migrations = ROOT / ".cache" / "letta-0.16.8"
        if not (migrations / "alembic.ini").exists():
            raise RuntimeError("Missing upstream 0.16.8 Alembic files in .cache/letta-0.16.8")
        init = subprocess.run([str(ROOT / ".server-venv/bin/alembic"), "upgrade", "head"], cwd=migrations, env=env, text=True, capture_output=True, timeout=180)
        if init.returncode:
            raise RuntimeError("Upstream database migrations failed: " + redact(init.stderr))
        embedder = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=str(ROOT / ".cache" / "fastembed"))
        probe_vector = next(embedder.embed(["embedding setup check"]))
        if len(probe_vector) != 384:
            raise RuntimeError("Unexpected embedding dimensions")
        adapter = ThreadingHTTPServer(("127.0.0.1", 0), Adapter)
        adapter.embedder = embedder
        threading.Thread(target=adapter.serve_forever, daemon=True).start()
        proxy = f"http://127.0.0.1:{adapter.server_port}/v1"
        env["OPENAI_BASE_URL"] = proxy
        server = subprocess.Popen([str(ROOT / ".server-venv/bin/letta"), "server", "--host", "127.0.0.1"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        def drain():
            for line in server.stdout:
                logs.append(redact(line))
        threading.Thread(target=drain, daemon=True).start()
        api = httpx.Client(base_url="http://127.0.0.1:8283", timeout=300, trust_env=False)
        for _ in range(120):
            if server.poll() is not None:
                raise RuntimeError("Letta server exited during startup:\n" + "".join(logs))
            try:
                if api.get("/v1/health/", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Letta server did not become ready in 120 seconds:\n" + "".join(logs))

        def request(method, path, **kwargs):
            response = api.request(method, path, **kwargs)
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            if response.is_error:
                raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {redact(payload)}")
            return redact(payload)

        def memory(agent_id):
            core = request("GET", f"/v1/agents/{agent_id}/core-memory/blocks")
            passages, after = [], None
            while True:
                params = {"limit": 100, "ascending": "true"}
                if after:
                    params["after"] = after
                page = request("GET", f"/v1/agents/{agent_id}/archival-memory", params=params)
                passages.extend(page)
                if len(page) < 100:
                    break
                after = page[-1]["id"]
            return {"timestamp": now(), "core_blocks": core, "archival_passages": passages}

        for number in range(1, 4):
            run = {"number": number, "started_at": now(), "turns": []}
            result["runs"].append(run)
            save()
            agent = request("POST", "/v1/agents/", json={
                "model": "openai-proxy/" + MODEL,
                "embedding_config": {"embedding_endpoint_type": "openai", "embedding_endpoint": proxy, "embedding_model": "BAAI/bge-small-en-v1.5", "embedding_dim": 384, "embedding_chunk_size": 300},
                "memory_blocks": [{"label": "human", "value": ""}, {"label": "persona", "value": ""}],
            })
            aid = agent["id"]
            run["agent_create_response"] = agent
            run["initial_memory"] = memory(aid)
            run["initial_tools"] = request("GET", f"/v1/agents/{aid}/tools", params={"limit": 100})
            save()
            print(f"Run {number}: agent created", flush=True)
            for i, text in enumerate(MESSAGES):
                turn = {"input": text, "started_at": now()}
                run["turns"].append(turn)
                save()
                turn["response"] = request("POST", f"/v1/agents/{aid}/messages", json={"messages": [{"role": "user", "content": text}]})
                turn["completed_at"] = now()
                save()
                if i in (0, 4, 5):
                    turn["memory"] = memory(aid)
                    if i == 5:
                        turn["recall_messages"] = request("GET", f"/v1/agents/{aid}/messages", params={"limit": 100, "order": "asc"})
                    save()
                print(f"Run {number}: turn {i + 1} recorded", flush=True)
            run["completed_at"] = now()
            save()
        result["status"] = "completed"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = redact(f"{type(exc).__name__}: {exc}")
        result["server_log_tail"] = list(logs)[-80:]
        print(redact(result["error"]), file=sys.stderr, flush=True)
    finally:
        result["finished_at"] = now()
        save()
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
        if adapter:
            adapter.shutdown()
        pg.stop()
        print(f"Artifact: {artifact.relative_to(ROOT)}", flush=True)
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
