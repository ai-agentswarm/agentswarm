# Large Language Models (LLMs)

The `LLM` class is the interface between Agentswarm and the various AI model providers.

## The Abstract Concept

Agentswarm is model-agnostic. The `LLM` abstract base class defines a standard way to:
1.  **Generate text**: Given a list of messages.
2.  **Handle Tools**: define function definitions (schemas) and parse tool calls from the model's response.

By implementing this interface, you can add support for *any* model provider that supports function calling (or even emulate it).

::: agentswarm.llms.LLM

## Implementing a Custom Provider

To add a new provider (e.g., Anthropic, OpenAI, local Llama), create a subclass of `LLM` and implement `generate`.

```python
from agentswarm.datamodels import Message, LLMFunction
from agentswarm.llms import LLM, LLMOutput

class MyCustomLLM(LLM):
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.client = ... # Initialize your client
        self.model = model_name

    async def generate(self, messages: list[Message], functions: list[LLMFunction] = None) -> LLMOutput:
        # 1. Convert Agentswarm Messages to provider format
        # 2. Convert LLMFunctions to provider tool schemas
        # 3. Call the API
        # 4. Parse the response into LLMOutput (text + function_calls)
        pass
```

## Supported Providers

Agentswarm currently includes support for Gemini.

### Gemini

The `GeminiLLM` implementation connects to Google's Vertex AI or Generative AI SDKs.

::: agentswarm.llms.GeminiLLM
