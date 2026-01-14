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

## API Reference

::: agentswarm.agents.ReActAgent
