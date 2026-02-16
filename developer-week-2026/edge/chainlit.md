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
