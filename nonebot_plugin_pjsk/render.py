import asyncio
import math
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Literal, Optional, TypedDict, Union
from typing_extensions import Concatenate, ParamSpec, Unpack

import anyio
from nonebot import logger
from nonebot_plugin_htmlrender import get_new_page
from playwright.async_api import Page, Request, Route
from yarl import URL

from nonebot_plugin_pjsk.utils import is_full_width, qor

from .config import config
from .resource import (
    DATA_FOLDER,
    FONT_PATH,
    JINJA_ENV,
    LOADED_STICKER_INFO,
    RESOURCE_FOLDER,
    StickerInfo,
    get_cache,
    make_cache_key,
    write_cache,
)

P = ParamSpec("P")

DEFAULT_WIDTH = 296
DEFAULT_HEIGHT = 256
DEFAULT_STROKE_WIDTH = 9
DEFAULT_LINE_SPACING = 1.3
DEFAULT_STROKE_COLOR = "#ffffff"

ROUTER_BASE_URL = "https://pjsk.nonebot/"


def calc_approximate_text_width(text: str, size: int, rotate_deg: float) -> float:
    rotate_rad = math.radians(rotate_deg)
    width = sum((size if is_full_width(x) else size / 2) for x in text)
    return abs(width * math.cos(rotate_rad)) + abs(size * math.sin(rotate_rad))


def auto_adjust_font_size(
    text: str,
    size: int,
    rotate_deg: float,
    width: int = DEFAULT_WIDTH,
    min_size: int = 8,
    multiplier: float = 1.2,
) -> int:
    while size > min_size:
        if (calc_approximate_text_width(text, size, rotate_deg) * multiplier) <= width:
            break
        size -= 1
    return size


async def root_router(route: Route):
    return await route.fulfill(body="<html></html>")


async def file_router(route: Route, request: Request):
    url = URL(request.url)
    path = anyio.Path(DATA_FOLDER / url.path[1:])
    logger.debug(f"Requested `{url}`, resolved to `{path}`")
    try:
        data = await path.read_bytes()
    except Exception:
        logger.exception("Error while reading file")
        return await route.abort()
    return await route.fulfill(body=data)


def to_router_url(path: Union[str, Path]) -> str:
    if not isinstance(path, Path):
        path = Path(path)
    url = f"{ROUTER_BASE_URL}{path.relative_to(DATA_FOLDER)}".replace("\\", "/")
    logger.debug(f"to_router_url: {path} -> {url}")
    return url


@asynccontextmanager
async def get_routed_page(initial_html: Optional[str] = None):
    async with get_new_page(device_scale_factor=1) as page:
        await page.route(f"{ROUTER_BASE_URL}", root_router)
        await page.route(f"{ROUTER_BASE_URL}**/*", file_router)
        await page.goto(ROUTER_BASE_URL)
        if initial_html:
            await page.set_content(initial_html)
        yield page


async def capture_element(
    page: Page,
    selector: str,
    image_type: Literal["png", "jpeg"] = "jpeg",
    omit_background: bool = False,
    cache_key: Optional[str] = None,
) -> bytes:
    element = await page.wait_for_selector(selector)
    assert element
    img = await element.screenshot(type=image_type, omit_background=omit_background)
    if config.pjsk_use_cache and cache_key:
        await write_cache(f"{cache_key}.{image_type}", img)
    return img


async def capture_sticker(html: str, cache_key: Optional[str] = None) -> bytes:
    async with get_routed_page(html) as page:
        return await capture_element(
            page,
            "svg",
            image_type="png",
            omit_background=True,
            cache_key=cache_key,
        )


async def capture_template(html: str, cache_key: Optional[str] = None) -> bytes:
    async with get_routed_page(html) as page:
        return await capture_element(page, ".main-wrapper", cache_key=cache_key)


class StickerRenderKwargs(TypedDict):
    image: str
    x: int
    y: int
    text: str
    font_color: str
    font_size: int
    rotate: float
    stroke_color: str
    stroke_width: int
    line_spacing: float
    font: str
    width: int
    height: int


def make_sticker_render_kwargs(
    info: StickerInfo,
    text: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    rotate: Optional[float] = None,
    font_size: Optional[int] = None,
    font_color: Optional[str] = None,
    stroke_width: Optional[int] = None,
    stroke_color: Optional[str] = None,
    line_spacing: Optional[float] = None,
    auto_adjust: bool = False,
) -> StickerRenderKwargs:
    default_text = info.default_text
    text = qor(text, default_text.text)
    rotate = qor(rotate, lambda: math.degrees(default_text.r / 10))
    font_size = (
        auto_adjust_font_size(text, default_text.s, rotate)
        if auto_adjust
        else qor(font_size, default_text.s)
    )
    params: StickerRenderKwargs = {
        "image": to_router_url(RESOURCE_FOLDER / info.img),
        "x": qor(x, default_text.x),
        "y": qor(y, default_text.y),
        "text": text,
        "font_color": qor(font_color, info.color),
        "font_size": font_size,
        "rotate": rotate,
        "stroke_color": qor(stroke_color, DEFAULT_STROKE_COLOR),
        "stroke_width": qor(stroke_width, DEFAULT_STROKE_WIDTH),
        "line_spacing": qor(line_spacing, DEFAULT_LINE_SPACING),
        "font": to_router_url(FONT_PATH),
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
    }
    return params


async def render_sticker_html(**kwargs: Unpack[StickerRenderKwargs]) -> str:
    template = JINJA_ENV.get_template("sticker.svg.jinja")
    return await template.render_async(id=hash(kwargs["image"]), **kwargs)


async def render_sticker_grid_html(items: List[str]) -> str:
    template = JINJA_ENV.get_template("sticker_grid.html.jinja")
    return await template.render_async(items=items)


async def render_help_html(text: str) -> str:
    template = JINJA_ENV.get_template("help.html.jinja")
    return await template.render_async(text=text)


def use_cache(cache_key: Union[str, Callable[P, str]], ext: Literal["png", "jpeg"]):
    def decorator(func: Callable[Concatenate[str, P], Awaitable[bytes]]):
        async def wrapper(*args: P.args, **kwargs: P.kwargs):
            key = cache_key(*args, **kwargs) if callable(cache_key) else cache_key
            if (config.pjsk_use_cache) and (c := await get_cache(f"{key}.{ext}")):
                logger.debug(f"Cache hit for `{key}.{ext}`")
                return c
            return await func(key, *args, **kwargs)

        return wrapper

    return decorator


def get_sticker_cache_key_maker(**params: Unpack[StickerRenderKwargs]) -> str:
    return make_cache_key(params)


@use_cache(get_sticker_cache_key_maker, "png")
async def get_sticker(key: str, **params: Unpack[StickerRenderKwargs]) -> bytes:
    return await capture_sticker(await render_sticker_html(**params), cache_key=key)


@use_cache("help", "jpeg")
async def get_help(key: str, text: str) -> bytes:
    return await capture_template(await render_help_html(text), cache_key=key)


@use_cache("all_characters", "jpeg")
async def get_all_characters_grid(key: str) -> bytes:
    character_dict: Dict[str, StickerInfo] = {}
    for info in LOADED_STICKER_INFO:
        character = info.character
        if character not in character_dict:
            character = (
                character
                if character[0].isupper()
                else character[0].upper() + character[1:]
            )
            character_dict[character] = info

    sticker_templates = await asyncio.gather(
        *(
            render_sticker_html(**make_sticker_render_kwargs(info, char))
            for char, info in character_dict.items()
        ),
    )
    return await capture_template(
        await render_sticker_grid_html(sticker_templates),
        cache_key=key,
    )


def get_character_stickers_grid_cache_key_maker(character: str) -> str:
    return character


@use_cache(get_character_stickers_grid_cache_key_maker, "jpeg")
async def get_character_stickers_grid(key: str, character: str) -> bytes:
    character = character.lower()
    sticker_templates = await asyncio.gather(
        *(
            render_sticker_html(**make_sticker_render_kwargs(info, info.sticker_id))
            for info in LOADED_STICKER_INFO
            if info.character.lower() == character
        ),
    )
    return await capture_template(
        await render_sticker_grid_html(sticker_templates),
        cache_key=key,
    )
