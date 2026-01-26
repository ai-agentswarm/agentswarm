# Remote Agents

Remote Agents allow you to bridge different environments, enabling two primary scenarios:
1.  **Distributed Execution**: Running your own agents in a different environment (e.g., cloud, microservice) to scale compute or access specific resources.
2.  **Agent as a Service (Provider/Consumer)**: Consuming agents published by others. A provider can expose a "contract" (the agent's signature, input/output types, and endpoint), and a consumer can execute that agent remotely without knowing its internal implementation.

This makes Remote Agents a fundamental building block for **Agent Hubs** and cross-organizational agent collaboration.

## Using a Remote Agent

To use a remote agent, you typically use a proxy agent like `HttpRemoteAgent`. This agent acts as a local representative of the real agent running on a remote server.

```python
from agentswarm.agents import HttpRemoteAgent, RemoteExecutionMode

# Define a proxy for a remote agent
remote_agent = HttpRemoteAgent(
    base_url="https://api.my-agent-swarm.com",
    remote_agent_id="data_analyst_agent",
    mode=RemoteExecutionMode.SYNC
)

# Use it like any other agent
result = await remote_agent.execute(user_id, context, input_data)
```

## How It Works

1.  **Serialization**: The proxy agent serializes the `Context` (messages, store configuration, usage, etc.) and the `Input`.
2.  **Communication**: It sends the serialized data to the remote worker using a protocol (e.g., HTTP).
3.  **Remote Execution**: The worker deserializes the context, locates the real agent, and executes it.
4.  **State Sync**: After execution, the worker returns the result and the updated `Context`.
5.  **Local Update**: The proxy agent updates the local `Context` with changes from the remote execution (e.g., new messages, thoughts, or usage metrics) and returns the result.

## Protocols

For details on the underlying communication protocol, see the [Remote Protocol](../core/remote_protocol.md) documentation.

## Security Considerations

AgentSwarm is designed with security in mind:
- **No Secrets over the Wire**: Connection strings and API keys should never be serialized. Use reference-based configuration instead.
- **Worker Isolation**: Remote workers manage their own secrets and environment variables.
- **Fail-safe**: Local-only components (like `LocalStore`) cannot be serialized, preventing accidental data leaks.

For more details, see the [Security Pipeline](../core/remote_protocol.md#security-and-configuration).
