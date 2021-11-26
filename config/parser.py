# @Time : 2021-11-26 11:41:34
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : parser.py
from config import PROJECT_NAME


def parse_consul_config(conf: str) -> dict:
    consul_conf = conf.split()
    assert consul_conf
    consuls_ = {}
    for cc in consul_conf:
        # "vdex#123@10.17.5.131:8500"
        rst = cc.rsplit(':')
        if len(rst) == 2:
            rst, port = rst
        else:
            rst, port = rst[0], 80

        # "vdex#123@10.17.5.131"
        rst = rst.rsplit('@')
        if len(rst) == 2:
            token, host = rst
        else:
            token, host = '', rst[0]

        # "vdex#123"
        rst = token.split('#')
        if len(rst) == 2:
            proj, token = rst
        else:
            proj, token = '', rst[0]

        # "vdex#10.17.5.131"
        rst = host.split('#')
        if len(rst) == 2:
            proj, host = rst
        else:
            proj, host = '', rst[0]

        assert proj
        consuls_[proj.upper()] = dict(host=host, port=port, token=token)
    return consuls_


# noinspection PyUnusedLocal
def key_builder_only_kwargs(func, *ignore, **kwargs):
    # python 3.8 support kwargs only by `def func(a, *, kw_only)`
    # but not support `def func(a, *, **kw_only)`
    # why kwargs only?
    # because if func is a class method, like
    #
    # class SomeClass:
    #     def func(self, a): ...,
    #
    # if you call func by args not kwargs, like: `SomeClass().func(a)`
    # *ignore will be [self, a], *self* is different in every call
    # so this key_builder require a kwargs only func
    extra = ""
    if ignore:
        if len(ignore) > 1:
            raise Exception(f"ignore max len 1 got {len(ignore)}, use kwargs only")
        if isinstance(ignore[0], type):
            extra = f"{ignore[0].__name__}"
        elif isinstance(ignore[0], object):
            extra = f"{ignore[0].__class__.__name__}"
        else:
            extra = PROJECT_NAME
    kwargs_s = '__'.join(map(lambda x: f"{x[0]}:{x[1]}", kwargs.items()))
    return f'{extra}:{func.__name__}:kwargs:{kwargs_s}'