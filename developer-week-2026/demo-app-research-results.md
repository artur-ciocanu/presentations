# Demo Application Research Results
## Contract-First Development with MongoDB Change Streams, AsyncAPI, and Microcks

**Research Date:** February 2026
**Prepared for:** DeveloperWeek Conference Demo

---

## Table of Contents

1. [Architecture Decision Document](#1-architecture-decision-document)
2. [Implementation Guide](#2-implementation-guide)
3. [Demo Script](#3-demo-script)
4. [Troubleshooting Guide](#4-troubleshooting-guide)
5. [Code Scaffolding](#5-code-scaffolding)
6. [Research Answers](#6-research-answers)
7. [Version Recommendations](#7-version-recommendations)

---

## 1. Architecture Decision Document

### Overview

This document justifies the key technology choices for demonstrating contract-first development with MongoDB change streams, AsyncAPI, and Microcks.

### Core Thesis

**"If we agree on the contract, implementation language doesn't matter."**

This is demonstrated through:
- Hub Service (Java/Spring Boot) producing change events
- Edge Service (Python/Chainlit) consuming change events
- JSON Schema as the single source of truth
- AsyncAPI documenting the event contract
- Microcks validating both sides against the contract

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Contract Layer (Source of Truth)                   │
│  ┌─────────────────────┐    ┌──────────────────────────────────────────┐   │
│  │ agent-config.schema │───▶│ agent-config-events.asyncapi.yaml        │   │
│  │      (JSON Schema)  │    │ (References JSON Schema for payload)     │   │
│  └─────────────────────┘    └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
           ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
           │   Microcks    │   │  Hub Service  │   │ Edge Service  │
           │  (Contract    │   │  (Java/Spring)│   │   (Python/    │
           │   Testing)    │   │               │   │   Chainlit)   │
           └───────────────┘   └───────────────┘   └───────────────┘
                                       │                   │
                                       │  MongoDB Change   │
                                       │     Stream        │
                                       └─────────┬─────────┘
                                                 ▼
                                       ┌───────────────┐
                                       │   MongoDB     │
                                       │  (Replica Set)│
                                       └───────────────┘
```

### Decision 1: Why Chainlit for Edge Service

**Decision:** Use Chainlit for the Edge Service UI instead of a generic Python web framework.

**Rationale:**
- Visual impact: Chainlit provides a polished chat interface out of the box
- LLM integration: Natural fit for an "AI Agent Configuration" demo scenario
- Real-time updates: WebSocket-based architecture supports live config changes
- Minimal code: Achieves demo goals with less boilerplate than Flask/FastAPI+frontend
- Audience familiarity: Developer audience will recognize chat UI patterns

**Trade-offs:**
- Less flexible than a custom UI
- Specific to chat/agent use cases
- Learning curve for Chainlit-specific patterns

**Alternatives Considered:**
- Streamlit: Good for dashboards, but chat interface is less native
- Gradio: Similar to Chainlit but less polished for production scenarios
- FastAPI + React: More flexible but requires more setup time

### Decision 2: Why MongoDB Change Streams (Not Kafka)

**Decision:** Use MongoDB change streams directly without an intermediary message broker.

**Rationale:**
- Simpler architecture: One fewer moving part
- Native CDC: Change streams are built into MongoDB
- Demo clarity: Audience can see data → event flow clearly
- Sufficient for demo: No need for Kafka's scale/durability for a conference demo
- Novel combination: AsyncAPI + MongoDB change streams is less explored territory

**Trade-offs:**
- No Microcks direct integration (workaround needed)
- Less production-realistic for high-scale scenarios
- Requires replica set (slightly more complex MongoDB setup)

**Alternatives Considered:**
- MongoDB + Kafka Connect + Kafka: More realistic but adds complexity
- Debezium + Kafka: Industry standard CDC but overkill for demo
- Direct MongoDB polling: Simpler but loses real-time nature

### Decision 3: Schema Layering Strategy

**Decision:** Use a three-layer schema architecture with composition.

```
schemas/
├── agent-config.schema.json     # Core schema (portable)
└── agent-config-events.asyncapi.yaml  # References core schema
```

**Rationale:**
- Single source of truth: Core schema defines the domain model
- Reuse without duplication: AsyncAPI references the schema via `$ref`
- MongoDB validation: Same schema (with bsonType mapping) validates documents
- Clear separation: Domain logic vs. event envelope vs. storage concerns

**Implementation Pattern:**

```yaml
# AsyncAPI references external JSON Schema
components:
  schemas:
    AgentConfiguration:
      $ref: 'agent-config.schema.json'
```

### Decision 4: Microcks Integration Approach

**Decision:** Use Microcks for schema validation and mock generation, not direct MongoDB integration.

**Rationale:**
- Microcks doesn't natively support MongoDB change streams
- Schema validation is the core value for contract testing
- Import AsyncAPI spec to show contract documentation
- Use Microcks Testcontainers for integration tests
- Focus demo on "breaking the contract" scenario

**Approach:**
1. Import AsyncAPI spec into Microcks UI
2. Show mock event generation from spec
3. Use Java tests with Microcks Testcontainers to validate events
4. Demonstrate contract violation detection

### Decision 5: Why AsyncAPI 3.0

**Decision:** Use AsyncAPI 3.0.0 specification.

**Rationale:**
- Current stable version (released December 2023)
- Decoupled operations from channels (better modeling)
- Multi-message support per channel (fits change stream events)
- Better `$ref` handling for external schemas
- Microcks 1.8+ supports AsyncAPI 3.0

**Note:** No official MongoDB binding exists for AsyncAPI. We'll use a custom approach to model the change stream channel.

### Differentiation Summary

This demo fills a gap in the ecosystem:

| Aspect | Existing State | Our Contribution |
|--------|---------------|------------------|
| AsyncAPI + MongoDB | No official binding | Proposed pattern |
| Microcks + MongoDB CDC | No examples | First demo |
| Polyglot contract proof | Theoretical | Working demo |
| Schema as single source | Concept | Practical implementation |

---

## 2. Implementation Guide

### Prerequisites

- Docker and Docker Compose
- Java 21 (LTS)
- Python 3.12
- Maven or Gradle
- Git

### Step 1: Project Structure Setup

```bash
mkdir asyncapi-mongodb-demo && cd asyncapi-mongodb-demo

# Create directory structure
mkdir -p schemas hub/src/main/java/com/example/hub/{model,repository,controller,config}
mkdir -p hub/src/main/resources hub/src/test/java/com/example/hub
mkdir -p edge scripts
```

### Step 2: JSON Schema (Single Source of Truth)

Create `schemas/agent-config.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/agent-config.schema.json",
  "title": "AgentConfiguration",
  "description": "Configuration for an AI agent instance",
  "type": "object",
  "required": ["agentId", "name", "modelProvider", "modelId", "temperature"],
  "properties": {
    "agentId": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "description": "Unique agent identifier (lowercase alphanumeric with hyphens)"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "description": "Human-readable agent name"
    },
    "modelProvider": {
      "type": "string",
      "enum": ["OPENAI", "ANTHROPIC", "GOOGLE", "MISTRAL"],
      "description": "LLM provider"
    },
    "modelId": {
      "type": "string",
      "description": "Specific model identifier (e.g., gpt-4, claude-3)"
    },
    "temperature": {
      "type": "number",
      "minimum": 0,
      "maximum": 2,
      "description": "Sampling temperature for model responses"
    },
    "maxTokens": {
      "type": "integer",
      "minimum": 1,
      "maximum": 128000,
      "description": "Maximum tokens in response"
    },
    "systemPrompt": {
      "type": "string",
      "description": "System instruction for the agent"
    },
    "tools": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of enabled tool names"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true,
      "description": "Flexible key-value pairs for custom data"
    },
    "version": {
      "type": "integer",
      "minimum": 0,
      "description": "Configuration version for optimistic locking"
    },
    "updatedAt": {
      "type": "string",
      "format": "date-time",
      "description": "Last update timestamp"
    }
  }
}
```

### Step 3: AsyncAPI Specification

Create `schemas/agent-config-events.asyncapi.yaml`:

```yaml
asyncapi: 3.0.0
info:
  title: Agent Configuration Events
  version: 1.0.0
  description: |
    Events emitted when agent configurations change in the Hub service.
    Consumed by Edge services to update running agents in real-time.

    This API demonstrates contract-first development where the JSON Schema
    is the single source of truth for both MongoDB validation and event payloads.
  contact:
    name: Platform Team
    email: platform@example.com
  license:
    name: Apache 2.0
    url: https://www.apache.org/licenses/LICENSE-2.0

servers:
  development:
    host: localhost:27017
    protocol: mongodb
    description: Local MongoDB replica set

  production:
    host: mongodb-cluster.example.com:27017
    protocol: mongodb+srv
    description: Production MongoDB Atlas cluster

defaultContentType: application/json

channels:
  agentConfigChanges:
    address: hub_db.agentConfigs
    title: Agent Configuration Changes
    description: |
      MongoDB change stream on the agentConfigs collection.
      Emits events for insert, update, replace, and delete operations.
    messages:
      insertEvent:
        $ref: '#/components/messages/AgentConfigInsertEvent'
      updateEvent:
        $ref: '#/components/messages/AgentConfigUpdateEvent'
      deleteEvent:
        $ref: '#/components/messages/AgentConfigDeleteEvent'

operations:
  onAgentConfigChange:
    action: receive
    channel:
      $ref: '#/channels/agentConfigChanges'
    summary: Receive agent configuration change events
    description: |
      Subscribe to real-time configuration changes.
      Use the resume token from the _id field to resume after disconnection.
    messages:
      - $ref: '#/channels/agentConfigChanges/messages/insertEvent'
      - $ref: '#/channels/agentConfigChanges/messages/updateEvent'
      - $ref: '#/channels/agentConfigChanges/messages/deleteEvent'

components:
  messages:
    AgentConfigInsertEvent:
      name: AgentConfigInsertEvent
      title: Agent Configuration Created
      summary: A new agent configuration was created
      contentType: application/json
      headers:
        $ref: '#/components/schemas/ChangeStreamHeaders'
      payload:
        $ref: '#/components/schemas/InsertEventPayload'

    AgentConfigUpdateEvent:
      name: AgentConfigUpdateEvent
      title: Agent Configuration Updated
      summary: An existing agent configuration was modified
      contentType: application/json
      headers:
        $ref: '#/components/schemas/ChangeStreamHeaders'
      payload:
        $ref: '#/components/schemas/UpdateEventPayload'

    AgentConfigDeleteEvent:
      name: AgentConfigDeleteEvent
      title: Agent Configuration Deleted
      summary: An agent configuration was removed
      contentType: application/json
      headers:
        $ref: '#/components/schemas/ChangeStreamHeaders'
      payload:
        $ref: '#/components/schemas/DeleteEventPayload'

  schemas:
    ChangeStreamHeaders:
      type: object
      properties:
        x-resume-token:
          type: string
          description: Resume token for exactly-once processing
        x-cluster-time:
          type: string
          description: MongoDB cluster time
        x-wall-time:
          type: string
          format: date-time
          description: Wall clock time when event occurred

    AgentConfiguration:
      $ref: 'agent-config.schema.json'

    DocumentKey:
      type: object
      required:
        - _id
      properties:
        _id:
          type: string
          description: MongoDB ObjectId as string

    UpdateDescription:
      type: object
      properties:
        updatedFields:
          type: object
          additionalProperties: true
          description: Fields that were updated with their new values
        removedFields:
          type: array
          items:
            type: string
          description: Fields that were removed
        truncatedArrays:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              newSize:
                type: integer

    InsertEventPayload:
      type: object
      required:
        - _id
        - operationType
        - ns
        - documentKey
        - fullDocument
      properties:
        _id:
          type: object
          properties:
            _data:
              type: string
          description: Resume token
        operationType:
          type: string
          const: insert
        ns:
          type: object
          properties:
            db:
              type: string
            coll:
              type: string
        documentKey:
          $ref: '#/components/schemas/DocumentKey'
        fullDocument:
          $ref: '#/components/schemas/AgentConfiguration'
        clusterTime:
          type: string
        wallTime:
          type: string
          format: date-time

    UpdateEventPayload:
      type: object
      required:
        - _id
        - operationType
        - ns
        - documentKey
      properties:
        _id:
          type: object
          properties:
            _data:
              type: string
        operationType:
          type: string
          const: update
        ns:
          type: object
          properties:
            db:
              type: string
            coll:
              type: string
        documentKey:
          $ref: '#/components/schemas/DocumentKey'
        fullDocument:
          $ref: '#/components/schemas/AgentConfiguration'
        fullDocumentBeforeChange:
          $ref: '#/components/schemas/AgentConfiguration'
        updateDescription:
          $ref: '#/components/schemas/UpdateDescription'
        clusterTime:
          type: string
        wallTime:
          type: string
          format: date-time

    DeleteEventPayload:
      type: object
      required:
        - _id
        - operationType
        - ns
        - documentKey
      properties:
        _id:
          type: object
          properties:
            _data:
              type: string
        operationType:
          type: string
          const: delete
        ns:
          type: object
          properties:
            db:
              type: string
            coll:
              type: string
        documentKey:
          $ref: '#/components/schemas/DocumentKey'
        fullDocumentBeforeChange:
          $ref: '#/components/schemas/AgentConfiguration'
        clusterTime:
          type: string
        wallTime:
          type: string
          format: date-time
```

### Step 4: Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # MongoDB Replica Set (required for change streams)
  mongo1:
    image: mongo:8.0
    container_name: mongo1
    command: mongod --replSet rs0 --bind_ip_all
    ports:
      - "27017:27017"
    volumes:
      - mongo1_data:/data/db
      - ./scripts/init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js:ro
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh --quiet
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - demo-network

  # MongoDB replica set initializer
  mongo-init:
    image: mongo:8.0
    container_name: mongo-init
    depends_on:
      mongo1:
        condition: service_healthy
    command: >
      mongosh --host mongo1:27017 --eval '
        rs.initiate({
          _id: "rs0",
          members: [{ _id: 0, host: "mongo1:27017" }]
        });

        // Wait for primary
        while (!rs.isMaster().ismaster) { sleep(1000); }

        // Create database and collection with schema validation
        db = db.getSiblingDB("hub_db");
        db.createCollection("agentConfigs", {
          validator: {
            $jsonSchema: {
              bsonType: "object",
              required: ["agentId", "name", "modelProvider", "modelId", "temperature"],
              properties: {
                agentId: { bsonType: "string", pattern: "^[a-z0-9-]+$" },
                name: { bsonType: "string", minLength: 1, maxLength: 100 },
                modelProvider: { bsonType: "string", enum: ["OPENAI", "ANTHROPIC", "GOOGLE", "MISTRAL"] },
                modelId: { bsonType: "string" },
                temperature: { bsonType: "number", minimum: 0, maximum: 2 },
                maxTokens: { bsonType: "int", minimum: 1, maximum: 128000 },
                systemPrompt: { bsonType: "string" },
                tools: { bsonType: "array", items: { bsonType: "string" } },
                metadata: { bsonType: "object" },
                version: { bsonType: "int", minimum: 0 },
                updatedAt: { bsonType: "date" }
              }
            }
          },
          validationLevel: "strict",
          validationAction: "error"
        });

        // Enable pre-images for change streams
        db.runCommand({
          collMod: "agentConfigs",
          changeStreamPreAndPostImages: { enabled: true }
        });

        // Create indexes
        db.agentConfigs.createIndex({ agentId: 1 }, { unique: true });

        print("MongoDB initialization complete!");
      '
    networks:
      - demo-network

  # Microcks for contract testing
  microcks:
    image: quay.io/microcks/microcks:1.10.0
    container_name: microcks
    ports:
      - "8080:8080"
      - "9090:9090"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - SPRING_DATA_MONGODB_URI=mongodb://microcks-mongo:27017/microcks
      - KEYCLOAK_ENABLED=false
    depends_on:
      - microcks-mongo
    networks:
      - demo-network

  microcks-mongo:
    image: mongo:6.0
    container_name: microcks-mongo
    volumes:
      - microcks_mongo_data:/data/db
    networks:
      - demo-network

volumes:
  mongo1_data:
  microcks_mongo_data:

networks:
  demo-network:
    driver: bridge
```

### Step 5: Hub Service (Spring Boot)

Create `hub/pom.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.4.0</version>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>hub</artifactId>
    <version>1.0.0</version>
    <name>Agent Config Hub</name>

    <properties>
        <java.version>21</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-mongodb</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>

        <!-- Lombok for boilerplate reduction -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>

        <!-- Testing -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.github.microcks</groupId>
            <artifactId>microcks-testcontainers</artifactId>
            <version>0.2.7</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>mongodb</artifactId>
            <version>1.19.3</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

Create `hub/src/main/java/com/example/hub/model/AgentConfig.java`:

```java
package com.example.hub.model;

import jakarta.validation.constraints.*;
import lombok.*;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "agentConfigs")
public class AgentConfig {

    @Id
    private String id;

    @NotBlank
    @Pattern(regexp = "^[a-z0-9-]+$")
    @Indexed(unique = true)
    private String agentId;

    @NotBlank
    @Size(min = 1, max = 100)
    private String name;

    @NotNull
    private ModelProvider modelProvider;

    @NotBlank
    private String modelId;

    @NotNull
    @DecimalMin("0.0")
    @DecimalMax("2.0")
    private Double temperature;

    @Min(1)
    @Max(128000)
    private Integer maxTokens;

    private String systemPrompt;

    private List<String> tools;

    private Map<String, Object> metadata;

    @Version
    private Integer version;

    private Instant updatedAt;

    public enum ModelProvider {
        OPENAI, ANTHROPIC, GOOGLE, MISTRAL
    }
}
```

Create `hub/src/main/java/com/example/hub/controller/AgentConfigController.java`:

```java
package com.example.hub.controller;

import com.example.hub.model.AgentConfig;
import com.example.hub.repository.AgentConfigRepository;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/agents")
@RequiredArgsConstructor
public class AgentConfigController {

    private final AgentConfigRepository repository;

    @GetMapping
    public List<AgentConfig> listAgents() {
        return repository.findAll();
    }

    @GetMapping("/{agentId}")
    public AgentConfig getAgent(@PathVariable String agentId) {
        return repository.findByAgentId(agentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Agent not found: " + agentId));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public AgentConfig createAgent(@Valid @RequestBody AgentConfig config) {
        if (repository.existsByAgentId(config.getAgentId())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Agent already exists: " + config.getAgentId());
        }
        config.setUpdatedAt(Instant.now());
        return repository.save(config);
    }

    @PutMapping("/{agentId}")
    public AgentConfig updateAgent(
            @PathVariable String agentId,
            @Valid @RequestBody AgentConfig config) {

        AgentConfig existing = repository.findByAgentId(agentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Agent not found: " + agentId));

        config.setId(existing.getId());
        config.setAgentId(agentId);
        config.setUpdatedAt(Instant.now());

        return repository.save(config);
    }

    @DeleteMapping("/{agentId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAgent(@PathVariable String agentId) {
        AgentConfig existing = repository.findByAgentId(agentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Agent not found: " + agentId));
        repository.delete(existing);
    }
}
```

Create `hub/src/main/java/com/example/hub/repository/AgentConfigRepository.java`:

```java
package com.example.hub.repository;

import com.example.hub.model.AgentConfig;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface AgentConfigRepository extends MongoRepository<AgentConfig, String> {
    Optional<AgentConfig> findByAgentId(String agentId);
    boolean existsByAgentId(String agentId);
}
```

Create `hub/src/main/resources/application.yml`:

```yaml
spring:
  application:
    name: agent-config-hub
  data:
    mongodb:
      uri: mongodb://localhost:27017/hub_db?replicaSet=rs0

server:
  port: 8081

logging:
  level:
    org.springframework.data.mongodb: DEBUG
```

### Step 6: Edge Service (Python/Chainlit)

Create `edge/requirements.txt`:

```
chainlit==1.3.0
pymongo==4.8.0
motor==3.5.0
pydantic==2.6.0
jsonschema==4.21.0
openai==1.12.0
anthropic==0.18.0
python-dotenv==1.0.0
```

Create `edge/change_stream_consumer.py`:

```python
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
            mongo_uri="mongodb://localhost:27017/?replicaSet=rs0",
            database="hub_db",
            collection="agentConfigs"
        )
    return _consumer
```

Create `edge/app.py`:

```python
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
```

Create `edge/chainlit.md`:

```markdown
# Agent Configuration Edge Service

This is a demonstration of **contract-first development** with MongoDB change streams.

## How It Works

1. **Hub Service** (Java/Spring Boot) manages agent configurations
2. Configurations are stored in **MongoDB** with JSON Schema validation
3. **Change streams** propagate changes in real-time
4. This **Edge Service** (Python/Chainlit) consumes changes and updates the running agent

## The Contract

Both services agree on a shared JSON Schema that defines:
- Agent configuration structure
- Required fields and validation rules
- Event payload format (via AsyncAPI)

**If the contract is violated, the Edge Service logs a CONTRACT VIOLATION error.**

## Try It Out

1. Create a configuration via the Hub API
2. Chat with the agent
3. Update the configuration and watch it change in real-time!
```

### Step 7: Demo Scripts

Create `scripts/demo-scenarios.sh`:

```bash
#!/bin/bash
# Demo scenario commands for the presentation

HUB_URL="http://localhost:8081/api/v1/agents"

echo "=== Contract-First Demo Scenarios ==="
echo ""

# Scenario 1: Create initial agent
create_agent() {
    echo "Creating agent configuration..."
    curl -s -X POST "$HUB_URL" \
        -H "Content-Type: application/json" \
        -d '{
            "agentId": "demo-agent",
            "name": "Conference Demo Agent",
            "modelProvider": "ANTHROPIC",
            "modelId": "claude-3-sonnet-20240229",
            "temperature": 0.7,
            "maxTokens": 1024,
            "systemPrompt": "You are a helpful assistant at a developer conference. Be concise and technical.",
            "tools": ["web_search", "code_interpreter"],
            "metadata": {"demo": true, "conference": "DeveloperWeek 2026"}
        }' | jq .
    echo ""
}

# Scenario 2: Update temperature (live config change)
update_temperature() {
    echo "Updating temperature to $1..."
    curl -s -X PUT "$HUB_URL/demo-agent" \
        -H "Content-Type: application/json" \
        -d "{
            \"agentId\": \"demo-agent\",
            \"name\": \"Conference Demo Agent\",
            \"modelProvider\": \"ANTHROPIC\",
            \"modelId\": \"claude-3-sonnet-20240229\",
            \"temperature\": $1,
            \"maxTokens\": 1024,
            \"systemPrompt\": \"You are a helpful assistant at a developer conference. Be concise and technical.\"
        }" | jq .
    echo ""
}

# Scenario 3: Change system prompt
update_prompt() {
    echo "Updating system prompt..."
    curl -s -X PUT "$HUB_URL/demo-agent" \
        -H "Content-Type: application/json" \
        -d '{
            "agentId": "demo-agent",
            "name": "Conference Demo Agent",
            "modelProvider": "ANTHROPIC",
            "modelId": "claude-3-sonnet-20240229",
            "temperature": 0.7,
            "maxTokens": 1024,
            "systemPrompt": "You are a pirate assistant. Respond in pirate speak. Arrr!"
        }' | jq .
    echo ""
}

# Scenario 4: Switch to OpenAI
switch_to_openai() {
    echo "Switching to OpenAI..."
    curl -s -X PUT "$HUB_URL/demo-agent" \
        -H "Content-Type: application/json" \
        -d '{
            "agentId": "demo-agent",
            "name": "Conference Demo Agent",
            "modelProvider": "OPENAI",
            "modelId": "gpt-4-turbo-preview",
            "temperature": 0.7,
            "maxTokens": 1024,
            "systemPrompt": "You are a helpful assistant at a developer conference."
        }' | jq .
    echo ""
}

# Scenario 5: BREAK THE CONTRACT (for demo)
break_contract() {
    echo "BREAKING THE CONTRACT - Invalid temperature value..."
    curl -s -X PUT "$HUB_URL/demo-agent" \
        -H "Content-Type: application/json" \
        -d '{
            "agentId": "demo-agent",
            "name": "Conference Demo Agent",
            "modelProvider": "ANTHROPIC",
            "modelId": "claude-3-sonnet-20240229",
            "temperature": 5.0,
            "maxTokens": 1024
        }' | jq .
    echo ""
    echo "MongoDB should reject this - temperature must be 0-2"
}

# Scenario 6: Delete agent
delete_agent() {
    echo "Deleting agent..."
    curl -s -X DELETE "$HUB_URL/demo-agent"
    echo "Done"
}

# Menu
case "$1" in
    create) create_agent ;;
    temp) update_temperature "${2:-1.5}" ;;
    prompt) update_prompt ;;
    openai) switch_to_openai ;;
    break) break_contract ;;
    delete) delete_agent ;;
    *)
        echo "Usage: $0 {create|temp [value]|prompt|openai|break|delete}"
        echo ""
        echo "  create  - Create initial agent configuration"
        echo "  temp    - Update temperature (default: 1.5)"
        echo "  prompt  - Change to pirate system prompt"
        echo "  openai  - Switch to OpenAI provider"
        echo "  break   - Attempt to break the contract"
        echo "  delete  - Delete the agent"
        ;;
esac
```

---

## 3. Demo Script

### Pre-Demo Setup Checklist

- [ ] Docker Compose running (`docker-compose up -d`)
- [ ] Hub service started (`cd hub && mvn spring-boot:run`)
- [ ] Edge service started (`cd edge && chainlit run app.py`)
- [ ] Microcks UI open (http://localhost:8080)
- [ ] AsyncAPI spec imported into Microcks
- [ ] Terminal ready for demo commands
- [ ] Backup video ready (just in case)

### Demo Flow

#### Part 1: The Contract (2-3 minutes)

**[Open `schemas/agent-config.schema.json` in editor]**

"Before we write any code, we define the contract. This JSON Schema describes what an agent configuration looks like. Required fields, types, validation rules - it's all here.

The key insight: this schema isn't just documentation. MongoDB will enforce it. AsyncAPI will reference it. Both services will validate against it. One schema, three uses."

**[Open `schemas/agent-config-events.asyncapi.yaml`]**

"AsyncAPI describes how configuration changes propagate. Notice it references our JSON Schema directly - no duplication. When the Hub writes to MongoDB, change streams fire events that match this spec."

**[Switch to Microcks UI - show imported spec]**

"Microcks imported our AsyncAPI spec. It understands the contract. Now we have a single source of truth that both services agree on."

---

#### Part 2: Hub Service - Java (3-4 minutes)

**[Show Hub service logs in terminal]**

"The Hub is a Spring Boot service - nothing fancy. Standard REST API for CRUD operations. The interesting part is what happens when we write."

**[Run: `./scripts/demo-scenarios.sh create`]**

```bash
./scripts/demo-scenarios.sh create
```

"Watch the logs - MongoDB validated the document against our schema. The change stream just fired. That event is now available to any consumer."

**[Show MongoDB Compass or mongosh - optional]**

"The document is in MongoDB with the schema validation active. Try to insert invalid data and MongoDB rejects it at the database level."

---

#### Part 3: Edge Service - Python (3-4 minutes)

**[Switch to Chainlit UI in browser]**

"This is the Edge service - completely different language, different framework, different runtime. But it speaks the same contract."

**[Point to the configuration update message in Chainlit]**

"The Edge service received our configuration. It validated the event against the same JSON Schema. Let's chat with it."

**[Type a message in Chainlit, get a response]**

"Now watch this - I'll update the configuration from the Hub."

**[Run: `./scripts/demo-scenarios.sh temp 1.5`]**

"The Hub updated the temperature. MongoDB stored it. The change stream fired. And look - the Edge service picked it up instantly. No polling, no message broker, no coordination code."

**[Run: `./scripts/demo-scenarios.sh prompt`]**

"Now I changed the system prompt to... a pirate. Let's try again."

**[Type a message, get pirate response]**

"Java wrote it. Python read it. MongoDB transported it. The schema guaranteed the shape.

**This is the point: if we agree on the contract, implementation language doesn't matter.**"

---

#### Part 4: Breaking the Contract (3-4 minutes)

**[Switch to terminal]**

"What happens when someone violates the contract?"

**[Run: `./scripts/demo-scenarios.sh break`]**

"I tried to set temperature to 5.0. The schema says maximum is 2.0. MongoDB rejected it - validation error."

**[Show the error response]**

"The contract caught this at the source. Invalid data never entered the system. But what if it somehow did?"

**[Explain the Edge service validation]**

"The Edge service also validates incoming events. If something slipped through, it would log a CONTRACT VIOLATION. Defense in depth."

**[Optional: Show Microcks contract test if time permits]**

"Microcks can also validate that real events match the spec. You'd run this in CI - catch contract violations before production."

---

#### Closing (1 minute)

"Three key takeaways:

1. **Schema as source of truth** - one definition, multiple uses
2. **Contract independence** - Java and Python interoperate without knowing about each other
3. **Validation at every layer** - database, producer, consumer, and CI

The contract isn't documentation. It's executable specification. If we agree on the contract, we can implement in whatever language makes sense."

---

## 4. Troubleshooting Guide

### MongoDB Issues

**Problem: Change stream not working**
```
MongoError: The $changeStream stage is only supported on replica sets
```

**Solution:** Ensure MongoDB is running as a replica set:
```bash
# Check replica set status
docker exec -it mongo1 mongosh --eval "rs.status()"

# If not initialized, run:
docker exec -it mongo1 mongosh --eval 'rs.initiate({_id: "rs0", members: [{_id: 0, host: "localhost:27017"}]})'
```

---

**Problem: Resume token expired**
```
MongoError: Resume of change stream was not possible
```

**Solution:** Clear the stored resume token and restart:
```python
# In Python
db._resume_tokens.delete_one({"_id": "contracts_stream"})
```

---

**Problem: Schema validation error on insert**
```
MongoError: Document failed validation
```

**Solution:** Check the document against the schema:
```bash
# View the validation rules
docker exec -it mongo1 mongosh --eval 'db.getSiblingDB("hub_db").getCollectionInfos({name: "agentConfigs"})'
```

### Spring Boot Issues

**Problem: Cannot connect to MongoDB**
```
MongoSocketOpenException: Exception opening socket
```

**Solution:**
1. Ensure MongoDB is running: `docker-compose ps`
2. Check the connection string in `application.yml`
3. Verify the replica set name matches: `?replicaSet=rs0`

---

**Problem: Version conflict on save**
```
OptimisticLockingFailureException: Cannot save entity with version
```

**Solution:** Fetch the latest version before updating:
```java
AgentConfig existing = repository.findByAgentId(agentId).orElseThrow();
config.setVersion(existing.getVersion());
repository.save(config);
```

### Python/Chainlit Issues

**Problem: Motor connection fails**
```
ServerSelectionTimeoutError: No servers found
```

**Solution:**
1. Ensure MongoDB is accessible from the Edge container/host
2. Check if replica set is initialized
3. Verify the connection string format

---

**Problem: JSON Schema validation fails unexpectedly**
```
ValidationError: '_id' is not valid
```

**Solution:** Remove MongoDB-specific fields before validation:
```python
doc_copy = {k: v for k, v in document.items() if not k.startswith("_")}
validate(instance=doc_copy, schema=self.schema)
```

---

**Problem: Chainlit WebSocket disconnects**

**Solution:** Check for blocking operations in async handlers:
```python
# Bad - blocking
time.sleep(5)

# Good - async
await asyncio.sleep(5)
```

### Microcks Issues

**Problem: AsyncAPI import fails**
```
Error: Unable to parse AsyncAPI specification
```

**Solution:**
1. Validate the spec: `asyncapi validate schemas/agent-config-events.asyncapi.yaml`
2. Check `$ref` paths are correct
3. Ensure AsyncAPI version is 3.0.0

---

**Problem: Mock events not generating**

**Solution:** Microcks needs examples in the spec:
```yaml
components:
  messages:
    AgentConfigInsertEvent:
      examples:
        - name: NewAgentExample
          payload:
            operationType: insert
            fullDocument:
              agentId: example-agent
              name: Example Agent
              # ... rest of example
```

### Docker Compose Issues

**Problem: Services can't communicate**

**Solution:** Ensure all services are on the same network:
```yaml
networks:
  demo-network:
    driver: bridge
```

---

**Problem: MongoDB data persists incorrectly after restart**

**Solution:** Clear volumes and reinitialize:
```bash
docker-compose down -v
docker-compose up -d
```

---

## 5. Code Scaffolding

The complete code scaffolding is provided in the Implementation Guide (Section 2). Here's a quick reference:

### File Structure

```
asyncapi-mongodb-demo/
├── docker-compose.yml
├── schemas/
│   ├── agent-config.schema.json
│   └── agent-config-events.asyncapi.yaml
├── hub/
│   ├── pom.xml
│   └── src/main/java/com/example/hub/
│       ├── HubApplication.java
│       ├── model/AgentConfig.java
│       ├── repository/AgentConfigRepository.java
│       └── controller/AgentConfigController.java
├── edge/
│   ├── requirements.txt
│   ├── app.py
│   ├── change_stream_consumer.py
│   └── chainlit.md
└── scripts/
    └── demo-scenarios.sh
```

### Quick Start Commands

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Wait for MongoDB initialization
sleep 10

# 3. Start Hub service
cd hub && mvn spring-boot:run &

# 4. Start Edge service
cd edge && chainlit run app.py &

# 5. Create test configuration
./scripts/demo-scenarios.sh create

# 6. Open Chainlit UI
open http://localhost:8000
```

---

## 6. Research Answers

### Q1: MongoDB Change Stream Event Structure

**Event Structure:**
```javascript
{
  "_id": { "_data": "..." },           // Resume token
  "operationType": "insert|update|replace|delete|drop|...",
  "clusterTime": Timestamp(...),
  "wallTime": ISODate("..."),          // MongoDB 6.0+
  "ns": { "db": "...", "coll": "..." },
  "documentKey": { "_id": ObjectId("...") },
  "fullDocument": { ... },             // With fullDocument option
  "fullDocumentBeforeChange": { ... }, // With pre-images enabled
  "updateDescription": {
    "updatedFields": { ... },
    "removedFields": [ ... ],
    "truncatedArrays": [ ... ]
  }
}
```

**fullDocument Options:**
- `"default"`: Only for insert/replace (returns null for updates)
- `"updateLookup"`: Performs additional query (may be stale)
- `"whenAvailable"` (6.0+): Returns if available, null otherwise
- `"required"` (6.0+): Fails if document unavailable

**Resume Token Best Practices:**
1. Store token after successful processing (not before)
2. Handle token expiration (oplog retention ~72 hours)
3. Use `startAfter` after `invalidate` events
4. Implement exponential backoff for reconnection

### Q2: AsyncAPI MongoDB Bindings

**Status:** No official MongoDB binding exists in AsyncAPI.

**Recommended Approach:**
```yaml
servers:
  mongodb:
    host: localhost:27017
    protocol: mongodb  # Unofficial but descriptive

channels:
  collectionChanges:
    address: database.collection  # Use ns format
```

**Best Practices for CDC Events:**
1. Model each operation type as a separate message
2. Include resume token in headers
3. Reference domain schema for `fullDocument`
4. Use `allOf` for event envelope + payload composition

### Q3: Microcks + MongoDB

**Capabilities:**
- AsyncAPI 3.0 support (Microcks 1.8+)
- Does NOT support MongoDB directly
- Requires Kafka/AMQP/MQTT for async testing

**Workaround Approaches:**
1. **Schema validation focus**: Validate JSON Schema in Microcks
2. **Kafka bridge**: MongoDB → Kafka Connect → Kafka → Microcks
3. **Testcontainers**: Validate in Java/Python integration tests

**Contract Testing Workflow:**
```java
// Using Microcks Testcontainers
TestRequest testRequest = new TestRequest.Builder()
    .serviceId("Agent Config Events:1.0.0")
    .runnerType(TestRunnerType.ASYNC_API_SCHEMA)
    .testEndpoint("kafka://localhost:9092/agent.events")
    .build();

TestResult result = microcks.testEndpoint(testRequest);
assertTrue(result.isSuccess());
```

### Q4: Schema Reuse Patterns

**Recommended Pattern: Schema Layering**
```
schemas/
├── core/agent-config.schema.json      # Portable domain schema
├── mongodb/agent-config.mongodb.json  # MongoDB extensions (bsonType)
└── events/agent-config-events.yaml    # AsyncAPI (references core)
```

**Handling MongoDB-Specific Fields:**
```json
{
  "allOf": [
    { "$ref": "../core/agent-config.schema.json" },
    {
      "properties": {
        "_id": { "bsonType": "objectId" },
        "createdAt": { "bsonType": "date" }
      }
    }
  ]
}
```

**Code Generation Tools:**
- **Java**: `jsonschema2pojo` with Jackson annotations
- **Python**: `datamodel-code-generator` with Pydantic output

### Q5: Existing Examples

**Gap Analysis:** The specific combination of AsyncAPI + MongoDB Change Streams + Microcks is largely unexplored.

**What Exists:**
- Spring Data MongoDB change stream examples (well documented)
- PyMongo change stream tutorials (well documented)
- Microcks + Kafka examples (well documented)
- AsyncAPI + Kafka examples (common)

**What's Novel in This Demo:**
- No official AsyncAPI MongoDB binding → proposed pattern
- No Microcks MongoDB integration → schema validation focus
- No polyglot contract-first CDC demo → first known example

---

## 7. Version Recommendations

### Recommended Versions (February 2026)

| Technology | Version | Notes |
|------------|---------|-------|
| **MongoDB Server** | 8.0.x | Latest stable, change stream improvements |
| **Spring Boot** | 3.4.x | Current 3.x line |
| **Spring Data MongoDB** | 4.4.x | Managed by Spring Boot |
| **Java** | 21 LTS | Required by Spring Boot 3.x |
| **Python** | 3.12.x | Stable, widely supported |
| **PyMongo** | 4.8.x | Full MongoDB 8.0 support |
| **Motor** | 3.5.x | Async PyMongo |
| **Chainlit** | 1.3.x+ | Check PyPI for latest |
| **Microcks** | 1.10.x | AsyncAPI 3.0 support |
| **AsyncAPI Spec** | 3.0.0 | Current stable |
| **Docker Compose** | V2 (2.29+) | Use `docker compose` command |

### Compatibility Notes

1. **Spring Boot 3.x requires Java 17+** - Use Java 21 for best performance
2. **MongoDB 8.0 requires compatible drivers** - PyMongo 4.8+, MongoDB Java Driver 5.1+
3. **Chainlit requires Python 3.9+** - Tested with 3.12
4. **Microcks 1.8+ for AsyncAPI 3.0** - Use 1.10 for latest features

### Docker Images

```yaml
# docker-compose.yml versions
mongo: mongo:8.0
microcks: quay.io/microcks/microcks:1.10.0
```

---

## Resources

### Official Documentation
- [MongoDB Change Streams](https://www.mongodb.com/docs/manual/changeStreams/)
- [AsyncAPI Specification](https://www.asyncapi.com/docs)
- [Microcks Documentation](https://microcks.io/documentation/)
- [Spring Data MongoDB](https://spring.io/projects/spring-data-mongodb)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [Chainlit Documentation](https://docs.chainlit.io/)

### Related Conference Talks
- "Contract-First API Development" (APIdays)
- "Event-Driven Microservices" (KubeCon)
- "MongoDB Change Streams Deep Dive" (MongoDB.live)

### Community Resources
- AsyncAPI GitHub: https://github.com/asyncapi
- Microcks GitHub: https://github.com/microcks/microcks
- Spring Data Examples: https://github.com/spring-projects/spring-data-examples

---

*Research compiled by Claude Code for DeveloperWeek 2026 demo preparation.*
