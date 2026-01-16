# Base Agent

The `BaseAgent` is the fundamental unit of work in Agentswarm.

## The Abstract Concept

An Agent in Agentswarm is simply a class that:

1.  **Accepts Input**: Defined by a Pydantic model (`InputType`).

2.  **Performs Work**: The `execute` method, which can do anything—call an LLM, query a database, or run a calculation.

3.  **Produces Output**: Defined by a Pydantic model (`OutputType`).

4.  **Describes Itself**: Provides a name (`id`) and `description` so that *other* agents (specifically LLMs) know how to use it.

## Implementing a New Agent

To create a custom agent, inherit from `BaseAgent` and specify your input/output types.

```python
from pydantic import BaseModel
from agentswarm.agents import BaseAgent
from agentswarm.datamodels import Context

class MyInput(BaseModel):
    query: str

class MyAgent(BaseAgent[MyInput, StrResponse]): 
    # Specifying [InputType, OutputType] generics is CRITICAL 
    # for automatic schema generation.

    def id(self) -> str:
        return "my_agent"

    def description(self, user_id: str) -> str:
        return "Helps the user with X"

    async def execute(self, user_id: str, context: Context, input: MyInput = None) -> StrResponse:
        # Your logic here
        return StrResponse(value=f"Processed {input.query}")
```

## Standard Outputs

Agentswarm provides a set of predefined output models in `agentswarm.datamodels.responses`. Using these standard responses helps maintain consistency across your agents, especially when they are used as tools by a ReAct agent.

- **`VoidResponse`**: Use when the agent performs an action but returns no data (e.g., "Email sent").

- **`StrResponse`**: Use when the agent returns a simple string, that should be elaborated.

- **`KeyStoreResponse`**: Use when the agent stores a large object in the Store and returns only the key and a description. This prevents context pollution.

- **`ThoughtResponse`**: Used internally for reasoning steps.

### Example

```python
from agentswarm.datamodels import VoidResponse

class EmailAgent(BaseAgent[EmailInput, VoidResponse]):
    # ...
    async def execute(self, user_id, context, input):
        send_email(input)
        return VoidResponse()
```

## Error Handling

Agentswarm follows standard Python idioms for error handling. **If an agent encounters a problem that prevents it from completing its task, it should raise an exception.**

The framework (specifically the `ReActAgent` or other orchestrators) is designed to catch these exceptions and handle them appropriately—typically by reporting the error back to the LLM so it can decide how to recover (e.g., by trying a different tool or modifying inputs).

```python
    async def execute(self, user_id, context, input):
        if not input.valid:
             # This will be caught by the calling agent and presented as an error
             raise ValueError(f"Invalid input: {input}")
        # ...
```

## API Reference

::: agentswarm.agents.BaseAgent
