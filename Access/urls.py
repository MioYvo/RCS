# coding=utf-8
# __author__ = 'Mio'
from Access.handler.record import AccessHandler
from Access.handler.event import EventHandler

urls = [
    (r"/api/v1/access", AccessHandler),
    (r"/api/v1/event", EventHandler),
]
