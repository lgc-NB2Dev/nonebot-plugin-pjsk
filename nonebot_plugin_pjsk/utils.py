import unicodedata
from asyncio import Semaphore
from enum import Enum, auto
from functools import lru_cache
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)
from typing_extensions import ParamSpec

from httpx import AsyncClient
from nonebot import logger

from .config import config

T = TypeVar("T")
TN = TypeVar("TN", int, float)
TA = TypeVar("TA")
TB = TypeVar("TB")
R = TypeVar("R")
P = ParamSpec("P")


class ResponseType(Enum):
    JSON = auto()
    TEXT = auto()
    BYTES = auto()


@overload
async def async_request(
    *urls: str,
    response_type: Literal[ResponseType.JSON],
    retries: int = config.pjsk_req_retry,
) -> Any:
    ...


@overload
async def async_request(
    *urls: str,
    response_type: Literal[ResponseType.TEXT],
    retries: int = config.pjsk_req_retry,
) -> str:
    ...


@overload
async def async_request(
    *urls: str,
    response_type: ResponseType = ResponseType.BYTES,
    retries: int = config.pjsk_req_retry,
) -> bytes:
    ...


async def async_request(
    *urls: str,
    response_type: ResponseType = ResponseType.BYTES,
    retries: int = config.pjsk_req_retry,
) -> Any:
    if not urls:
        raise ValueError("No URL specified")

    url, rest = urls[0], urls[1:]
    try:
        async with AsyncClient(
            proxy=config.pjsk_req_proxy,
            timeout=config.pjsk_req_timeout,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            if response_type == ResponseType.JSON:
                return await response.json()
            if response_type == ResponseType.TEXT:
                return response.text
            return response.read()

    except Exception as e:
        err_suffix = f"because error occurred while requesting {url}: {e.__class__.__name__}: {e}"
        if retries <= 0:
            if not rest:
                raise
            logger.error(f"Requesting next url {err_suffix}")
            logger.debug(repr(e))
            return await async_request(*rest, response_type=response_type)

        retries -= 1
        logger.error(f"Retrying ({retries} left) {err_suffix}")
        logger.debug(repr(e))
        return await async_request(*urls, response_type=response_type, retries=retries)


def append_prefix(suffix: str, prefixes: Sequence[str]) -> List[str]:
    return [prefix + suffix for prefix in prefixes]


def with_semaphore(semaphore: Semaphore):
    def decorator(func: Callable[P, Awaitable[R]]):
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            async with semaphore:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def chunks(iterable: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


class ResolveValueError(ValueError):
    pass


def resolve_value(
    value: Optional[str],
    default: Union[TN, Callable[[], TN]],
    expected_type: Type[TN] = int,
) -> TN:
    def get_default() -> TN:
        return default() if isinstance(default, Callable) else default

    if not value:
        return get_default()
    try:
        if value.startswith("^"):
            return get_default() + expected_type(value[1:])
        return expected_type(value)  # type: ignore pylance 抽风
    except Exception as e:
        raise ResolveValueError(value) from e


def qor(a: Optional[TA], b: Union[TB, Callable[[], TB]]) -> Union[TA, TB]:
    return a if (a is not None) else (b() if isinstance(b, Callable) else b)


@lru_cache()
def is_full_width(char: str) -> bool:
    return unicodedata.east_asian_width(char) in ("A", "F", "W")
