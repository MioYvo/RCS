import asyncio
import functools
import threading
import time


def ttl_lru_cache(seconds: int, maxsize: int = 128, typed: bool = False):
    def wrapper_cache(func):
        wrapped_cache_func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        wrapped_cache_func.delta = seconds * 10 ** 9
        wrapped_cache_func.expiration = time.monotonic_ns() + wrapped_cache_func.delta

        @functools.wraps(wrapped_cache_func)
        def wrapped_func(*args, **kwargs):
            if not kwargs.pop('cache', True) or time.monotonic_ns() >= wrapped_cache_func.expiration:
                wrapped_cache_func.cache_clear()
                wrapped_cache_func.expiration = time.monotonic_ns() + wrapped_cache_func.delta
            return wrapped_cache_func(*args, **kwargs)

        wrapped_func.cache_info = wrapped_cache_func.cache_info
        wrapped_func.cache_clear = wrapped_cache_func.cache_clear
        return wrapped_func
    return wrapper_cache


class Cacheable:
    def __init__(self, co):
        self.co = co
        self.done = False
        self.result = None
        self.lock = asyncio.Lock()

    def __await__(self):
        with (yield from self.lock):
            if self.done:
                return self.result
            self.result = yield from self.co.__await__()
            self.done = True
            return self.result


def async_cache(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)
        return Cacheable(r)
    return wrapped


class ThreadSafeCacheable:
    def __init__(self, co):
        self.co = co
        self.done = False
        self.result = None
        self.lock = threading.Lock()

    def __await__(self):
        while True:
            if self.done:
                return self.result
            if self.lock.acquire(blocking=False):
                self.result = yield from self.co.__await__()
                self.done = True
                return self.result
            else:
                yield from asyncio.sleep(0.005)


def thread_safe_async_cache(f):
    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)
        return Cacheable(r)
    return wrapped
