from __future__ import absolute_import
import asyncio
import logging
from random import choice
from typing import Optional

from consul import base

__all__ = ['Consul']

from httpx import AsyncClient


class HTTPClient(base.HTTPClient):
    """Asyncio adapter for python consul using aiohttp library"""

    def __init__(self, *args, loop=None, client: AsyncClient = None, **kwargs):
        super(HTTPClient, self).__init__(*args, **kwargs)
        self._loop = loop
        self._client = client

    async def _request(self, callback, method, uri, data=None, headers=None):
        resp = await self._client.request(
            method=method, url=uri, data=data, headers=headers)
        body = resp.text
        content = resp.read()
        if resp.status_code == 599:
            raise base.Timeout
        r = base.Response(resp.status_code, resp.headers, body, content)
        return callback(r)

    async def get(self, callback, path, params=None, headers=None):
        uri = self.uri(path, params)
        return await self._request(callback, 'GET', uri, headers=headers)

    async def put(self, callback, path, params=None, data='', headers=None):
        uri = self.uri(path, params)
        return await self._request(callback,
                                   'PUT',
                                   uri,
                                   data=data,
                                   headers=headers)

    async def delete(self, callback, path, params=None, data='', headers=None):
        uri = self.uri(path, params)
        return await self._request(callback,
                                   'DELETE',
                                   uri,
                                   data=data,
                                   headers=headers)

    async def post(self, callback, path, params=None, data='', headers=None):
        uri = self.uri(path, params)
        return await self._request(callback,
                                   'POST',
                                   uri,
                                   data=data,
                                   headers=headers)

    async def aclose(self):
        await self._client.aclose()


class Consul(base.Consul):

    def __init__(self, *args, loop=None, client=None, **kwargs):
        self._loop = loop or asyncio.get_event_loop()
        self._client = client
        super().__init__(*args, **kwargs)

    def http_connect(self, host, port, scheme, verify=False, cert=None):
        return HTTPClient(host, port, scheme, loop=self._loop,
                          verify=verify, cert=cert, client=self._client)

    async def register(self, name, service_id, address, port, interval_seconds=10, token=''):
        check = {
            # "id": service_id,
            # "name": name,
            "http": f"{address}:{port}",
            # "grpc_use_tls": False,
            "interval": f"{interval_seconds}s"
        }
        tags = ['rcs', 'http']
        await self.agent.service.register(name, service_id, address, port, tags=tags, check=check, token=token)

    async def get_value(self, key: str, default=True) -> Optional[str]:
        key = f"RCS_{key}" if default else key
        ret = await self.kv.get(key)
        try:
            v = ret[1]['Value']
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            return v
        except Exception as e:
            logging.error(f"Wrong consul kv key:{key} or wrong token")
            logging.error(e)
        return None

    async def get_service_one(self, key: str) -> Optional[str]:
        ret = await self.catalog.service(key)
        if ret and ret[1]:
            # (index, [
            #     {
            #         "Node": "foobar",
            #         "Address": "10.1.10.12",
            #         "ServiceID": "redis",
            #         "ServiceName": "redis",
            #         "ServiceTags": null,
            #         "ServicePort": 8000
            #     }
            # ])
            v = choice(ret[1])
            return f"{v['Address']}:{v['ServicePort']}"
        else:
            return None
