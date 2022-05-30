from dataclasses import dataclass
from datetime import timedelta
from typing import Union, Callable


@dataclass
class Operator:
    arg_name: str
    func: Callable
    data: Union[int, str, float, timedelta]
    func_name: str
