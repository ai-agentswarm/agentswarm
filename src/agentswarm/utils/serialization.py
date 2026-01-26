from typing import Any, Dict, Type, TypeVar
import importlib

T = TypeVar("T")


def get_class_path(cls: Type) -> str:
    return f"{cls.__module__}.{cls.__name__}"


def load_class(class_path: str) -> Type:
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def serialize_component(component: Any) -> Dict[str, Any]:
    if component is None:
        return None
    return {
        "__class__": get_class_path(component.__class__),
        "config": component.to_dict(),
    }


def deserialize_component(data: Dict[str, Any], expected_type: Type[T]) -> T:
    if data is None:
        return None
    cls = load_class(data["__class__"])
    if not issubclass(cls, expected_type):
        raise TypeError(f"Class {cls} is not a subclass of {expected_type}")
    return cls.recreate(data["config"])
