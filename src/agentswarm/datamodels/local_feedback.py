from typing import Callable, Set
from .feedback import Feedback, FeedbackSystem
import logging

logger = logging.getLogger("agentswarm.datamodels.local_feedback")


class LocalFeedbackSystem(FeedbackSystem):
    """
    The LocalFeedbackSystem implements a simple in-memory feedback system
    using a list of subscription callbacks.
    """

    def __init__(self):
        self._subscriptions: Set[Callable[[Feedback], None]] = set()

    def push(self, feedback: Feedback):
        """
        Pushes a feedback event to all subscribers.
        """
        for callback in self._subscriptions:
            try:
                callback(feedback)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    def subscribe(self, callback: Callable[[Feedback], None]):
        """
        Adds a callback to the feedback subscriptions.
        """
        self._subscriptions.add(callback)
