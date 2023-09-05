from asyncio import Semaphore
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from aiohttp import ClientSession
from nonebot import logger

from .config import config

T = TypeVar("T")
TN = TypeVar("TN", int, float)
TA = TypeVar("TA")
TB = TypeVar("TB")


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
        async with ClientSession(raise_for_status=True) as session:
            async with session.get(url, proxy=config.pjsk_req_proxy) as response:
                if response_type == ResponseType.JSON:
                    return await response.json()
                if response_type == ResponseType.TEXT:
                    return await response.text()
                return await response.read()

    except Exception as e:
        if retries <= 0:
            if not rest:
                raise

            logger.error(
                f"Requesting next url because error occurred while requesting {url}",
            )
            logger.debug(repr(e))
            return await async_request(*rest, response_type=response_type)

        retries -= 1
        logger.error(
            f"Retrying ({retries} left) because error occurred while requesting {url}",
        )
        logger.debug(repr(e))
        return await async_request(url, response_type=response_type, retries=retries)


def append_prefix(suffix: str, prefixes: List[str]) -> List[str]:
    return [prefix + suffix for prefix in prefixes]


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
