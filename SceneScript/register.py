import functools
# scene_scripts = dict()
#
#
# def scripts(func):
#     if not scene_scripts.get(func.__name__):
#         scene_scripts[func.__name__] = func
#
#     @functools.wraps(func)
#     def wrapper(*args, **kw):
#         return func(*args, **kw)
#     return wrapper


class ScriptsManager:
    def __init__(self):
        self.scene_scripts = {}

    def register(self, func):
        if not self.scene_scripts.get(func.__name__):
            self.scene_scripts[func.__name__] = func

        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        return wrapper


scripts_manager = ScriptsManager()
