from typing import Any

from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app import models, schemas
from app.api import deps

router = APIRouter()

