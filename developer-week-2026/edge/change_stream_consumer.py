"""
Change Stream Consumer for Agent Configuration updates.

This module connects to MongoDB change streams and notifies
Chainlit sessions when configurations change.
"""

import asyncio
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from jsonschema import validate, ValidationError
import json

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Agent configuration model matching JSON Schema."""
    agentId: str
    name: str
    modelProvider: str
    modelId: str
    temperature: float
    maxTokens: Optional[int] = None
    systemPrompt: Optional[str] = None
    tools: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    updatedAt: Optional[datetime] = None


class ChangeEvent(BaseModel):
    """Processed change stream event."""
    operation_type: str
    document_id: str
    agent_id: Optional[str] = None
    full_document: Optional[AgentConfig] = None
    updated_fields: Optional[Dict[str, Any]] = None
    removed_fields: Optional[list[str]] = None
    timestamp: datetime


class ChangeStreamConsumer:
    """
    Async consumer for MongoDB change streams.

    Validates incoming events against the JSON Schema contract
    before notifying subscribers.
    """

    def __init__(
        self,
        mongo_uri: str,
        database: str,
        collection: str,
        schema_path: str = "../schemas/agent-config.schema.json"
    ):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[database]
        self.collection = self.db[collection]
        self.callbacks: list[Callable[[ChangeEvent], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Load JSON Schema for validation
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)

    def on_change(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Register a callback for change events."""
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Remove a registered callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def start(self) -> None:
        """Start consuming change stream events."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._watch())
        logger.info("Change stream consumer started")

    async def stop(self) -> None:
        """Stop the change stream consumer."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Change stream consumer stopped")

    async def _watch(self) -> None:
        """Main watch loop with reconnection logic."""
        pipeline = [
            {"$match": {"operationType": {"$in": ["insert", "update", "replace", "delete"]}}}
        ]

        while self._running:
            try:
                async with self.collection.watch(
                    pipeline,
                    full_document="whenAvailable",
                    full_document_before_change="whenAvailable"
                ) as stream:
                    async for change in stream:
                        if not self._running:
                            break
                        await self._process_change(change)

            except Exception as e:
                logger.error(f"Change stream error: {e}")
                if self._running:
                    await asyncio.sleep(5)  # Backoff before retry

    async def _process_change(self, change: Dict[str, Any]) -> None:
        """Process a single change event."""
        try:
            operation_type = change["operationType"]
            document_key = change.get("documentKey", {})
            full_document = change.get("fullDocument")

            # Validate against JSON Schema contract
            if full_document:
                self._validate_document(full_document)

            # Build change event
            event = ChangeEvent(
                operation_type=operation_type,
                document_id=str(document_key.get("_id", "")),
                agent_id=full_document.get("agentId") if full_document else None,
                full_document=AgentConfig(**full_document) if full_document else None,
                updated_fields=change.get("updateDescription", {}).get("updatedFields"),
                removed_fields=change.get("updateDescription", {}).get("removedFields"),
                timestamp=datetime.utcnow()
            )

            # Notify all callbacks
            for callback in self.callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        except ValidationError as e:
            # CONTRACT VIOLATION - this is what we want to demonstrate!
            logger.error(f"CONTRACT VIOLATION: Document failed schema validation: {e}")
            # In production, you might send this to a dead letter queue
            # or alert monitoring systems

        except Exception as e:
            logger.error(f"Error processing change: {e}")

    def _validate_document(self, document: Dict[str, Any]) -> None:
        """Validate document against JSON Schema contract."""
        # Remove MongoDB-specific fields before validation
        doc_copy = {k: v for k, v in document.items() if not k.startswith("_")}
        validate(instance=doc_copy, schema=self.schema)


# Singleton instance for use across the application
_consumer: Optional[ChangeStreamConsumer] = None


def get_consumer() -> ChangeStreamConsumer:
    """Get or create the change stream consumer singleton."""
    global _consumer
    if _consumer is None:
        _consumer = ChangeStreamConsumer(
            mongo_uri="mongodb://localhost:27017/?replicaSet=rs0&directConnection=true",
            database="hub_db",
            collection="agentConfigs"
        )
    return _consumer
