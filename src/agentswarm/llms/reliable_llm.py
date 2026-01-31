import asyncio
import logging
from typing import List, Optional
from .llm import LLM, LLMFunction, LLMOutput
from ..datamodels.message import Message
from ..datamodels.feedback import FeedbackSystem

logger = logging.getLogger(__name__)


class ReliableLLM(LLM):
    """
    A wrapper around an LLM that adds timeout and retry mechanisms.
    """

    def __init__(
        self,
        llm: LLM,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        """
        Initialize the ReliableLLM.

        Args:
            llm (LLM): The base LLM implementation to wrap.
            timeout (float): Timeout in seconds for each request. Defaults to 30.0.
            max_retries (int): Maximum number of retries. Defaults to 3.
            retry_delay (float): Initial delay between retries in seconds. Defaults to 1.0.
            backoff_factor (float): Multiplier for the retry delay. Defaults to 2.0.
        """
        self.llm = llm
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor

    async def generate(
        self,
        messages: List[Message],
        functions: List[LLMFunction] = None,
        feedback: Optional[FeedbackSystem] = None,
    ) -> LLMOutput:
        """
        Generate a response from the wrapped LLM with timeout and retry mechanisms.
        """
        last_exception = None
        current_delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                # Use asyncio.wait_for to implement timeout
                return await asyncio.wait_for(
                    self.llm.generate(messages, functions, feedback),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                last_exception = Exception(f"Request timed out after {self.timeout}s")
                logger.warning(f"Attempt {attempt + 1} failed: Timeout")
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

            if attempt < self.max_retries:
                logger.info(f"Retrying in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= self.backoff_factor
            else:
                logger.error("Max retries reached.")

        raise last_exception
