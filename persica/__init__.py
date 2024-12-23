import inspect
import logging
import os
from collections.abc import Iterable, Iterator
from importlib import import_module
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Type, TypedDict, TypeVar, Union

logger = logging.Logger("persica")


class _NoneInstantiate:
    pass


NoneInstantiate = _NoneInstantiate


class BaseConfig:
    pass


class BaseComponent:
    __is_component__: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs):
        cls.__is_component__ = kwargs.get("component", True)


COMPONENT = TypeVar("COMPONENT", bound=BaseComponent)
CONFIG = TypeVar("CONFIG", bound=TypedDict)


class NoSuchParameterException(Exception):
    pass


class Factor:
    def __init__(self, paths: Iterable[str], root: str | None = None, kwargs: Iterable[object] | None = None):
        if root is None:
            self.root = os.getcwd()
        else:
            self.root = root
        self.paths = paths
        self.components: dict[type[BaseComponent], type[NoneInstantiate] | BaseComponent] = {}
        self.kwargs: dict[type[object], object] = {}
        if kwargs is not None:
            for k in kwargs:
                original_class: type[object] = k.__class__
                self.kwargs[original_class] = k

    def gen_pkg(self, root, path: Path) -> Iterator[str]:
        for p in path.iterdir():
            if not p.name.startswith("_"):
                if p.is_dir():
                    yield from self.gen_pkg(root, p)
                elif p.suffix == ".py":
                    yield str(p.relative_to(root).with_suffix("")).replace(os.sep, ".")

    def load_module(self) -> None:
        for _path in self.paths:
            new_path = _path.replace(".", os.sep)
            path = Path(self.root) / new_path
            for pkg in self.gen_pkg(self.root, path):
                logger.info("import module %s", pkg)
                try:
                    import_module(pkg)
                except Exception as e:
                    logger.info("import module error %s", pkg)
                    raise e

    def init_components(self, component: type[BaseComponent]) -> BaseComponent:
        logger.info("init component %s", component.__name__)
        params = {}
        try:
            signature = inspect.signature(component.__init__)
        except ValueError as exc:
            print(f"Module {component.__name__} get initialize signature error")
            raise exc
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            if parameter.default != inspect.Parameter.empty:
                params[name] = parameter.default
            else:
                params[name] = None
        for name, parameter in signature.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            annotation = parameter.annotation
            if issubclass(annotation, BaseComponent):
                instantiate = self.components.get(parameter.annotation)
            else:
                instantiate = self.kwargs.get(parameter.annotation)
            if instantiate is None:
                raise NoSuchParameterException(
                    f"无法找到 {component.__name__} 组件中 {name} 参数需要的 {annotation.__name__} 类型"
                )
            if instantiate == NoneInstantiate:
                instantiate = self.init_components(parameter.annotation)
            params[name] = instantiate
        component_instantiate = component(**params)
        self.components[component] = component_instantiate
        return component_instantiate

    def get_all_components(self, cls: type[BaseComponent] = BaseComponent) -> list[type[BaseComponent]]:
        sub_classes = cls.__subclasses__()
        all_sub_classes = sub_classes.copy()
        for subclass in sub_classes:
            all_sub_classes.extend(self.get_all_components(subclass))
        return all_sub_classes

    @staticmethod
    def get_all_sub_config() -> list[type[BaseConfig]]:
        return BaseConfig.__subclasses__()

    def install(self):
        self.load_module()
        components = self.get_all_components()
        for component in components:
            if component.__is_component__:
                self.components[component] = NoneInstantiate
        for key, value in self.components.items():
            if value == NoneInstantiate:
                self.init_components(key)

    def add_kwargs(self, k: object):
        original_class: type[object] = k.__class__
        self.kwargs[original_class] = k

    def get_component(self, key: type[COMPONENT]) -> COMPONENT:
        result = self.components.get(key)
        if isinstance(result, BaseComponent):
            return result
        raise KeyError(f"can not found {key.__name__}")

    def get_components(self, key: type[COMPONENT]) -> Iterator[COMPONENT]:
        for _, value in self.components.items():
            if isinstance(value, key):
                yield value
