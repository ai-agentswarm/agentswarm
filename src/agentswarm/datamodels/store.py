from abc import ABC, abstractmethod

class Store(ABC):
    """
    The Store class defines a simple key/value API to access the store.
    The implementation can vary from a local dictionary, to a distributed remote store.
    """

    @abstractmethod
    def get(self, key: str) -> any:
        """
        Obtains the value associated with the given key.
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: any):
        """
        Sets the value associated with the given key.
        """
        raise NotImplementedError

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Checks if the store has a value associated with the given key.
        """
        raise NotImplementedError

    def items(self) -> dict[str, any]:
        """
        Returns all key-value pairs in the store.
        """
        raise NotImplementedError