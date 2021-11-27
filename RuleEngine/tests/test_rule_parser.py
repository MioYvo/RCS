# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/30/21 6:55 PM

from utils.rule_operator import RuleParser


def test_rule_evaluate():
    ru = ['or', ['>', 1, 2], ['and', ['in_', 1, 1, 2, 3], ['>', 3, ['int', '2']]]]
    assert RuleParser(ru).evaluate() is True
