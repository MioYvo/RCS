import json
from typing import Union

import ujson
from tornado.escape import native_str
from tornado.web import RequestHandler, Finish

from utils.encoder import MyEncoder
from utils.http_code import (HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_422_UNPROCESSABLE_ENTITY,
                             HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN,
                             HTTP_500_INTERNAL_SERVER_ERROR, HTTP_401_UNAUTHORIZED)
from utils.error_code import ERR_UNKNOWN, ERR_NO_CONTENT, ERR_ARG, ERR_MULTIPLE_OBJ_RETURNED


# noinspection PyAbstractClass
class BaseRequestHandler(RequestHandler):
    def finish(self, chunk: Union[str, bytes, dict] = None, status=None):
        if status:
            self.set_status(status)

        super(BaseRequestHandler, self).finish(chunk)

    def options(self):
        # self.set_header("Access-Control-Allow-Origin", "*")
        # self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE")
        # self.set_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        pass

    def write_response(self, content=None, error_code=0, message="", status_code=HTTP_200_OK, reason=None, meta=None):
        if meta is None:
            meta = {}
        self.set_status(status_code, reason=reason)
        if status_code != HTTP_204_NO_CONTENT:
            # 如果是204的返回, http的标准是不能有body, 所以tornado的httpclient接收的时候会
            # 报错变成599错误
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.write(json.dumps(dict(error_code=error_code, message=message, meta=meta, content=content),
                                  cls=MyEncoder))

    def write_error_response(self, content=None, error_code=ERR_UNKNOWN, message="UnknownError",
                             status_code=HTTP_400_BAD_REQUEST, reason=None):
        """
        错误响应
        :param error_code:
        :param message:
        :param status_code:
        :param content:
        :param reason:
        :return:
        """
        self.clear()
        if status_code == HTTP_422_UNPROCESSABLE_ENTITY and not reason:
            reason = message
        self.write_response(content=content, error_code=error_code, message=message,
                            status_code=status_code, reason=reason)
        raise Finish()

    def write_no_content_response(self):
        self.set_status(HTTP_204_NO_CONTENT)

    def write_not_found_entity_response(self, content=None, message="没有找到对应实体"):
        """
        查询id没有结果
        :param message:
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=ERR_NO_CONTENT, message=message,
                                  status_code=HTTP_400_BAD_REQUEST)

    def write_multiple_results_found_response(self, content=None):
        """
        查询获取单个数据时，找到不止一个
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=ERR_MULTIPLE_OBJ_RETURNED,
                                  message="MultipleObjectsReturned",
                                  status_code=HTTP_400_BAD_REQUEST)

    def write_unknown_error_response(self, content=None):
        """
        创建中的错误
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=ERR_UNKNOWN, message="UnknownError",
                                  status_code=HTTP_422_UNPROCESSABLE_ENTITY, reason="UNPROCESSABLE_ENTITY")

    def write_parse_args_failed_response(self, message="args parse failed", content=None):
        """
        参数解析错误
        :param message:
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=ERR_ARG, message=message,
                                  status_code=HTTP_400_BAD_REQUEST)

    def write_duplicate_entry(self, content=None):
        """
        插入操作，重复键值
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=1062, message="Duplicate entry",
                                  status_code=HTTP_500_INTERNAL_SERVER_ERROR, reason="Duplicate entry")

    def write_logic_error_response(self, content=None):
        """
        逻辑层返回错误
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=106, message="LogicResponseFailed",
                                  status_code=HTTP_422_UNPROCESSABLE_ENTITY, reason="logic response failed")

    def write_forbidden_response(self, content=None, message="Forbidden"):
        """
        被禁止
        :param message:
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=107, message=message,
                                  status_code=HTTP_403_FORBIDDEN)


    def write_refund_money_error(self, content=None):
        """
        退款失败
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=108, message="RefundMoneyFailed",
                                  status_code=HTTP_422_UNPROCESSABLE_ENTITY, reason="RefundMoneyFailed")

    def write_cost_money_error(self, content=None):
        """
        扣款失败
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=109, message="CostMoneyFailed",
                                  status_code=HTTP_422_UNPROCESSABLE_ENTITY, reason="RefundMoneyFailed")

    def write_unauthorized(self, content=None, message="Unauthorized"):
        """
        身份验证失败
        :param content:
        :param message:
        :return:
        """
        self.write_error_response(content=content, error_code=110, message=message, status_code=HTTP_401_UNAUTHORIZED)

    def write_rate_limit_response(self, content=None, message="Rate limit"):
        """
        速率限制
        :param message:
        :param content:
        :return:
        """
        self.write_error_response(content=content, error_code=111, message=message,
                                  status_code=HTTP_403_FORBIDDEN)

    def set_headers(self, headers):
        if headers:
            for header in headers:
                self.set_header(header, headers[header])

    def get_token(self):
        try:
            token = self.request.headers.get("Authorization").split(' ')[1]
            return token
        except Exception as e:
            self.write_forbidden_response("Can't get token {}".format(e))
            return False

    def get_query_args(self):
        """
        获取query_arguments，只取值列表最后一个
        :return:
        """
        rst = {}
        for key, value in self.request.query_arguments.items():
            if isinstance(value[-1], str):
                value = value[-1]
            else:
                value = value[-1].decode()
            if value:
                rst[key] = value
            else:
                continue
        return rst

    def get_body_args(self):
        """
        获取body_arguments, 只取列表最后一个
        :return:
        """
        if self.request.body_arguments:
            return {key: native_str(value[-1])
                    for key, value in self.request.body_arguments.items()}
        if self.request.body:
            return ujson.loads(self.request.body)
        return {}
