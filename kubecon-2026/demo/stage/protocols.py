"""Equivalent Hindsight recall through REST and the native MCP endpoint."""

import httpx
from fastmcp import Client

from runtime import RECALL_ARGS


def recall_arguments():
    return dict(RECALL_ARGS)


async def rest_recall(base_url, bank_id):
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        response = await client.post(f"{base_url}/v1/default/banks/{bank_id}/memories/recall", json=recall_arguments())
        response.raise_for_status()
        return response.json()


async def mcp_recall(base_url, bank_id):
    async with Client(f"{base_url}/mcp/{bank_id}/", timeout=60) as client:
        result = await client.call_tool("recall", recall_arguments())
        if not isinstance(result.data, dict):
            raise RuntimeError("MCP recall returned an unexpected response")
        return result.data


def fact_identity(response):
    """The protocols differ in field names; compare actual fact IDs, text and sources."""
    return {(item["id"], item["text"], item.get("document_id")) for item in response["results"]}
