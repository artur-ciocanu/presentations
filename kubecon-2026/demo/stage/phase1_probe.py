"""Exercise the two real model paths; report timings without logging credentials."""

import asyncio
import sys
import time
import uuid

from hindsight_client import Hindsight
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import load_config


class ProbeAnswer(BaseModel):
    answer: str


async def main():
    try:
        cfg = load_config()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None

    llm_client = AsyncOpenAI(base_url=cfg["LLM_BASE_URL"], api_key=cfg["LLM_API_KEY"],
                             timeout=25.0, max_retries=0)
    provider = OpenAIProvider(openai_client=llm_client)
    agent = Agent(OpenAIResponsesModel(cfg["LLM_MODEL"], provider=provider), output_type=ProbeAnswer)
    print(f"Provider: {cfg['HINDSIGHT_API_LLM_PROVIDER']}; model: {cfg['LLM_MODEL']}", flush=True)
    failed = False
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(agent.run("Return the answer 'ready'."), timeout=30)
        if result.output.answer.strip().lower().rstrip(".") != "ready":
            raise RuntimeError("Unexpected probe answer")
        print(f"PydanticAI Responses structured call: OK ({time.monotonic() - start:.2f}s)", flush=True)
    except Exception as exc:
        print(f"PydanticAI Responses call: FAILED ({type(exc).__name__}; HTTP {getattr(exc, 'status_code', 'unknown')}; {time.monotonic() - start:.2f}s)", flush=True)
        failed = True
    finally:
        await llm_client.close()

    if "--llm-only" in sys.argv:
        if failed:
            raise SystemExit(1)
        return

    memory = Hindsight(base_url=f"http://127.0.0.1:{cfg['HINDSIGHT_PORT']}", timeout=50.0)
    try:
        bank = "stage-preflight-" + uuid.uuid4().hex[:12]
        await asyncio.wait_for(memory.acreate_bank(bank_id=bank, name="Stage preflight", enable_observations=False), timeout=15)
        start = time.monotonic()
        await asyncio.wait_for(memory.aretain(bank_id=bank, content="The traveler prefers a window seat.",
                                             document_id="probe-source", retain_async=False), timeout=45)
        print(f"Hindsight synchronous retain: OK ({time.monotonic() - start:.2f}s)", flush=True)
        start = time.monotonic()
        recalled = await asyncio.wait_for(memory.arecall(bank_id=bank, query="What seat does the traveler prefer?", budget="low"), timeout=15)
        if not recalled.results:
            raise RuntimeError("Retain succeeded but recall returned no facts")
        print(f"Hindsight recall: OK ({len(recalled.results)} fact(s); {time.monotonic() - start:.2f}s)", flush=True)
        print(f"Preflight bank: {bank}", flush=True)
    except Exception as exc:
        print(f"Hindsight probe: FAILED ({type(exc).__name__}; HTTP {getattr(exc, 'status_code', 'unknown')}; {time.monotonic() - start:.2f}s)", flush=True)
        failed = True
    finally:
        await memory.aclose()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
