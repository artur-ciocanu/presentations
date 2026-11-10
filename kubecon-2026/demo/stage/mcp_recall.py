"""Print actual native-MCP recall output for a single bank."""

import asyncio
import json
import sys

from config import load_config
from protocols import mcp_recall


async def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: just mcp-recall BANK_ID")
    cfg = load_config()
    result = await mcp_recall(f"http://127.0.0.1:{cfg['HINDSIGHT_PORT']}", sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
