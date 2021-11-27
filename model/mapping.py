# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/31/21 9:13 AM
from typing import Dict, Union, Type

# from model.event import Event
# from model.record import Record
# from model.rule import Rule

from model.odm import Event, Record, Rule


COLL_MAPPING: Dict[str, Type[Union[Event, Record, Rule]]] = {
    Event.__name__: Event,
    Record.__name__: Record,
    Rule.__name__: Rule
}
