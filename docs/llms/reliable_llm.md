# Reliable LLM Wrapper

The `ReliableLLM` class is a wrapper designed to enhance any LLM implementation with built-in **timeout** and **retry** mechanisms. This is particularly useful for production environments where network reliability or LLM availability can vary.

## Features

- **Timeout**: Enforce a maximum execution time for each LLM request.
- **Retry Mechanism**: Automatically retry failed requests (due to timeout or other exceptions).
- **Exponential Backoff**: Increase the delay between retries to avoid overwhelming the service.

## Configuration

The `ReliableLLM` constructor accepts the following parameters:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `llm` | `LLM` | *Required* | The base LLM instance to wrap. |
| `timeout` | `float` | `30.0` | Timeout in seconds for each request. |
| `max_retries` | `int` | `3` | Maximum number of retries. |
| `retry_delay` | `float` | `1.0` | Initial delay between retries in seconds. |
| `backoff_factor` | `float` | `2.0` | Multiplier applied to the delay after each failure. |

## Usage Example

```python
from agentswarm.llms import GeminiLLM, ReliableLLM

# 1. Create your base LLM
base_llm = GeminiLLM(api_key="your-api-key")

# 2. Wrap it with ReliableLLM
reliable_llm = ReliableLLM(
    llm=base_llm,
    timeout=10.0,       # 10 seconds timeout
    max_retries=5,      # retry up to 5 times
    retry_delay=2.0     # start with 2 seconds delay
)

# 3. Use it exactly like any other LLM
# response = await reliable_llm.generate(messages)
```

## How it works

When `generate()` is called:
1. It attempts to call the wrapped LLM's `generate()` method using `asyncio.wait_for`.
2. If the request times out or an exception occurs, it logs a warning.
3. If the number of attempts is less than `max_retries`, it waits for the current delay and tries again.
4. The delay is multiplied by the `backoff_factor` after each failed attempt.
5. If all retries are exhausted, the last exception is raised.
