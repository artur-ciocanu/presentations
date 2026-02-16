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
- LLM API keys (OpenAI and/or Anthropic)

## Setup

```
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
just demo-temp 1.5        # Update temperature
just demo-prompt          # Switch to pirate prompt
just demo-openai          # Switch to OpenAI provider
just demo-break           # Attempt contract violation (rejected by MongoDB)
just demo-delete          # Delete the agent
```

## Demo Flow

1. Show the contract: `schemas/agent-config.schema.json` and `schemas/agent-config-events.asyncapi.yaml`
2. Show Microcks UI: http://localhost:8080 (import AsyncAPI spec)
3. Create agent: `just demo-create` -- watch Edge receive the event
4. Chat with agent in Chainlit UI: http://localhost:8000
5. Live update: `just demo-temp 1.5` or `just demo-prompt` -- watch Edge reconfigure
6. Break the contract: `just demo-break` -- MongoDB rejects invalid data
7. Key takeaway: Java wrote it, Python read it, the schema guaranteed the shape

## Ports

| Service         | Port  |
|-----------------|-------|
| MongoDB         | 27017 |
| Hub API         | 8081  |
| Edge (Chainlit) | 8000  |
| Microcks        | 8080  |
