# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/31/21 9:13 AM
from typing import Dict, Union, Type

from model.event import Event
from model.record import Record
from model.rule import Rule


COLL_MAPPING: Dict[str, Type[Union[Event, Record, Rule]]] = {
    Event.collection.name: Event,
    Record.collection.name: Record,
    Rule.collection.name: Rule
}
