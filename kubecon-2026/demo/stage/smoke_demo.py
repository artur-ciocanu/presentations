"""Run the first flight turn against real services and save actual evidence."""

import asyncio
import json
import time
from datetime import datetime, timezone

import yaml
from config import ROOT
from runtime import Demo


async def main():
    scenario = yaml.safe_load((ROOT / "scenario.yaml").read_text())
    target = ROOT / "artifacts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    saved = {"success": False}
    demo = Demo()
    try:
        session = await demo.create_session()
        result = await demo.turn(session, scenario["conversations"][0]["utterance"])
        saved["turn"] = result
        print(f"Stored {result['stored_facts']['total']} facts; unfiltered recall {len(result['recall_unfiltered']['results'])}; "
              f"subject:user recall {len(result['recall_subject_user']['results'])}.", flush=True)
        for name, ok in result["checks"].items():
            print(f"  {'PASS' if ok else 'FAIL'} {name}", flush=True)
        failed = [name for name, ok in result["checks"].items() if not ok]
        assert not failed, ", ".join(failed)
        saved["success"] = True
        print("LIVE FLIGHT SMOKE PASS", flush=True)
    except Exception as exc:
        saved["error_type"] = type(exc).__name__
        if isinstance(exc, AssertionError):
            saved["check"] = str(exc)
        print(f"LIVE FLIGHT SMOKE FAILED: {type(exc).__name__}" + (f" ({saved['check']})" if "check" in saved else ""), flush=True)
    finally:
        saved["seconds"] = round(time.monotonic() - start, 3)
        saved["phase_seconds"] = dict(demo.phase_times)
        (target / "live-smoke.json").write_text(json.dumps(saved, indent=2, ensure_ascii=False))
        print(f"Evidence: {target}; {saved['seconds']:.2f}s", flush=True)
        print("Phase seconds:", json.dumps(saved["phase_seconds"]), flush=True)
        await demo.aclose()
    if not saved["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
