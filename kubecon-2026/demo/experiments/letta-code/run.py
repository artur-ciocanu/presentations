#!/usr/bin/env python3
"""Exercise the local Letta Code App Server without persisting provider secrets."""
import base64
import io
import json
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
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parent
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


def main():
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    artifact = ROOT / "artifacts" / f"{stamp}.json"
    artifact.parent.mkdir(exist_ok=True)
    state = ROOT / ".state" / stamp
    state.mkdir(parents=True, exist_ok=True)
    for number in range(1, 4):
        (state / f"run-{number}").mkdir()

    credentials = {}
    with (ROOT / "../../stage/.env").open() as source:
        for line in source:
            name = line.strip().removeprefix("export ").split("=", 1)[0].strip()
            if name in {"LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"}:
                credentials.update(dotenv_values(stream=io.StringIO(line), interpolate=False))
    upstream, key, model = (credentials.get(k) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
    if not all((upstream, key, model)):
        raise SystemExit("Missing LLM_BASE_URL, LLM_API_KEY, or LLM_MODEL")
    upstream = upstream.rstrip("/")

    def redact(value):
        if isinstance(value, str):
            return value.replace(key, "[REDACTED]").replace(upstream, "[REDACTED_UPSTREAM_URL]")
        if isinstance(value, list):
            return [redact(x) for x in value]
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        return value

    result = {
        "started_at": now(), "status": "running",
        "versions": {"letta_code": version("letta"), "python": sys.version},
        "model": model,
        "setup": {
            "backend": "native Letta Code App Server --backend local; WebSocket on 127.0.0.1:4500",
            "provider": "OpenAI-compatible localhost adapter; actual URL and key read from demo/stage/.env in memory only",
            "model_list": "adapter advertises configured model",
            "request_adjustment": "adapter sets reasoning_effort=none for chat completions, required by the endpoint when using function tools",
            "agent": "default runtime_start create_agent, no custom prompts, memory blocks, tools, or reflection configuration; clean isolated working directory",
            "isolation": "each agent has its own backend, home, and workspace; sandbox-exec denies writes outside its run directory and reads of protected paths and other runs; provider subprocess receives only a dummy key",
        },
        "runs": [], "model_requests": [],
    }
    lock = threading.RLock()

    def save():
        with lock:
            artifact.write_text(json.dumps(redact(result), ensure_ascii=False, indent=2) + "\n")

    class Adapter(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, content, content_type="application/json"):
            content = content.replace(key.encode(), b"[REDACTED]").replace(upstream.encode(), b"[REDACTED_UPSTREAM_URL]")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path.split("?")[0] == "/v1/models":
                return self.respond(200, json.dumps({"object": "list", "data": [{"id": model, "object": "model", "created": 0, "owned_by": "configured"}]}).encode())
            self.respond(404, b'{"error":"unsupported adapter path"}')

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if not self.path.startswith("/v1/"):
                return self.respond(404, b'{"error":"unsupported adapter path"}')
            try:
                payload = json.loads(body)
                if self.path.split("?")[0] == "/v1/chat/completions":
                    payload["reasoning_effort"] = "none"
                body = json.dumps(payload).encode()
                record = {"timestamp": now(), "path": self.path, "request": redact(payload)}
                with lock:
                    result["model_requests"].append(record)
                response = httpx.post(upstream + self.path[3:], content=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": self.headers.get("Accept", "application/json")}, timeout=300)
                record["status"] = response.status_code
                if response.status_code >= 400:
                    record["error_body"] = redact(response.text)
                save()
                self.respond(response.status_code, response.content, response.headers.get("content-type", "application/json"))
            except Exception as exc:
                self.respond(502, json.dumps({"error": redact(str(exc))}).encode())

    def git(memory_dir, *args):
        p = subprocess.run(["git", "-C", str(memory_dir), *args], env=env, capture_output=True, text=True, timeout=30)
        return {"exit_code": p.returncode, "stdout": redact(p.stdout), "stderr": redact(p.stderr)}

    def snapshot(agent_id, conversation_id):
        memory_dir = backend / "memfs" / agent_id / "memory"
        out = {"timestamp": now(), "memory_path": str(memory_dir.relative_to(ROOT)), "files": {}}
        if memory_dir.exists():
            for path in sorted(memory_dir.rglob("*")):
                if ".git" in path.relative_to(memory_dir).parts or path.is_symlink() or not path.is_file():
                    continue
                out["files"][str(path.relative_to(memory_dir))] = redact(path.read_text(errors="replace"))
            out["git_status"] = git(memory_dir, "status", "--porcelain")
            out["git_history_with_diffs"] = git(memory_dir, "log", "--all", "-p", "--format=fuller", "--no-ext-diff")
        encoded = base64.urlsafe_b64encode(f"conversation:{conversation_id}".encode()).decode().rstrip("=")
        conversation_dir = backend / "conversations" / encoded
        out["conversation_files"] = {}
        if conversation_dir.exists():
            for path in sorted(conversation_dir.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    out["conversation_files"][str(path.relative_to(conversation_dir))] = redact(path.read_text(errors="replace"))
        return out

    protected = [ROOT / "../../stage", ROOT / "../mem0", ROOT / "../letta", ROOT / "../../../presentation", ROOT / "../../../archive", ROOT / "../../../brief", ROOT / "../../../talk", ROOT / "../../../voice.md", ROOT / "../../../writing-frameworks.md", ROOT / "../../../talk-framework.md", ROOT / "artifacts", ROOT / "REPORT.md", ROOT / "run.py", ROOT / ".letta-local", ROOT / ".home"]
    for prior in (ROOT / ".state").iterdir():
        if prior != state:
            protected.append(prior)
    cli = str(ROOT / ".venv/bin/letta")
    server, adapter = None, None
    logs = deque(maxlen=400)
    save()
    try:
        adapter = ThreadingHTTPServer(("127.0.0.1", 0), Adapter)
        threading.Thread(target=adapter.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{adapter.server_port}/v1"
        for number in range(1, 4):
            run = {"number": number, "started_at": now(), "startup_events": [], "turns": []}
            result["runs"].append(run)
            run_state = state / f"run-{number}"
            home, temp, backend, cwd = (run_state / x for x in ("home", "tmp", "backend", "workspace"))
            for path in (home, temp, backend, cwd):
                path.mkdir(parents=True, exist_ok=True)
            profile = '(version 1) (allow default) (deny file-write*) (allow file-write* (subpath "' + str(run_state) + '") (literal "/dev/null"))'
            for path in protected + [state / f"run-{i}" for i in range(1, 4) if i != number]:
                path = path.resolve()
                profile += ' (deny file-read* (subpath "' + str(path) + '"))'
            env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE") if k in os.environ}
            env["PATH"] = str(ROOT / ".venv/bin") + os.pathsep + env.get("PATH", "")
            env.update({"HOME": str(home), "TMPDIR": str(temp), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(run_state / "cache"), "LETTA_LOCAL_BACKEND_DIR": str(backend), "GIT_CEILING_DIRECTORIES": str(ROOT)})
            prefix = ["/usr/bin/sandbox-exec", "-p", profile, cli]
            setup = subprocess.run(prefix + ["--backend", "local", "connect", "openai-compatible", "--name", "experiment", "--base-url", base, "--api-key", "loopback-only"], cwd=cwd, env=env, capture_output=True, text=True, timeout=90)
            run["provider_setup"] = {"exit_code": setup.returncode, "stdout": redact(setup.stdout), "stderr": redact(setup.stderr)}
            save()
            if setup.returncode:
                raise RuntimeError("Provider setup failed: " + redact(setup.stderr + setup.stdout))
            models = subprocess.run(prefix + ["--backend", "local", "model", "list", "--byok"], cwd=cwd, env=env, capture_output=True, text=True, timeout=90)
            run["model_listing"] = {"exit_code": models.returncode, "stdout": redact(models.stdout), "stderr": redact(models.stderr)}
            save()
            if models.returncode:
                raise RuntimeError("Model listing failed: " + redact(models.stderr + models.stdout))
            logs = deque(maxlen=400)
            server = subprocess.Popen(prefix + ["server", "--backend", "local", "--listen", "ws://127.0.0.1:4500"], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            def drain(process, sink):
                for line in process.stdout:
                    sink.append(redact(line))

            threading.Thread(target=drain, args=(server, logs), daemon=True).start()
            for _ in range(90):
                if server.poll() is not None:
                    raise RuntimeError("App Server exited: " + "".join(logs))
                try:
                    if httpx.get("http://127.0.0.1:4500/readyz", timeout=1, trust_env=False).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("App Server did not become ready")
            run["app_server_info"] = httpx.get("http://127.0.0.1:4500/app-server-info", timeout=10, trust_env=False).json()
            save()

            with connect("ws://127.0.0.1:4500/ws", open_timeout=10, max_size=32 * 1024 * 1024) as ws:
                ws.send(json.dumps({"type": "runtime_start", "request_id": f"start-{number}", "create_agent": {"body": {"model": "openai-compatible/" + model}}, "cwd": str(cwd)}))
                while True:
                    event = json.loads(ws.recv(timeout=120))
                    run["startup_events"].append(redact(event))
                    if event.get("type") == "runtime_start_response" and event.get("request_id") == f"start-{number}":
                        if not event.get("success"):
                            raise RuntimeError("Agent startup failed: " + str(redact(event)))
                        runtime = event["runtime"]
                        break
                run["runtime"] = runtime
                run["initial_memory"] = snapshot(runtime["agent_id"], runtime["conversation_id"])
                save()
                print(f"Run {number}: agent created", flush=True)
                for index, text in enumerate(MESSAGES):
                    turn = {"input": text, "started_at": now(), "events": []}
                    run["turns"].append(turn)
                    save()
                    ws.send(json.dumps({"type": "input", "runtime": runtime, "payload": {"kind": "create_message", "messages": [{"role": "user", "content": text}]}}))
                    while True:
                        event = json.loads(ws.recv(timeout=240))
                        turn["events"].append(redact(event))
                        save()
                        if event.get("type") == "control_request":
                            # Do not silently grant an unknown permission. Preserve the request.
                            raise RuntimeError("Agent requested interactive tool approval; stopped rather than changing default permissions: " + str(redact(event)))
                        if event.get("type") == "stream_delta":
                            delta = event.get("delta", {})
                            if delta.get("message_type") in ("loop_error", "error_message"):
                                raise RuntimeError("Agent error: " + str(redact(delta)))
                            if delta.get("message_type") == "stop_reason" and delta.get("stop_reason") != "requires_approval":
                                break
                    turn["completed_at"] = now()
                    if index in (0, 4, 5):
                        turn["memory"] = snapshot(runtime["agent_id"], runtime["conversation_id"])
                    save()
                    print(f"Run {number}: turn {index + 1} recorded", flush=True)
                run["completed_at"] = now()
                save()
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            server = None
        result["status"] = "completed"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = redact(f"{type(exc).__name__}: {exc}")
        result["server_log_tail"] = list(logs)[-80:]
        print(result["error"], file=sys.stderr, flush=True)
    finally:
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if adapter:
            adapter.shutdown()
        result["finished_at"] = now()
        save()
        print(f"Artifact: {artifact.relative_to(ROOT)}", flush=True)
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
