from typing import Iterable, List, Union
from dataclasses import dataclass
import collections.abc
import subprocess
from abc import ABCMeta, abstractmethod
from autobus.path import File, check_files_exist, get_least_mtime, get_most_mtime
from enum import Enum

class TraversalTree:
    """This is a class to non-recursevely traverse tree-like structures. It does not contain nodes itself. 
    Note that root itself is not used in traverse."""

    def __init__(self, root, children_field: str):
        self.root = root
        self.children_field = children_field
    
    def get_leaves(self) -> List:
        leaves = set()
        stack = [getattr(self.root, self.children_field)]

        while(stack):
            current = stack[-1].pop()
            if not stack[-1]:
                stack.pop()
            children = getattr(current, self.children_field)
            if callable(children):
                children = children()
            if not children:
                leaves.add(current)
            else:
                stack.append(children)
        
        return leaves

    
    def find(self, node) -> bool:
        stack = [getattr(self.root, self.children_field)]

        while(stack):
            current = stack[-1].pop()
            if current == node:
                return True
            if not stack[-1]:
                stack.pop()
            children = getattr(current, self.children_field)
            if callable(children):
                children = children()
            if children:
                stack.append(children)
        
        return False


class GeneratorBase(metaclass=ABCMeta):
    imitate = False

    def __init__(self, **kwargs) -> None:
        self.popen_kwargs = dict(stdin=None,
                                 input=None,
                                 stdout=None,
                                 stderr=None,
                                 capture_output=False,
                                 shell=False,
                                 cwd=None,
                                 timeout=None,
                                 check=False,
                                 encoding=None,
                                 errors=None,
                                 text=None,
                                 env=None,
                                 universal_newlines=None
                                 )
        self.popen_kwargs.update(kwargs)

    def _execute(self, *args, **kwargs) -> None:
        """Runs command in a subprocess. This function is not for overload. Function passes all kwargs to subprocess.run"""
        print(self.cmd)
        if not self.imitate:
            subprocess.run(*args, **kwargs)

    def execute(self, **kwargs) -> None:
        """Runs command in a subprocess. This function is supposed to be overloaded. Make some preparations, compute command arguments etc before run here."""
        new_kwargs = {}
        new_kwargs.update(self.popen_kwargs)
        new_kwargs.update(kwargs)
        self._execute(self.cmd_list, **new_kwargs)

    @property
    @abstractmethod
    def cmd_list(self) -> list:
        pass

    @property
    def cmd(self) -> str:
        return " ".join(self.cmd_list)

    def __str__(self) -> str:
        return self.cmd

class Command(GeneratorBase):
    """This is the base class for custom shell command execution"""

    def __init__(self, *args, **kwargs) -> None:
        self._cmd = None
        self._cmd_list = None
        super().__init__(**kwargs)
        if len(args) == 1:
            self.cmd = args[0]
        elif len(args) > 1:
            self.cmd_list = list(args)
        else:
            raise AttributeError("Not enough arguments")

    @property
    def cmd(self) -> Union[str,  None]:
        if self._cmd is not None:
            return str(self._cmd)
        elif self._cmd_list is not None:
            return " ".join(self._cmd_list)
        return None

    @property
    def cmd_list(self) -> Union[Iterable, None]:
        if self._cmd is not None:
            return [self._cmd]
        elif self._cmd_list is not None:
            return self._cmd_list
        return None

    @cmd.setter
    def cmd(self, value: Union[str, Iterable]) -> None:
        if isinstance(value, str):
            self._cmd_list = None
            self._cmd = value
            self.popen_kwargs["shell"] = True
        else:
            raise TypeError(f"{self.__class__.__name__}.cmd should be str")

    @cmd_list.setter
    def cmd_list(self, value: Union[str, Iterable]) -> None:
        if isinstance(value, collections.abc.Iterable):
            self._cmd_list = value
            self._cmd = None
            self.popen_kwargs["shell"] = False
        else:
            raise TypeError(
                f"{self.__class__.__name__}.cmd_list should be Iterable")
    
    def execute(self, **kwargs):
        """Runs command in a subprocess. This function is supposed to be overloaded. Make some preparations, compute command arguments etc before run here."""
        if self.popen_kwargs["shell"]:
            self._execute(self.cmd, **kwargs)
        else:
            self._execute(self.cmd_list, **kwargs)

class TargetState(Enum):
    NOT_SELECTED = 0
    SELECTED = 1
    DONE = 2

class TargetBase(metaclass=ABCMeta):
    def __init__(self) -> None:
        self._dependencies = []
        self.dependees = []
        self.stages = []
        self.state = TargetState.NOT_SELECTED
    
    def build(self, force=False):
        for stage in self.stages:
            if not isinstance(stage, list):
                stage = [stage]
            # TODO add async generator execution
            for generator in stage:
                generator.execute()

    @property
    def input_files(self) -> List[File]:
        return []
    
    @property
    def output_files(self) -> List[File]:
        return []
    
    @property
    def selected_dependencies(self) -> List[TargetBase]:
        return [dependency.target for dependency in self._dependencies if dependency.selected]

    @property
    def dependencies(self) -> List[TargetBase]:
        return [dependency.target for dependency in self._dependencies]
    
    def add_dependencies(self, dependencies: List[TargetBase], selection_function=None):
        self._dependencies.append(Dependency.from_list(dependencies, self, selection_function))
    
    def output_files_exist(self) -> bool:
        return check_files_exist(self.output_files)
    
    def input_files_exist(self) -> bool:
        return check_files_exist(self.input_files)
    
    @property
    def input_files_most_mtime(self):
        return get_least_mtime(self.input_files)
    
    @property
    def output_files_least_mtime(self):
        return get_most_mtime(self.output_files)
    
    def is_rebuild_needed(self) -> bool:
        if not self.output_files or not self.output_files_exist():
            return True
        if not self.input_files or not self.input_files_exist():
            return True
        if self.input_files_most_mtime >= self.output_files_least_mtime:
            return True
        return False
    
    def check_output_files(self):
        for file in self.output_files:
            if not file.exists:
                raise FileNotFoundError(f"Output file \"{file}\" was not generated.")

class Dependency:
    def __init__(self, target: 'TargetBase', dependee: 'TargetBase', selection_function=None):
        self.target = target
        self.target.dependees.append(dependee)
        self.selection_function = selection_function
    
    @classmethod
    def from_list(cls, targets: List['TargetBase'], dependee: 'TargetBase', selection_function=None) -> List[Dependency]:
        return [cls(target, dependee, selection_function) for target in targets]
    
    def selected(self):
        return self.selection_function(self) if self.selection_function else True
