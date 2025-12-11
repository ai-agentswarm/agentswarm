from abc import abstractmethod
from typing import TypeVar, Generic, get_args

from pydantic import BaseModel
from ..datamodels import Context


InputType = TypeVar('InputType', bound=BaseModel)
OutputType = TypeVar('OutputType', bound=BaseModel)


class BaseAgent(Generic[InputType, OutputType]):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def description(self, user_id: str) -> str:
        pass

    @abstractmethod
    async def execute(self, user_id: str, context: Context, input: InputType = None) -> OutputType:
        pass

    def _get_generic_type(self, index: int):
        """
        Obtains the concrete type of the generic at the specified index (0 for InputType, 1 for OutputType).
        Works by inspecting __orig_bases__ of the class at runtime.
        """
        for base in getattr(self.__class__, "__orig_bases__", []):
            origin = getattr(base, "__origin__", None)
            if origin is BaseAgent or issubclass(origin, BaseAgent):
                args = get_args(base)
                if args and len(args) > index:
                    return args[index]
        return None

    def input_parameters(self) -> dict:
        input_type = self._get_generic_type(0)
        if input_type and hasattr(input_type, 'model_json_schema'):
            schema = input_type.model_json_schema()
            schema.pop('title', None)
            return schema
        return {}
    
    def output_parameters(self) -> dict:
        output_type = self._get_generic_type(1)
        if output_type and hasattr(output_type, 'model_json_schema'):
            schema = output_type.model_json_schema()
            schema.pop('title', None)
            return schema
        return {}