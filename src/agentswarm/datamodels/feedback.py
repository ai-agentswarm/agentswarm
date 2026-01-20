from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from pydantic import BaseModel


class Feedback(BaseModel):
    """
    The Feedback class represents a notification or a piece of feedback
    emitted during agent execution.
    """

    source: str
    payload: Any


class FeedbackSystem(ABC):
    """
    The FeedbackSystem class defines the interface for pushing and
    subscribing to feedback events.
    """

    @abstractmethod
    def push(self, feedback: Feedback):
        """
        Pushes a new feedback event.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, callback: Callable[[Feedback], None]):
        """
        Subscribes to feedback events.
        """
        raise NotImplementedError
