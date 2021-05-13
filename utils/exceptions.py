# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/13/21 10:56 PM
from typing import Any

from utils.error_code import ERR_NOT_FOUND, ERR_ARG
from utils.http_code import HTTP_400_BAD_REQUEST


class RCSException(Exception):
    def __init__(self, error_code: int = 0, message: str = "", content: Any = None):
        self.status_code = HTTP_400_BAD_REQUEST
        self.error_code = error_code
        self.message = message
        self.content = content


class RCSExcNotFound(RCSException):
    def __init__(self, entity_id: str):
        super(RCSExcNotFound, self).__init__(
            error_code=ERR_NOT_FOUND, message="EntityNotFound", content=dict(entity_id=entity_id))


class RCSExcErrArg(RCSException):
    def __init__(self, content: Any = None):
        super(RCSExcErrArg, self).__init__(
            error_code=ERR_ARG, message="ArgsParseFailed", content=content)


class APIError(Exception):
    pass
