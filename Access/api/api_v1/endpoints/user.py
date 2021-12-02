# @Time : 2021-11-26 10:19:22
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : user.py
from enum import Enum
from typing import Optional
from urllib.parse import urljoin

from fastapi import APIRouter
from pydantic import BaseModel, Field as PDField

from utils.exceptions import RCSExcErrArg, RCSExcNotFound
from utils.logger import Logger
from config.clients import consuls, httpx_client
from utils.u_consul import Consul

router = APIRouter()
logger = Logger(__file__)


class ProjectType(str, Enum):
    vdex = 'VDEX'
    vtoken = "VTOKEN"
    paydex = "PAYDEX"


class UserInfo(BaseModel):
    idCardFrontMsg: str = PDField(title='证件照正面照片地址')
    idCardReverseMsg: str = PDField(title='证件照背面照片地址')
    tel: str = PDField(title='手机号')
    user_id: int = PDField(title='用户ID')
    nickName: str = PDField(title='昵称')
    addTime: int = PDField(title='注册时间')
    email: Optional[str]
    truename: str = PDField(title='真实姓名')
    idCard: str = PDField(title='证件号码')
    userType: str = PDField(title='会员等级', description='00使用，10普通，20VIP')
    googleSecret: str = PDField(title='是否绑定谷歌验证码', description='10是，20否')
    emailProvider: str = PDField(title='邮箱服务商')


php_service_consul_name = {
    "VDEX": "vdex_dapp_phpservice",
    "PAYDEX": "paydex_dapp_phpservice"
}


@router.get("/userinfo/{project_name}/{user_id}", response_model=UserInfo, description="")
async def user_info(project_name: str, user_id: str):
    php_consul_name = php_service_consul_name.get(project_name.upper())
    if not php_consul_name:
        raise RCSExcErrArg(content=f"{project_name=:} not found")

    consul_client: Consul = consuls.get(project_name.upper())
    if not consul_client:
        raise RCSExcErrArg(content=f"{project_name=:} client not registered")

    php_address = await consul_client.get_service_one(php_consul_name)
    if not php_address:
        raise RCSExcErrArg(content=f"{project_name=:} php service not found")

    url = urljoin(f"http://{php_address}", "/vdexapi/user_mg")
    ret = await httpx_client.get(url, params=dict(account=user_id))
    try:
        return UserInfo(**ret.json()['data'])
    except Exception as e:
        logger.error(e, ret=ret.content)
        raise RCSExcNotFound(entity_id=user_id)
