from asyncio import Semaphore
from enum import Enum, auto
from typing import Any, Iterable, List, Literal, Optional, Type, TypeVar, overload

from httpx import AsyncClient

from .config import config

T = TypeVar("T")
TN = TypeVar("TN", int, float)


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


def split_list(li: Iterable[T], length: int) -> List[List[T]]:
    latest = []
    tmp = []
    for n, i in enumerate(li):
        tmp.append(i)
        if (n + 1) % length == 0:
            latest.append(tmp)
            tmp = []
    if tmp:
        latest.append(tmp)
    return latest


class ResolveValueError(ValueError):
    pass


def resolve_value(
    value: Optional[str],
    default: TN,
    expected_type: Type[TN] = int,
) -> TN:
    if not value:
        return default
    try:
        if value.startswith("^"):
            return default + expected_type(value[1:])
        return expected_type(value)  # type: ignore pylance 抽风
    except Exception as e:
        raise ResolveValueError(value) from e
