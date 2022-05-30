# @Time : 2021-11-27 18:05:50
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : health.py
from fastapi import APIRouter


router = APIRouter()


@router.get("/health/", tags=['health'], description='Health check')
async def health():
    return "ok"
