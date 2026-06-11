# Reliable LLM Wrapper

The `ReliableLLM` class is a wrapper designed to enhance any LLM implementation with built-in robustness guards and a **retry** mechanism. This is particularly useful for production environments where network reliability or LLM behavior can vary.

It protects against three distinct failure modes, all observed live on the token stream through the `FeedbackSystem`:

1. **Inactivity timeout** — a request is aborted only when `timeout` seconds elapse *without a new token*. This is **not** a total-duration timeout: a legitimately long generation that keeps streaming tokens is never penalized. It catches the two cases that actually matter — a model that never starts responding (time-to-first-token), and a stream that stalls between chunks.
2. **Repetition-loop detection** — when a model "goes mad" and keeps emitting the same word/line/phrase, the tokens keep flowing, so the timeout would never trigger. A loop detector watches the stream and aborts as soon as a short pattern repeats consecutively too many times.
3. **Output cap (optional)** — a hard limit on the total number of emitted characters, as a last-resort bound on runaway generations.

Every aborted attempt is retried with exponential backoff, up to `max_retries` times.

## Features

- **Inactivity (idle) timeout**: abort only when no token is produced for `timeout` seconds.
- **Loop detection**: detect and abort degenerate repetition loops.
- **Output cap**: optionally bound the total output size.
- **Retry mechanism**: automatically retry aborted requests.
- **Exponential backoff**: increase the delay between retries to avoid overwhelming the service.

## Configuration

The `ReliableLLM` constructor accepts the following parameters:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `llm` | `LLM` | *Required* | The base LLM instance to wrap. |
| `timeout` | `float` | `30.0` | **Inactivity** timeout in seconds. A request is aborted only if this much time passes without a new token. |
| `max_retries` | `int` | `3` | Maximum number of retries. |
| `retry_delay` | `float` | `1.0` | Initial delay between retries in seconds. |
| `backoff_factor` | `float` | `2.0` | Multiplier applied to the delay after each failure. |
| `loop_detection` | `bool` | `True` | Enable repetition-loop detection. |
| `loop_min_repetitions` | `int` | `12` | Minimum consecutive repetitions of a pattern before a loop is declared. |
| `loop_max_pattern_length` | `int` | `256` | Longest repeating pattern (in characters) considered by the detector. |
| `max_output_chars` | `Optional[int]` | `None` | Hard cap on total emitted characters. `None` disables the cap. |

## Usage Example

```python
from agentswarm.llms import GeminiLLM, ReliableLLM

# 1. Create your base LLM
base_llm = GeminiLLM(api_key="your-api-key")

# 2. Wrap it with ReliableLLM
reliable_llm = ReliableLLM(
    llm=base_llm,
    timeout=10.0,              # abort if no token arrives for 10 seconds
    max_retries=5,             # retry up to 5 times
    retry_delay=2.0,           # start with 2 seconds delay
    loop_detection=True,       # abort on degenerate repetition loops
    loop_min_repetitions=12,   # a pattern repeated 12+ times is a loop
    max_output_chars=100_000,  # optional hard cap on output size
)

# 3. Use it exactly like any other LLM
# response = await reliable_llm.generate(messages)
```

## How it works

When `generate()` is called, each attempt runs the wrapped LLM concurrently with a watchdog. An internal proxy feedback (`_StreamGuard`) is always supplied to the wrapped LLM. For streaming-capable backends this also enables incremental token delivery, and it lets the watchdog observe the stream token by token:

1. Every token refreshes a `last_activity` timestamp. If `timeout` seconds pass without a new token, the attempt is aborted with a `TimeoutError` (inactivity timeout).
2. Token text is fed to a sliding-window loop detector. If a short pattern repeats consecutively at least `loop_min_repetitions` times, the attempt is aborted with an `LLMLoopError`.
3. If `max_output_chars` is set and the total emitted text exceeds it, the attempt is aborted with an `LLMOutputLimitError`.
4. On any abort, a warning is logged. If attempts remain, the wrapper waits for the current delay (multiplied by `backoff_factor` after each failure) and tries again.
5. If all retries are exhausted, the last exception is raised.

!!! note "Backends without token feedback"
    Loop detection and the output cap rely on observing the token stream. If the wrapped LLM does not emit token feedback at all, these guards are inactive and the inactivity timeout gracefully degrades to a total-duration timeout.

## Exceptions

| Exception | Raised when |
| :--- | :--- |
| `TimeoutError` | No token was received within the inactivity `timeout`. |
| `LLMLoopError` | The stream got stuck repeating the same pattern. |
| `LLMOutputLimitError` | The output exceeded `max_output_chars`. |

`LLMLoopError` and `LLMOutputLimitError` are defined in `agentswarm.utils.exceptions` and inherit from `AgentSwarmError`. All three are retried like any other failure; if every attempt aborts the same way, the last exception is propagated to the caller.
