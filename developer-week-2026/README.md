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
- [just](https://github.com/casey/just) (command runner, installed via mise)
- LLM API keys (Azure OpenAI and/or Anthropic)

## Setup

```
mise install
just infra
# Wait for MongoDB initialization (~10s)

# Terminal 1: Hub service
just hub

# Terminal 2: Edge service
export AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com"
export AZURE_OPENAI_API_KEY="<your-azure-openai-key>"
export AZURE_OPENAI_API_VERSION="2024-02-01"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o" # Azure deployment name
# Optional: Anthropic via Azure AI Foundry
export ANTHROPIC_FOUNDRY_API_KEY="<your-azure-foundry-api-key>"
export ANTHROPIC_FOUNDRY_RESOURCE="<your-foundry-resource-name>"
# Optional: defaults used only when no agent config exists yet
export EDGE_DEFAULT_AGENT_ID="edge-default-agent"
export EDGE_DEFAULT_AGENT_NAME="Edge Default Agent"
export EDGE_DEFAULT_AZURE_DEPLOYMENT="gpt-4.1"
just edge-install
just edge

# Terminal 3: Demo commands
just demo-create
```

## Available Commands

```
just              # List all commands
just infra        # Start MongoDB + Microcks
just infra-down   # Stop infrastructure
just infra-clean  # Stop + remove all data
just infra-logs   # Follow infrastructure logs
just hub          # Run Hub service (port 8081)
just hub-build    # Build Hub service
just edge-install # Install Edge dependencies
just edge         # Run Edge service (port 8000)
```

### Demo Scenarios

```
just demo-create          # Create initial agent config
just demo-list            # List all agents
just demo-prompt          # Switch to pirate prompt
just demo-openai          # Switch to Azure OpenAI provider
just demo-break           # Attempt contract violation (rejected by MongoDB)
just demo-delete          # Delete the agent
```

## Demo Flow

1. Show the contract: `schemas/agent-config.schema.json` and `schemas/agent-config-events.asyncapi.yaml`
2. Show Microcks UI: http://localhost:8080
3. Import both contracts into Microcks:
   - AsyncAPI: `schemas/agent-config-events.asyncapi.yaml`
   - OpenAPI: `schemas/agent-config-api.openapi.yaml`
4. In Microcks, open the OpenAPI operations (`GET/POST/PUT/DELETE /api/v1/agents`) and call out that payloads reference the same `agent-config.schema.json`
5. In Microcks, open the AsyncAPI and inspect:
   - Channel `agentConfigChanges`
   - Messages `AgentConfigInsertEvent`, `AgentConfigUpdateEvent`, `AgentConfigDeleteEvent`
   - Example payloads for each message
6. Call `just demo-create`, then show Chainlit receives the matching change and highlight the same payload shape in Microcks
7. Call `just demo-prompt`, then show how update payload examples document `updateDescription.updatedFields`
8. Break the contract: `just demo-break` -- MongoDB rejects invalid data because it enforces the generated contract validator
9. Key takeaway: one schema drives Java, Python, MongoDB validation, OpenAPI, and AsyncAPI documentation

Note: Microcks may visually classify the AsyncAPI artifact using a Kafka-style event icon/label even when `servers.protocol` is `mongodb`. That is a UI representation detail; your contract still documents MongoDB change streams correctly.

MongoDB validation uses `schemas/agent-config.mongodb.schema.json`, which is auto-generated from `schemas/agent-config.schema.json` by `just infra`.

## Edge Auto-Bootstrap

When Chainlit starts, Edge now ensures at least one valid agent configuration exists.
If MongoDB has no configs, Edge auto-creates a default one so you can chat immediately.

## Ports

| Service         | Port  |
|-----------------|-------|
| MongoDB         | 27017 |
| Hub API         | 8081  |
| Edge (Chainlit) | 8000  |
| Microcks        | 8080  |
