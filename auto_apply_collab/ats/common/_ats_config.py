import collections.abc
import importlib
import importlib.util
import logging
import pkgutil
import sys
import typing
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def lazy_import(name):
    spec = importlib.util.find_spec(name)
    if spec is None:
        logger.warning(f"Could not find module {name}")
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


template = lazy_import("ats.template")


class ATSRegistry(collections.abc.Mapping):
    # Inner class for storing ats related data
    class ATSData:
        def __init__(self, ats_name, ats_module, *args: str):
            self.ats_name = ats_name
            self.ats_module = ats_module
            self.alternative_names = list(args)
            # Don't fetch anything from ats_module until it is needed. Otherwise, lazy_import will be useless
            self.all_names = list(set([self.ats_name] + self.alternative_names))

        def __repr__(self):
            """
            :return: string representation of ATSData

            It checks self for instance attributes and loops through them to return a string representation of the
            object
            """
            return f"{type(self).__name__}({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())})"

        def search(self, search_term: str) -> bool:
            """
            search_term: string to search for in self
            """
            for ats_name in self.all_names:
                if search_term in ats_name or ats_name in search_term:
                    return True
            return False

    def __init__(self):
        self._ats = {}
        self._registered = False
        if not self._registered:
            self.register()

    def __getitem__(self, key):
        if not self._registered:
            self.register()
        return self._ats[key]

    def __iter__(self):
        if not self._registered:
            self.register()
        return iter(self._ats)

    def __len__(self):
        if not self._registered:
            self.register()
        return len(self._ats)

    def __repr__(self):
        return f"{type(self).__name__}({self._ats})"

    def register(self):
        # ats_module = importlib.import_module("ats")
        spec = importlib.util.find_spec("ats")
        modules = list(
            filter(
                lambda x: x.ispkg is True,
                pkgutil.walk_packages(spec.submodule_search_locations),
            )
        )
        modules_to_register = [
            m
            for m in modules
            if importlib.util.find_spec(f"ats.{m.name}.__ats_register__")
        ]
        for module in modules_to_register:
            ats_register_module = importlib.import_module(
                f"ats.{module.name}.__ats_register__"
            )
            entrypoint_module = lazy_import(
                f"ats.{module.name}.{ats_register_module.ENTRYPOINT_MODULE}"
            )
            ats_name = ats_register_module.ATS_NAME
            alternative_names = ats_register_module.ALTERNATIVE_NAMES
            self._ats.update(
                {
                    ats_name: self.ATSData(
                        ats_name, entrypoint_module, *alternative_names
                    )
                }
            )

        self._registered = True

    def get_ats_if_found(self, search_term: str) -> Optional[Union[Any, None]]:
        """
        :param search_term: string to search for in self
        :return: self if search_term is found in self, None otherwise

        It checks self for instance attributes and loops through them to see if search_term is found in any of them
        """
        for ats_name, ats_data in self._ats.items():
            ats_data: ATSRegistry.ATSData
            if ats_data.search(search_term):
                return ats_data
        return None


def search_ats(search_term: str):
    if typing.TYPE_CHECKING:
        return template
    ats_data: ATSRegistry.ATSData = ats_registry.get_ats_if_found(search_term)
    return ats_data.ats_module if ats_data else None


ats_registry: ATSRegistry = ATSRegistry()

if __name__ == "__main__":
    print(ats_registry)
    # print(get_ats("dice"))
    print(search_ats("dice"))
    print(template)
    print(ats_registry)
