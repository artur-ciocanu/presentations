"""
Edge Service - Chainlit Application

Demonstrates an AI agent that dynamically updates its configuration
based on MongoDB change stream events.
"""

import asyncio
import logging
from typing import Optional

import chainlit as cl
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from change_stream_consumer import get_consumer, ChangeEvent, AgentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM clients
openai_client = AsyncOpenAI()
anthropic_client = AsyncAnthropic()

# Current configuration (updated via change stream)
current_config: Optional[AgentConfig] = None


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
            response = await openai_client.chat.completions.create(
                model=current_config.modelId,
                messages=messages,
                temperature=current_config.temperature,
                max_tokens=current_config.maxTokens
            )
            reply = response.choices[0].message.content

        elif current_config.modelProvider == "ANTHROPIC":
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
        await cl.Message(
            content=f"Error calling LLM: {str(e)}"
        ).send()


@cl.on_chat_end
async def on_chat_end():
    """Clean up when chat session ends."""
    consumer = get_consumer()
    consumer.remove_callback(handle_config_change)
