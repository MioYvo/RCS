# coding=utf-8
# __author__ = 'Mio'
from RuleEngine.handler.rule import RuleHandler, RuleIdHandler

urls = [
    (r"/api/v1/rule", RuleHandler),
    (r"/api/v1/rule/([\w-]+)", RuleIdHandler),
]
