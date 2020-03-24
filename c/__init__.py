from autobus.base import GeneratorBase, TargetBase
from abc import abstractmethod
from autobus.path import File
from typing import List, Dict


class CCMixin:
    defines = []
    verbose = False

    @property
    def define_arg_list(self) -> list:
        return ["-D{0}".format(item) for item in self.defines]


class CCObjectFileGenerator(CCMixin, GeneratorBase):
    """This processor compiles source file to object file"""

    def __init__(self, input_file: 'File', output_file: 'File', command: str = None, external_libs: List[str] = None, defines: List[str] = None, flags: List[str] = None, verbose=False) -> None:
        super().__init__()
        self._cmd = command or "gcc"
        self.input_file = input_file
        self.output_file = output_file
        self.external_libs = external_libs or []
        self.defines = defines or []
        if verbose:
            self.verbose = True

    @property
    def input_files(self):
        return [self.input_file]

    @property
    def output_files(self):
        return [self.output_file]

    @property
    def cmd_list(self) -> list:
        result = [self._cmd, "-c", str(self.input_file)]
        if self.defines:
            result += self.define_arg_list
        if self.output_file:
            result += ["-o", str(self.output_file)]
        return result


class CCBinaryFileGenerator(CCMixin, GeneratorBase):
    """This processor compiles source files, links object files and libraries to executable"""

    def __init__(self, input_files: List[File], output_file: 'File', command: str = None, external_libs: List[str] = None, defines: List[str] = None, flags: List[str] = None, linker_flags: List[str] = None, verbose=False) -> None:
        super().__init__()
        self._cmd = command or "gcc"
        self.input_files = input_files
        self.output_file = output_file
        self.external_libs = external_libs or []
        self.defines = defines or []
        self.flags = flags or []
        self.linker_flags = linker_flags or []
        if verbose:
            self.verbose = True

    @property
    def output_files(self):
        return [self.output_file]

    @property
    def external_lib_arg_list(self):
        result = []
        for lib in self.external_libs:
            if File(lib).extension:
                result.append("-l:{}".format(lib))
            else:
                result.append("-l{}".format(lib))
        return result
    
    @property
    def linker_flag_arg_list(self) -> List[str]:
        return ["-Wl,{0}".format(flag) for flag in self.linker_flags]
        

    @property
    def cmd_list(self, **kwargs):
        result = [self._cmd]
        result += [str(file) for file in self.input_files]
        if self.verbose:
            result.append("-v")
        if self.defines:
            result += self.define_arg_list
        if self.external_libs:
            result += self.external_lib_arg_list
        if self.flags:
            result += self.flags
        if self.linker_flags:
            result += self.linker_flag_arg_list
        if self.output_file:
            result += ["-o", str(self.output_file)]
        return result

class CBinaryFileTarget(TargetBase):
    pass
