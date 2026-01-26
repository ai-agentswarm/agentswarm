class AgentSwarmError(Exception):
    """Base class for exceptions in this module."""

    pass


class RemoteExecutionNotSupportedError(AgentSwarmError):
    """Exception raised when a component does not support remote execution serialization."""

    pass
