"""Measure warm Hindsight recall and its reported in-process rerank phase."""

import asyncio
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone

from hindsight_client import Hindsight

from config import ROOT, load_config
from runtime import RECALL_ARGS


def summary(values):
    ordered = sorted(values)
    return {"median_ms": round(statistics.median(ordered), 2),
            "p95_ms": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 2),
            "max_ms": round(max(ordered), 2)}


async def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: just bench-recall BANK_ID")
    cfg = load_config()
    bank = sys.argv[1]
    client = Hindsight(base_url=f"http://127.0.0.1:{cfg['HINDSIGHT_PORT']}", timeout=60)
    samples = []
    try:
        for index in range(21):
            start = time.perf_counter()
            response = await client.arecall(bank_id=bank, trace=True, **RECALL_ARGS)
            total = (time.perf_counter() - start) * 1000
            data = response.model_dump(mode="json")
            metrics = data.get("trace", {}).get("summary", {}).get("phase_metrics", [])
            phase = next((p for p in metrics if p["phase_name"] == "reranking"), None)
            if not phase or phase["details"].get("reranker_type") != "cross-encoder":
                raise RuntimeError("No cross-encoder timing returned by Hindsight")
            if not data["results"] or any((r.get("scores") or {}).get("reranker") is None for r in data["results"]):
                raise RuntimeError("No reranker-scored results")
            if index:  # First call is an unmeasured warm-up.
                samples.append({"total_ms": round(total, 3), "rerank_ms": round(phase["duration_seconds"] * 1000, 3),
                                "candidates": phase["details"].get("candidates_reranked"),
                                "results": len(data["results"])})
    finally:
        await client.aclose()
    result = {"bank_id": bank, "samples": samples,
              "total_recall": summary([s["total_ms"] for s in samples]),
              "rerank_phase": summary([s["rerank_ms"] for s in samples])}
    target = ROOT / "artifacts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True, exist_ok=False)
    (target / "recall-benchmark.json").write_text(json.dumps(result, indent=2))
    print(f"Warm sequential calls: {len(samples)}; candidates per call: {sorted({s['candidates'] for s in samples})}")
    print("Total recall (ms):", json.dumps(result["total_recall"]))
    print("Hindsight-reported cross-encoder phase (ms):", json.dumps(result["rerank_phase"]))
    print(f"Saved timings: {target}")


if __name__ == "__main__":
    asyncio.run(main())
