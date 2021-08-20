import functools
from .withdraw import single_withdrawal_amount_limit

scene_scripts = dict()

scene_scripts[single_withdrawal_amount_limit.__name__] = single_withdrawal_amount_limit


def scripts(func):
    if not scene_scripts.get(func.__name__):
        scene_scripts[func.__name__] = func

    @functools.wraps(func)
    def wrapper(*args, **kw):
        return func(*args, **kw)
    return wrapper
