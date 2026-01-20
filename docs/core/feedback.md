# Feedback System

The Feedback System provides a mechanism for agents and LLMs to emit real-time notifications or streaming data during execution. This is particularly useful for notifying users about the agent's progress or for streaming LLM responses.

## Overview

The feedback system is based on an asynchronous push-subscribe pattern. Agents push `Feedback` objects to the system, and subscribers receive them via callbacks.

### Feedback Object

A `Feedback` object consists of:

-   **source**: A string identifying the origin of the feedback (e.g., "llm" or an agent ID).
-   **payload**: The content of the feedback, which can be any data type.

## FeedbackSystem Interface

The `FeedbackSystem` is an abstract base class that defines the protocol for feedback:

```python
class FeedbackSystem(ABC):
    @abstractmethod
    def push(self, feedback: Feedback):
        """Pushes a new feedback event."""
        pass

    @abstractmethod
    def subscribe(self, callback: Callable[[Feedback], None]):
        """Subscribes to feedback events."""
        pass
```

## LocalFeedbackSystem

Agentswarm includes a `LocalFeedbackSystem`, which is a simple in-memory implementation of the `FeedbackSystem`. It manages a set of local callbacks and notifies them whenever feedback is pushed.

## Usage

### In Context

The `Context` object optionally contains a `FeedbackSystem`. You can emit feedback directly from the context:

```python
context.emit_feedback(payload="Starting task...", source="my_agent")
```

### LLM Streaming

The `LLM.generate` method can optionally receive a `FeedbackSystem`. When provided, the LLM can use it to stream chunks of the generated response:

```python
feedback_system = LocalFeedbackSystem()
feedback_system.subscribe(lambda fb: print(fb.payload, end="", flush=True))

await llm.generate(messages=messages, feedback=feedback_system)
```

## API Reference

::: agentswarm.datamodels.Feedback
::: agentswarm.datamodels.FeedbackSystem
::: agentswarm.datamodels.LocalFeedbackSystem
