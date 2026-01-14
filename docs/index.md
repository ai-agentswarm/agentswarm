# Welcome to Agentswarm

**Agentswarm** is a recursive, functional, and state-isolated Multi-Agent Framework.

It is designed to build complex, scalable agentic systems by composing small, focused agents.

## Key Features

- **Recursion**: Agents can be composed of other agents.
- **State Isolation**: Each agent execution has its own isolated context.
- **MCP Support**: Native integration with the Model Context Protocol (MCP) to connect to external tools.

## Quickstart

Install the library:

```bash
pip install agentswarm
```

Create a simple agent:

```python
from agentswarm.agents import ReActAgent

class MyAgent(ReActAgent):
    # ... implementation ...
    pass
```

Explore the documentation sections to learn more about the core concepts, available agents, and how to extend the framework.
