"""One-turn walkthrough of the stage demo: retain, then recall without and with the subject filter."""

import asyncio
import json
import time
from datetime import datetime, timezone

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from config import ROOT
from runtime import Demo

console = Console(highlight=False)


def show_facts(title, items):
    console.print(f"\n[bold]{title}[/bold]")
    if not items:
        console.print("No facts returned.")
    for rank, item in enumerate(items, 1):
        text = Text(f"{rank}. " + (item.get("text") or ""))
        text.append("\n   tags: " + ", ".join(item.get("tags") or []))
        console.print(Panel(text, expand=False))


async def main():
    scenario = yaml.safe_load((ROOT / "scenario.yaml").read_text())
    target = ROOT / "artifacts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True, exist_ok=False)
    saved = {"success": False}
    start = time.monotonic()
    demo = Demo()
    try:
        session = await demo.create_session()
        result = await demo.turn(session, scenario["conversations"][0]["utterance"])
        saved["turn"] = result
        console.print(f"[bold]Memory bank:[/bold] {session.bank_id}")
        console.print("\n[bold]WRITE · retain · tags: task:flight-booking[/bold]\n" + result["source_text"])
        show_facts("Stored facts, with the labels Hindsight assigned as tags", result["stored_facts"]["items"])
        show_facts(f"READ · recall · no filter · {result['question']}", result["recall_unfiltered"]["results"])
        show_facts(f"READ · recall · tags: [\"subject:user\"] · any_strict · {result['question']}", result["recall_subject_user"]["results"])
        failed = [name for name, ok in result["checks"].items() if not ok]
        if failed:
            raise AssertionError("Slide claims not met: " + ", ".join(failed))
        console.print("\n[bold green]Matches S18–S19:[/bold green] unfiltered #1 is mom's health fact; the subject:user filter excludes it.")
        saved["success"] = True
    except Exception as exc:
        saved["error_type"] = type(exc).__name__
        if isinstance(exc, AssertionError):
            saved["check"] = str(exc)
        console.print(f"[bold red]Walkthrough failed:[/bold red] {type(exc).__name__} {saved.get('check', '')}")
    finally:
        saved["seconds"] = round(time.monotonic() - start, 3)
        saved["phase_seconds"] = dict(demo.phase_times)
        (target / "architecture.json").write_text(json.dumps(saved, indent=2, ensure_ascii=False))
        console.print(f"Evidence: {target}; {saved['seconds']:.2f}s; phases: {json.dumps(saved['phase_seconds'])}")
        await demo.aclose()
    if not saved["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
