"""
Edge Service - Chainlit Application

Demonstrates an AI agent that dynamically updates its configuration
based on MongoDB change stream events.
"""

import asyncio
import logging
import os
from functools import lru_cache
from datetime import datetime, timezone
from typing import Optional

import chainlit as cl
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, BadRequestError
from anthropic import AsyncAnthropic, AsyncAnthropicFoundry

from change_stream_consumer import get_consumer, ChangeEvent, AgentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Current configuration (updated via change stream)
current_config: Optional[AgentConfig] = None


@lru_cache(maxsize=1)
def get_azure_openai_client() -> AsyncAzureOpenAI:
    """Create a cached Azure OpenAI client from environment variables."""
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    missing = []
    if not azure_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")

    if missing:
        raise ValueError(
            "Missing Azure OpenAI environment variables: "
            + ", ".join(missing)
        )

    return AsyncAzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version=api_version
    )


@lru_cache(maxsize=1)
def get_anthropic_client() -> AsyncAnthropic | AsyncAnthropicFoundry:
    """
    Create a cached Anthropic client.

    Uses Anthropic Foundry client when ANTHROPIC_FOUNDRY_* variables are set,
    otherwise falls back to direct Anthropic API client.
    """
    foundry_api_key = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
    foundry_resource = os.getenv("ANTHROPIC_FOUNDRY_RESOURCE")
    foundry_base_url = os.getenv("ANTHROPIC_FOUNDRY_BASE_URL")

    if foundry_api_key and (foundry_resource or foundry_base_url):
        if foundry_base_url:
            logger.info("Using Anthropic Foundry client via explicit base URL.")
            return AsyncAnthropicFoundry(
                api_key=foundry_api_key,
                base_url=foundry_base_url
            )

        logger.info("Using Anthropic Foundry client via resource name.")
        return AsyncAnthropicFoundry(
            api_key=foundry_api_key,
            resource=foundry_resource
        )

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_base_url = os.getenv("ANTHROPIC_BASE_URL")

    anthropic_kwargs = {}
    if anthropic_api_key:
        anthropic_kwargs["api_key"] = anthropic_api_key
    if anthropic_base_url:
        anthropic_kwargs["base_url"] = anthropic_base_url

    logger.info("Using direct Anthropic API client.")
    return AsyncAnthropic(**anthropic_kwargs)


async def ensure_config_exists() -> AgentConfig:
    """Load an existing config or create a default one for immediate usability."""
    consumer = get_consumer()
    collection = consumer.collection

    existing = await collection.find_one(sort=[("updatedAt", -1)])
    if existing:
        return AgentConfig(**existing)

    default_agent_id = os.getenv("EDGE_DEFAULT_AGENT_ID", "edge-default-agent")
    default_deployment = (
        os.getenv("EDGE_DEFAULT_AZURE_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or "gpt-4o"
    )
    default_name = os.getenv("EDGE_DEFAULT_AGENT_NAME", "Edge Default Agent")

    await collection.update_one(
        {"agentId": default_agent_id},
        {"$setOnInsert": {
            "agentId": default_agent_id,
            "name": default_name,
            "modelProvider": "OPENAI",
            "modelId": default_deployment,
            "temperature": 0.7,
            "maxTokens": 1024,
            "systemPrompt": "You are a helpful assistant at a developer conference.",
            "tools": ["web_search"],
            "metadata": {"autoBootstrappedBy": "edge-service"},
            "updatedAt": datetime.now(timezone.utc)
        }},
        upsert=True
    )

    created = await collection.find_one({"agentId": default_agent_id})
    if not created:
        raise RuntimeError("Failed to bootstrap default agent configuration.")

    return AgentConfig(**created)


async def create_azure_chat_completion(
    client: AsyncAzureOpenAI,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: Optional[int]
):
    """Call Azure Chat Completions with token-parameter compatibility fallback."""
    request_args = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if max_tokens is not None:
        request_args["max_tokens"] = max_tokens

    for _ in range(3):
        try:
            return await client.chat.completions.create(**request_args)
        except BadRequestError as e:
            error_text = str(e)
            adjusted = False

            # Newer models may reject `max_tokens` and require `max_completion_tokens`.
            if (
                max_tokens is not None
                and "max_tokens" in error_text
                and "max_completion_tokens" in error_text
                and "max_tokens" in request_args
            ):
                request_args.pop("max_tokens", None)
                request_args["max_completion_tokens"] = max_tokens
                adjusted = True

            # Some models only support default temperature=1.
            if (
                "temperature" in error_text
                and "default (1) value is supported" in error_text
                and request_args.get("temperature") != 1
            ):
                request_args["temperature"] = 1
                adjusted = True

            if adjusted:
                continue
            raise

    raise RuntimeError("Azure completion retries exhausted.")


async def handle_config_change(event: ChangeEvent) -> None:
    """Handle configuration changes from the Hub service."""
    global current_config

    if event.operation_type == "delete":
        logger.info(f"Agent {event.agent_id} deleted")
        if current_config and current_config.agentId == event.agent_id:
            current_config = None
            # Notify active sessions
            await cl.Message(
                content=f"Configuration for agent '{event.agent_id}' was deleted.",
                author="System"
            ).send()
        return

    if event.full_document:
        old_config = current_config
        current_config = event.full_document

        logger.info(f"Configuration updated: {current_config.name}")

        # Build change summary
        if event.operation_type == "insert":
            change_msg = f"New agent configured: **{current_config.name}**"
        else:
            changes = []
            if event.updated_fields:
                changes = [f"`{k}`: {v}" for k, v in event.updated_fields.items()]
            change_msg = f"Configuration updated:\n" + "\n".join(f"- {c}" for c in changes) if changes else "Configuration updated"

        # Notify active Chainlit session
        await cl.Message(
            content=f"{change_msg}\n\n**Current settings:**\n"
                    f"- Model: {current_config.modelProvider}/{current_config.modelId}\n"
                    f"- Temperature: {current_config.temperature}\n"
                    f"- System Prompt: {current_config.systemPrompt[:100] + '...' if current_config.systemPrompt and len(current_config.systemPrompt) > 100 else current_config.systemPrompt or 'None'}",
            author="System"
        ).send()


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session."""
    global current_config

    # Start change stream consumer if not running
    consumer = get_consumer()
    consumer.on_change(handle_config_change)
    await consumer.start()

    if not current_config:
        current_config = await ensure_config_exists()

    # Welcome message
    if current_config:
        await cl.Message(
            content=f"Hello! I'm **{current_config.name}**, powered by {current_config.modelProvider}/{current_config.modelId}.\n\n"
                    f"My configuration is managed by the Hub service and updates in real-time. "
                    f"Try changing my settings through the Hub API and watch me adapt!"
        ).send()
    else:
        await cl.Message(
            content="Hello! I'm waiting for configuration from the Hub service. "
                    "Please create an agent configuration via the Hub API."
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming chat messages."""
    global current_config

    if not current_config:
        await cl.Message(
            content="I don't have a configuration yet. Please create one via the Hub API:\n\n"
                    "```bash\n"
                    "curl -X POST http://localhost:8081/api/v1/agents \\\n"
                    "  -H 'Content-Type: application/json' \\\n"
                    "  -d '{\"agentId\": \"demo-agent\", \"name\": \"Demo Agent\", ...}'\n"
                    "```"
        ).send()
        return

    # Build messages for LLM
    messages = []
    if current_config.systemPrompt:
        messages.append({"role": "system", "content": current_config.systemPrompt})
    messages.append({"role": "user", "content": message.content})

    # Call appropriate LLM based on configuration
    try:
        if current_config.modelProvider == "OPENAI":
            azure_openai_client = get_azure_openai_client()
            response = await create_azure_chat_completion(
                client=azure_openai_client,
                model=current_config.modelId,
                messages=messages,
                temperature=current_config.temperature,
                max_tokens=current_config.maxTokens
            )
            reply = response.choices[0].message.content

        elif current_config.modelProvider == "ANTHROPIC":
            anthropic_client = get_anthropic_client()
            system_prompt = current_config.systemPrompt or ""
            user_messages = [{"role": "user", "content": message.content}]

            response = await anthropic_client.messages.create(
                model=current_config.modelId,
                system=system_prompt,
                messages=user_messages,
                temperature=current_config.temperature,
                max_tokens=current_config.maxTokens or 1024
            )
            reply = response.content[0].text

        else:
            reply = f"Unsupported model provider: {current_config.modelProvider}"

        await cl.Message(content=reply).send()

    except Exception as e:
        logger.error(f"LLM error: {e}")
        error_text = str(e)
        if (
            current_config.modelProvider == "ANTHROPIC"
            and "DeploymentNotFound" in error_text
        ):
            await cl.Message(
                content=(
                    f"Anthropic deployment '{current_config.modelId}' was not found in Azure Foundry.\n"
                    "Set `modelId` to the exact deployed name from your Foundry project and retry "
                    f"(for example: `just demo-create <your-anthropic-deployment>`)."
                )
            ).send()
            return
        if "Deployment" in error_text and "not supported by any backend" in error_text:
            await cl.Message(
                content=(
                    f"Azure deployment '{current_config.modelId}' is not available on your endpoint.\n"
                    "Set `modelId` to a valid Azure deployment name (not the base model name), "
                    "or run `just demo-openai <your-deployment-name>`."
                )
            ).send()
            return
        await cl.Message(
            content=f"Error calling LLM: {error_text}"
        ).send()


@cl.on_chat_end
async def on_chat_end():
    """Clean up when chat session ends."""
    consumer = get_consumer()
    consumer.remove_callback(handle_config_change)
