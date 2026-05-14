# ReAct Agent

The `ReActAgent` is the most powerful agent type in the framework, implementing the **Reasoning and Acting** loop.

## How it Works

The ReAct agent operates in a loop:

1.  **Context Construction**: It gathers the conversation history and a special System Prompt that defines its operational rules (parallel execution, thinking first, etc.).

2.  **Tool Discovery**: It looks at the list of `available_agents` (tools) and converts them into function definitions for the LLM.

3.  **Generation**: It sends the context to the LLM.

4.  **Execution**:
    *   If the LLM calls the **Thinking Tool** (parallel to others), the thought is recorded.
    *   If the LLM calls other tools, they are executed **in parallel** (up to a concurrency limit).

5.  **Recursion**: The results are added back to the context, and the loop repeats until the LLM produces a final answer or the max iterations are reached.

## Implementation Details

When you subclass `ReActAgent`, you typically only need to define:
- `get_llm()`: Which LLM to use.
- `available_agents()`: Which tools (other BaseAgents) this agent can use.

```python
class MyOrchestrator(ReActAgent):
    def get_llm(self, user_id: str):
        return GeminiLLM()
        
    def available_agents(self, user_id: str):
        return [
            SearchAgent(),
            DatabaseAgent(),
            # ...
        ]
```

By default, the ReActAgent will use the `ThinkingAgent` as the thinking tool. Its implementation is streightforward, and is necessary to improve the performance of the reasoning loop.
It is possible to override its implementation by subclassing it and providing a custom implementation of the `get_thinking_agent()` method.
For example:

```python
class ResponsiveThinkingAgent(ThinkingAgent):
    async def execute(
        self, user_id: str, context: Context, input_args: ThinkingInput
    ) -> ThoughtResponse:
        context.emit_feedback(input_args.reasoning)
        return await super().execute(user_id, context, input_args)
```

And then use it in your ReActAgent:

```python
class MyOrchestrator(ReActAgent):
    def get_thinking_agent(self):
        return ResponsiveThinkingAgent()
```

In this example, the `ResponsiveThinkingAgent` emits a feedback message to the user, showing the reasoning process in real-time.

## Lifecycle Hooks

### `on_agent_result`

The `on_agent_result` hook is called after each agent execution completes successfully within the ReAct loop. Override it in your subclass to inspect, log, or react to agent results without modifying the core execution flow.

**Signature:**

```python
async def on_agent_result(
    self, user_id: str, context: Context, agent_id: str, result
) -> None:
```

**Parameters:**

| Parameter  | Type      | Description                                                                 |
|------------|-----------|-----------------------------------------------------------------------------|
| `user_id`  | `str`     | The user ID for the current execution.                                      |
| `context`  | `Context` | The current execution context (with access to store, tracing, etc.).        |
| `agent_id` | `str`     | The ID of the agent that was executed.                                       |
| `result`   | `Any`     | The result returned by the agent (`KeyStoreResponse`, `StrResponse`, etc.). |

**Example: Logging agent executions**

```python
class MyOrchestrator(ReActAgent):
    async def on_agent_result(self, user_id, context, agent_id, result):
        print(f"Agent '{agent_id}' completed for user '{user_id}' with result: {result}")
```

**Example: Tracking usage metrics**

```python
class MetricsOrchestrator(ReActAgent):
    def __init__(self):
        super().__init__()
        self.execution_count = {}

    async def on_agent_result(self, user_id, context, agent_id, result):
        self.execution_count[agent_id] = self.execution_count.get(agent_id, 0) + 1
```

**Example: Conditional side-effects based on result type**

```python
from agentswarm.datamodels import KeyStoreResponse

class NotifyingOrchestrator(ReActAgent):
    async def on_agent_result(self, user_id, context, agent_id, result):
        if isinstance(result, KeyStoreResponse):
            # Notify external system when data is stored
            await notify_data_stored(user_id, result.key, result.description)
```

!!! note
    The hook is called with the **parent** context (not the iteration context), giving you access to the full execution state. If the agent execution raises an exception, the hook is **not** called—the error is handled separately and reported back to the LLM.


## API Reference

::: agentswarm.agents.ReActAgent
