# Tracing

Tracing is the observability layer of Agentswarm. It allows you to peer inside the "black box" of agent execution, monitoring not just final outputs but the internal reasoning, tool calls, and state changes.

## The Abstract Concept

The `Tracing` class is an abstract contract (interface). The core framework makes calls to this interface at key moments:
- When an agent starts execution.
- When an agent finishes or errors.
- When a loop step (like a ReAct iteration) begins.
- When a tool result is received.

By implementing this interface, you can route these signals to any observability backend you prefer.

::: agentswarm.utils.tracing.Tracing

## Extensibility

You are not limited to local files. You can implement a `Tracing` subclass to send data to:
- **Datadog / New Relic**: For enterprise monitoring.
- **LangSmith / Langfuse**: For LLM-specific observability.
- **Console / Stdout**: For real-time streaming to the terminal.

### Example: Console Tracer

```python
from agentswarm.utils.tracing import Tracing
from agentswarm.datamodels import Context

class ConsoleTracing(Tracing):
    def trace_agent(self, context: Context, agent_id: str, arguments: dict):
        print(f"🚀 Starting Agent: {agent_id} with inputs: {arguments}")

    def trace_agent_result(self, context: Context, agent_id: str, result: any):
        print(f"✅ Agent {agent_id} completed: {result}")
    
    # ... implement other methods ...
```

## Local Tracing

The provided `LocalTracing` implementation writes trace events to JSON files on the local filesystem. This is the default used in examples and allows for post-execution analysis (e.g., using the included trace viewer).

::: agentswarm.utils.tracing.LocalTracing
