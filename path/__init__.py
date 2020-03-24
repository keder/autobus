from os import sep, getcwd
from os.path import normpath, isabs, abspath, expanduser, relpath, join, basename, splitext, exists, getmtime
from typing import List, Union
from glob import glob
from dataclasses import dataclass
import enum
from pathlib import Path


class File:
    def __init__(self, name: str, parent: 'Directory' = None, extension: str = None) -> None:
        self.parent = parent
        self.name = "{name}.{ext}".format(name=name, ext=extension) if extension else name
    
    @property
    def extension(self):
        return self.split()[1]
    
    @property
    def basename(self):
        return self.split()[0]
    
    @property
    def exists(self) -> bool:
        return exists(self.absolute_path)
    
    @property
    def mtime(self):
        return getmtime(self.absolute_path)
    
    def touch(self):
        Path(self.absolute_path).touch()
    
    def split(self):
        return splitext(basename(self.name))
    
    @property
    def absolute_path(self) -> str:
        if self.parent is not None:
            return normpath(join(self.parent.absolute_path, self.name))
        raise AttributeError("Need parent to form absolute path")

    def __str__(self) -> str:
        if self.parent:
            return self.absolute_path
        else:
            return self.name

class Directory:
    @classmethod
    def cwd(cls) -> 'Directory':
        obj = cls(getcwd())
        return obj

    def __init__(self, path: str, parent: 'Directory' = None) -> None:
        self._path = normpath(path)
        if self._path[0] == '~':
            self._path = expanduser(self._path)
        if not isabs(self._path) and not parent:
            raise AttributeError("For relative paths parent dir should be specified")
        self.parent = parent
        
    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, value: str):
        self._path = normpath(value)
        if self._path[0] == '~':
            self._path = expanduser(self._path)

    @property
    def absolute_path(self) -> str:
        if isabs(self.path):
            return self.path
        return normpath(join(self.parent.absolute_path, self.path))
    
    def get_relative(self, other: Union[str, 'Directory'] = None):
        if isinstance(other, self.__class__):
            other = other.absolute_path
        other = other or getcwd()
        return relpath(self.absolute_path, other)
    
    def glob(self, pattern: str):
        return glob(join(self.absolute_path, pattern))
    
    def create(self):
        Path(self.absolute_path).mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return self.absolute_path

def check_files_exist(file_list: List[File]) -> bool:
    for file in file_list:
        if not file.exists:
            return False
    return True

def get_least_mtime(file_list: List[File]) -> float:
    result = None
    for file in file_list:
        mtime = file.mtime
        if result is None or mtime < result:
            result = mtime
    return result or 0.0

def get_most_mtime(file_list: List[File]) -> float:
    result = None
    for file in file_list:
        mtime = file.mtime
        if result is None or mtime > result:
            result = mtime
    return result or 0.0
