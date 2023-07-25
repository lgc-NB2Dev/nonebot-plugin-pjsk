import math
from asyncio import Semaphore
from enum import Enum, auto
from typing import Any, Awaitable, Literal, TypeVar, overload

from httpx import AsyncClient
from typing_extensions import ParamSpec

from .config import config

P = ParamSpec("P")
TAwaitable = TypeVar("TAwaitable", bound=Awaitable)


class ResponseType(Enum):
    JSON = auto()
    TEXT = auto()
    BYTES = auto()


@overload
async def async_request(
    url: str,
    response_type: Literal[ResponseType.JSON],
    prefix: str = config.pjsk_assets_prefix,
) -> Any:
    ...


@overload
async def async_request(
    url: str,
    response_type: Literal[ResponseType.TEXT],
    prefix: str = config.pjsk_assets_prefix,
) -> str:
    ...


@overload
async def async_request(
    url: str,
    response_type: Literal[ResponseType.BYTES] = ResponseType.BYTES,
    prefix: str = config.pjsk_assets_prefix,
) -> bytes:
    ...


async def async_request(
    url: str,
    response_type: ResponseType = ResponseType.BYTES,
    prefix: str = config.pjsk_assets_prefix,
) -> Any:
    if not url.startswith(("http://", "https://")):
        url = f"{prefix}{url}"
    async with AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        if response_type == ResponseType.JSON:
            return response.json()
        if response_type == ResponseType.TEXT:
            return response.text
        return response.content


def with_semaphore(semaphore: Semaphore):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with semaphore:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def rad2deg(rad: float) -> float:
    return rad * 180 / math.pi
