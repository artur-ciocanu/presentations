# Implementation Plan: Contract-First Demo with MongoDB Change Streams

**Date:** 2026-02-14
**Source:** `demo-app-research-results.md`
**Goal:** Demo reliability -- every phase has verification before moving on.

---

## What We're NOT Doing

- No `requirements.txt` (using `uv` / `pyproject.toml`)
- No bare `mvn` commands (using Maven Wrapper `./mvnw`)
- No manual version management (mise handles Java, Python, UV)
- No `scripts/demo-scenarios.sh` (Justfile IS the demo script)
- No Dockerfiles for hub/edge (running locally)
- No Microcks Testcontainers integration tests
- No Kafka bridge
- No code generation from schemas

---

## Phase 1: Project Tooling

### Overview
Set up mise for runtime version management and a Justfile skeleton. This ensures everyone (and the demo machine) uses identical tool versions.

### File: `mise.toml`

```toml
[tools]
java = "21"
python = "3.12"
uv = "latest"
```

### File: `justfile`

```just
# Contract-First Demo -- DeveloperWeek 2026

# Default: list available commands
default:
    @just --list

# --- Infrastructure ---

# Start MongoDB replica set and Microcks
infra:
    docker compose up -d

# Stop all infrastructure
infra-down:
    docker compose down

# Stop and remove all data volumes
infra-clean:
    docker compose down -v

# Show infrastructure logs
infra-logs:
    docker compose logs -f

# --- Hub Service (Java/Spring Boot) ---

# Run the Hub service
hub:
    cd hub && ./mvnw spring-boot:run

# Build the Hub service
hub-build:
    cd hub && ./mvnw clean package -DskipTests

# --- Edge Service (Python/Chainlit) ---

# Install Edge dependencies
edge-install:
    cd edge && uv sync

# Run the Edge service
edge:
    cd edge && uv run chainlit run app.py --port 8000

# --- Demo Scenarios ---

_hub_url := "http://localhost:8081/api/v1/agents"

# Create initial agent configuration
demo-create:
    curl -s -X POST {{ _hub_url }} \
        -H "Content-Type: application/json" \
        -d '{ \
            "agentId": "demo-agent", \
            "name": "Conference Demo Agent", \
            "modelProvider": "ANTHROPIC", \
            "modelId": "claude-3-sonnet-20240229", \
            "temperature": 0.7, \
            "maxTokens": 1024, \
            "systemPrompt": "You are a helpful assistant at a developer conference. Be concise and technical.", \
            "tools": ["web_search", "code_interpreter"], \
            "metadata": {"demo": true, "conference": "DeveloperWeek 2026"} \
        }' | jq .

# Update agent temperature (default: 1.5)
demo-temp value="1.5":
    curl -s -X PUT {{ _hub_url }}/demo-agent \
        -H "Content-Type: application/json" \
        -d '{ \
            "agentId": "demo-agent", \
            "name": "Conference Demo Agent", \
            "modelProvider": "ANTHROPIC", \
            "modelId": "claude-3-sonnet-20240229", \
            "temperature": {{ value }}, \
            "maxTokens": 1024, \
            "systemPrompt": "You are a helpful assistant at a developer conference. Be concise and technical." \
        }' | jq .

# Switch system prompt to pirate mode
demo-prompt:
    curl -s -X PUT {{ _hub_url }}/demo-agent \
        -H "Content-Type: application/json" \
        -d '{ \
            "agentId": "demo-agent", \
            "name": "Conference Demo Agent", \
            "modelProvider": "ANTHROPIC", \
            "modelId": "claude-3-sonnet-20240229", \
            "temperature": 0.7, \
            "maxTokens": 1024, \
            "systemPrompt": "You are a pirate assistant. Respond in pirate speak. Arrr!" \
        }' | jq .

# Switch to OpenAI provider
demo-openai:
    curl -s -X PUT {{ _hub_url }}/demo-agent \
        -H "Content-Type: application/json" \
        -d '{ \
            "agentId": "demo-agent", \
            "name": "Conference Demo Agent", \
            "modelProvider": "OPENAI", \
            "modelId": "gpt-4-turbo-preview", \
            "temperature": 0.7, \
            "maxTokens": 1024, \
            "systemPrompt": "You are a helpful assistant at a developer conference." \
        }' | jq .

# BREAK the contract (invalid temperature)
demo-break:
    curl -s -X PUT {{ _hub_url }}/demo-agent \
        -H "Content-Type: application/json" \
        -d '{ \
            "agentId": "demo-agent", \
            "name": "Conference Demo Agent", \
            "modelProvider": "ANTHROPIC", \
            "modelId": "claude-3-sonnet-20240229", \
            "temperature": 5.0, \
            "maxTokens": 1024 \
        }' | jq .

# Delete the demo agent
demo-delete:
    curl -s -X DELETE {{ _hub_url }}/demo-agent

# List all agents
demo-list:
    curl -s {{ _hub_url }} | jq .
```

### Automated Verification

```bash
# Verify mise installs correct versions
mise install
java -version    # Should show 21.x
python --version # Should show 3.12.x
uv --version     # Should show latest

# Verify just works
just --list      # Should show all commands
```

### Manual Verification
- Run `mise install` and confirm no errors
- Run `just` and see the command list

### Checkpoint
Confirm: `java -version`, `python --version`, `uv --version`, and `just --list` all work.

---

## Phase 2: Contract Layer

### Overview
Create the JSON Schema (single source of truth) and AsyncAPI 3.0 spec. These two files define the entire contract between Hub and Edge.

### File: `schemas/agent-config.schema.json`

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

### File: `schemas/agent-config-events.asyncapi.yaml`

Full AsyncAPI 3.0.0 spec as defined in research document lines 276-521. Contains:
- Server definitions (development MongoDB on localhost:27017)
- Channel: `agentConfigChanges` on `hub_db.agentConfigs`
- Operations: `onAgentConfigChange` (receive)
- Messages: InsertEvent, UpdateEvent, DeleteEvent
- Schemas: ChangeStreamHeaders, AgentConfiguration ($ref to JSON Schema), DocumentKey, UpdateDescription, event payloads

### Automated Verification

```bash
# Validate JSON Schema is valid JSON
python -c "import json; json.load(open('schemas/agent-config.schema.json'))"

# Validate AsyncAPI YAML is valid YAML
python -c "import yaml; yaml.safe_load(open('schemas/agent-config-events.asyncapi.yaml'))"
```

### Manual Verification
- Open both files and confirm they match the research document
- Confirm `$ref: 'agent-config.schema.json'` in the AsyncAPI spec points to the schema

### Checkpoint
Both schema files exist, parse without errors, and the AsyncAPI spec references the JSON Schema.

---

## Phase 3: Infrastructure

### Overview
Docker Compose with MongoDB 8.0 replica set (required for change streams) and Microcks 1.10 for contract visualization. MongoDB init container configures the replica set, creates the collection with JSON Schema validation, and enables change stream pre-images.

### File: `docker-compose.yml`

```yaml
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

### Automated Verification

```bash
# Start infrastructure
just infra

# Wait for init to complete
docker compose logs -f mongo-init  # Watch for "MongoDB initialization complete!"

# Verify replica set
docker exec -it mongo1 mongosh --eval "rs.status().ok"  # Should print 1

# Verify collection with schema validation
docker exec -it mongo1 mongosh --eval 'db.getSiblingDB("hub_db").getCollectionInfos({name: "agentConfigs"})' | head -20

# Verify Microcks is running
curl -s http://localhost:8080/api/version | jq .
```

### Manual Verification
- Open http://localhost:8080 -- Microcks UI should load
- `docker compose ps` shows mongo1, microcks, microcks-mongo running (mongo-init exited 0)

### Checkpoint
MongoDB replica set is healthy, collection has schema validation, Microcks UI is accessible.

---

## Phase 4: Hub Service (Java/Spring Boot)

### Overview
REST API for CRUD operations on agent configurations. Uses Maven Wrapper so no global Maven install needed. Spring Data MongoDB handles persistence. When data is written, MongoDB change streams fire automatically.

### Directory Structure

```
hub/
├── .mvn/wrapper/          (generated by maven wrapper)
├── mvnw                   (generated)
├── mvnw.cmd               (generated)
├── pom.xml
└── src/
    └── main/
        ├── java/com/example/hub/
        │   ├── HubApplication.java
        │   ├── model/AgentConfig.java
        │   ├── repository/AgentConfigRepository.java
        │   └── controller/AgentConfigController.java
        └── resources/
            └── application.yml
```

### Steps

1. **Generate Maven Wrapper** in `hub/`:
   ```bash
   cd hub && mvn wrapper:wrapper -Dmaven=3.9.9
   ```
   This creates `mvnw`, `mvnw.cmd`, and `.mvn/wrapper/`.

2. **Create `hub/pom.xml`** -- as specified in research (lines 643-715), Spring Boot 3.4.0 parent, dependencies: spring-boot-starter-web, spring-boot-starter-data-mongodb, spring-boot-starter-validation, lombok.

3. **Create `hub/src/main/java/com/example/hub/HubApplication.java`**:
   ```java
   package com.example.hub;

   import org.springframework.boot.SpringApplication;
   import org.springframework.boot.autoconfigure.SpringBootApplication;

   @SpringBootApplication
   public class HubApplication {
       public static void main(String[] args) {
           SpringApplication.run(HubApplication.class, args);
       }
   }
   ```

4. **Create `hub/src/main/java/com/example/hub/model/AgentConfig.java`** -- as specified in research (lines 720-783). Document entity with validation annotations.

5. **Create `hub/src/main/java/com/example/hub/repository/AgentConfigRepository.java`** -- as specified in research (lines 861-873). MongoRepository with `findByAgentId` and `existsByAgentId`.

6. **Create `hub/src/main/java/com/example/hub/controller/AgentConfigController.java`** -- as specified in research (lines 787-857). REST endpoints: GET list, GET by id, POST create, PUT update, DELETE.

7. **Create `hub/src/main/resources/application.yml`** -- as specified in research (lines 877-891). Port 8081, MongoDB URI with replicaSet=rs0.

### Automated Verification

```bash
# Build (infra must be running for MongoDB connection)
just hub-build

# Start hub service
just hub  # In a separate terminal

# Test CRUD
curl -s http://localhost:8081/api/v1/agents | jq .          # [] empty list

curl -s -X POST http://localhost:8081/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"agentId":"test","name":"Test","modelProvider":"ANTHROPIC","modelId":"claude-3","temperature":0.5}' | jq .

curl -s http://localhost:8081/api/v1/agents/test | jq .      # Returns the agent

curl -s -X DELETE http://localhost:8081/api/v1/agents/test    # 204 No Content
```

### Manual Verification
- Hub starts without errors on port 8081
- POST creates a document, GET retrieves it, DELETE removes it
- Check MongoDB: `docker exec -it mongo1 mongosh --eval 'db.getSiblingDB("hub_db").agentConfigs.find()'`

### Checkpoint
Hub service starts, all CRUD operations work, data is visible in MongoDB.

---

## Phase 5: Edge Service (Python/Chainlit)

### Overview
Chat UI that consumes MongoDB change stream events and dynamically reconfigures itself. Uses `uv` for dependency management with `pyproject.toml`. Makes real LLM API calls (requires API keys).

### Directory Structure

```
edge/
├── pyproject.toml
├── app.py
├── change_stream_consumer.py
└── chainlit.md
```

### Steps

1. **Create `edge/pyproject.toml`**:
   ```toml
   [project]
   name = "edge-service"
   version = "1.0.0"
   description = "Edge Service - Chainlit AI Agent with MongoDB Change Stream Consumer"
   requires-python = ">=3.12"
   dependencies = [
       "chainlit>=1.3.0",
       "pymongo>=4.8.0",
       "motor>=3.5.0",
       "pydantic>=2.6.0",
       "jsonschema>=4.21.0",
       "openai>=1.12.0",
       "anthropic>=0.18.0",
       "python-dotenv>=1.0.0",
   ]
   ```

2. **Create `edge/change_stream_consumer.py`** -- as specified in research (lines 910-1097). Async consumer that:
   - Connects to MongoDB change stream on `hub_db.agentConfigs`
   - Validates incoming documents against the JSON Schema contract
   - Fires callbacks on insert/update/delete events
   - Handles reconnection with backoff

3. **Create `edge/app.py`** -- as specified in research (lines 1101-1257). Chainlit app that:
   - Registers a change stream callback on chat start
   - Displays config change notifications in real-time
   - Routes LLM calls to OpenAI or Anthropic based on current config
   - Shows helpful instructions when no config exists

4. **Create `edge/chainlit.md`** -- as specified in research (lines 1261-1287). Welcome page content.

5. **Create `edge/.env`** (not committed, document in README):
   ```
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

### Automated Verification

```bash
# Install dependencies
just edge-install

# Verify imports work
cd edge && uv run python -c "import chainlit; import motor; import jsonschema; print('OK')"

# Start edge service (infra + hub must be running)
just edge  # Opens on http://localhost:8000
```

### Manual Verification
- Chainlit UI loads at http://localhost:8000
- Welcome message shows "waiting for configuration" (if no agent created yet)
- After `just demo-create`, edge shows configuration notification
- Chat messages get real LLM responses

### Checkpoint
Edge service starts, connects to change stream, receives events, and responds via LLM.

---

## Phase 6: Demo Commands & README

### Overview
Finalize the Justfile with all demo scenario commands and write a README documenting the full workflow. The Justfile replaces any shell scripts -- everything runs via `just <command>`.

### File: `README.md`

```markdown
# Contract-First Development Demo

**DeveloperWeek 2026** -- "If we agree on the contract, implementation language doesn't matter."

## Architecture

- **Hub Service** (Java/Spring Boot) -- manages agent configurations via REST API
- **Edge Service** (Python/Chainlit) -- AI chat agent that reconfigures in real-time
- **MongoDB** -- stores configs with JSON Schema validation, emits change stream events
- **Microcks** -- contract visualization and validation
- **JSON Schema** -- single source of truth for the contract
- **AsyncAPI 3.0** -- documents the event-driven contract

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [mise](https://mise.jdx.dev/) (manages Java, Python, uv versions)
- [just](https://github.com/casey/just) (command runner)
- LLM API keys (OpenAI and/or Anthropic)

## Setup

    mise install
    just infra
    # Wait for MongoDB initialization (~10s)

    # Terminal 1: Hub service
    just hub

    # Terminal 2: Edge service
    just edge-install
    just edge

    # Terminal 3: Demo commands
    just demo-create

## Available Commands

    just              # List all commands
    just infra        # Start MongoDB + Microcks
    just infra-down   # Stop infrastructure
    just infra-clean  # Stop + remove all data
    just infra-logs   # Follow infrastructure logs
    just hub          # Run Hub service (port 8081)
    just hub-build    # Build Hub service
    just edge-install # Install Edge dependencies
    just edge         # Run Edge service (port 8000)

### Demo Scenarios

    just demo-create          # Create initial agent config
    just demo-list            # List all agents
    just demo-temp 1.5        # Update temperature
    just demo-prompt          # Switch to pirate prompt
    just demo-openai          # Switch to OpenAI provider
    just demo-break           # Attempt contract violation (rejected by MongoDB)
    just demo-delete          # Delete the agent

## Demo Flow

1. Show the contract: `schemas/agent-config.schema.json` and `schemas/agent-config-events.asyncapi.yaml`
2. Show Microcks UI: http://localhost:8080 (import AsyncAPI spec)
3. Create agent: `just demo-create` -- watch Edge receive the event
4. Chat with agent in Chainlit UI: http://localhost:8000
5. Live update: `just demo-temp 1.5` or `just demo-prompt` -- watch Edge reconfigure
6. Break the contract: `just demo-break` -- MongoDB rejects invalid data
7. Key takeaway: Java wrote it, Python read it, the schema guaranteed the shape

## Ports

| Service    | Port |
|------------|------|
| MongoDB    | 27017 |
| Hub API    | 8081  |
| Edge (Chainlit) | 8000 |
| Microcks   | 8080  |
```

### Automated Verification

```bash
# Full end-to-end test (infra + hub + edge must be running)
just demo-create                     # 201 Created
just demo-list                       # Shows 1 agent
just demo-temp 1.5                   # 200 OK, temperature updated
just demo-prompt                     # 200 OK, system prompt updated
just demo-break                      # 4xx error, contract violation
just demo-delete                     # 204 No Content
just demo-list                       # [] empty
```

### Manual Verification
- Walk through the full demo script from the research document (Section 3)
- Verify each scenario in Chainlit UI shows real-time updates
- Verify contract break is rejected with a clear error
- Confirm Microcks shows the imported AsyncAPI spec

### Checkpoint
All `just` commands work. Full demo runs end-to-end. README is accurate.

---

## Summary

| Phase | Creates | Depends On |
|-------|---------|------------|
| 1. Project Tooling | `mise.toml`, `justfile` | Nothing |
| 2. Contract Layer | `schemas/` (JSON Schema + AsyncAPI) | Nothing |
| 3. Infrastructure | `docker-compose.yml` | Phase 1 (just commands) |
| 4. Hub Service | `hub/` (Spring Boot + mvnw) | Phase 1, 3 |
| 5. Edge Service | `edge/` (Chainlit + uv) | Phase 1, 2, 3, 4 |
| 6. Demo & README | `README.md`, finalized `justfile` | All phases |
