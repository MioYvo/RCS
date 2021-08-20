from collections import Callable
from dataclasses import dataclass


@dataclass
class Operator:
    arg_name: str
    func: Callable
    data: object
