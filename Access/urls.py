# coding=utf-8
# __author__ = 'Mio'
from Access.handler.record import RecordHandler
from Access.handler.event import EventHandler, EventIdHandler

urls = [
    (r"/api/v1/record", RecordHandler),
    (r"/api/v1/event", EventHandler),
    (r"/api/v1/event/([\w-]+)", EventIdHandler),
]
