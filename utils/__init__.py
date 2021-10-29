from collections import Callable
from dataclasses import dataclass
from typing import Union


@dataclass
class Operator:
    arg_name: str
    func: Callable
    data: Union[int, str, float]
    func_name: str
