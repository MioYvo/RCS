from dataclasses import dataclass
from typing import Union, Callable


@dataclass
class Operator:
    arg_name: str
    func: Callable
    data: Union[int, str, float]
    func_name: str
