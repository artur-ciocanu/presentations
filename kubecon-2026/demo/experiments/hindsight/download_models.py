#!/usr/bin/env python3
"""Optional parallel HTTPS fallback for stalled public model downloads.

Outputs are verified against Hugging Face's published LFS SHA-256 and are not
installed into the active cache; stop the server before doing that.
"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent / ".cache" / "downloads" / "ranged"
MODELS = [
    ("BAAI/bge-small-en-v1.5", 133466304, "3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad"),
    ("hindsight-ai/hs-rerank-1", 227593826, "4a3b0d9a505dd9fe810bfa411e23a45c33d6c6d5801e1b680f390edea7db2782"),
]
CHUNK = 8 * 1024 * 1024


def download(model, size, digest):
    directory = ROOT / digest
    directory.mkdir(parents=True, exist_ok=True)
    def part(i):
        start, end = i * CHUNK, min(size, (i + 1) * CHUNK) - 1
        path = directory / str(i)
        req = Request(f"https://huggingface.co/{model}/resolve/main/model.safetensors?part={i}",
                      headers={"Range": f"bytes={start}-{end}"})
        with urlopen(req, timeout=120) as response:
            expected = f"bytes {start}-{end}/{size}"
            if response.status != 206 or response.headers.get("Content-Range") != expected:
                raise ValueError(f"Unexpected range response for {model} part {i}")
            content = response.read()
        if len(content) != end - start + 1:
            raise ValueError(f"Incomplete range for {model} part {i}")
        path.write_bytes(content)
        return path
    count = (size + CHUNK - 1) // CHUNK
    with ThreadPoolExecutor(max_workers=8) as executor:
        paths = list(executor.map(part, range(count)))
    output = ROOT / f"{digest}.safetensors"
    h = hashlib.sha256()
    with output.open("wb") as dst:
        for path in paths:
            data = path.read_bytes()
            h.update(data)
            dst.write(data)
    if h.hexdigest() != digest:
        raise ValueError(f"SHA-256 mismatch for {model}")
    print(f"Verified {model} ({size} bytes, SHA-256 {digest})", flush=True)


with ThreadPoolExecutor(max_workers=2) as executor:
    list(executor.map(lambda args: download(*args), MODELS))
