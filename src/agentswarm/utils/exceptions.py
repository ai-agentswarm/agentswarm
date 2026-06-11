class AgentSwarmError(Exception):
    """Base class for exceptions in this module."""

    pass


class RemoteExecutionNotSupportedError(AgentSwarmError):
    """Exception raised when a component does not support remote execution serialization."""

    pass


class LLMLoopError(AgentSwarmError):
    """Exception raised when an LLM stream appears stuck in a repetition loop."""

    pass


class LLMOutputLimitError(AgentSwarmError):
    """Exception raised when an LLM stream exceeds the maximum allowed output size."""

    pass
