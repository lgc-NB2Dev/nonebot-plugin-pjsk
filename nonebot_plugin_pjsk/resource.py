import asyncio
import random
import shutil
from pathlib import Path
from typing import Coroutine, List, Optional, overload

import anyio
from nonebot import get_driver, logger
from pydantic import BaseModel, Field, parse_raw_as

from .config import config
from .utils import ResponseType, append_prefix, async_request, with_semaphore

DATA_FOLDER = Path.cwd() / "data" / "pjsk"
FONT_FOLDER = DATA_FOLDER / "fonts"
RESOURCE_FOLDER = DATA_FOLDER / "resource"
STICKER_INFO_CACHE = DATA_FOLDER / "characters.json"

CACHE_FOLDER = DATA_FOLDER / "cache"
if CACHE_FOLDER.exists():
    shutil.rmtree(CACHE_FOLDER)
CACHE_FOLDER.mkdir(parents=True)

FONT_PATH = FONT_FOLDER / "YurukaFangTang.ttf"

for _folder in (DATA_FOLDER, FONT_FOLDER, RESOURCE_FOLDER):
    if not _folder.exists():
        _folder.mkdir(parents=True)


class StickerText(BaseModel):
    text: str
    x: int
    y: int
    r: int  # rotate
    s: int  # font size


class StickerInfo(BaseModel):
    sticker_id: str = Field(..., alias="id")
    name: str
    character: str
    img: str
    color: str
    default_text: StickerText = Field(..., alias="defaultText")


LOADED_STICKER_INFO: List[StickerInfo] = []


def sort_stickers():
    LOADED_STICKER_INFO.sort(key=lambda x: x.character.lower())
    for i, x in enumerate(LOADED_STICKER_INFO, 1):
        x.sticker_id = str(i)


@overload
def select_or_get_random(sticker_id: None = None) -> StickerInfo:
    ...


@overload
def select_or_get_random(sticker_id: str) -> Optional[StickerInfo]:
    ...


def select_or_get_random(sticker_id: Optional[str] = None) -> Optional[StickerInfo]:
    return (
        next((x for x in LOADED_STICKER_INFO if sticker_id == x.sticker_id), None)
        if sticker_id
        else random.choice(LOADED_STICKER_INFO)
    )


async def check_and_download_font():
    async def download(font_name: str):
        logger.opt(colors=True).info(f"Downloading font <y>{font_name}</y>")

        path = anyio.Path(FONT_FOLDER) / font_name
        urls = append_prefix(f"fonts/{font_name}", config.pjsk_repo_prefix)
        await path.write_bytes(await async_request(*urls))

        logger.opt(colors=True).info(f"Successfully downloaded font <y>{font_name}</y>")

    # tasks: List[Coroutine] = [
    #     download(path.name) for path in FONT_PATHS if not path.exists()
    # ]
    # await asyncio.gather(*tasks)
    if not FONT_PATH.exists():
        await download(FONT_PATH.name)


async def load_sticker_info():
    logger.debug("Updating sticker information")

    path = anyio.Path(STICKER_INFO_CACHE)
    urls = append_prefix("src/characters.json", config.pjsk_assets_prefix)
    try:
        loaded_text = await async_request(*urls, response_type=ResponseType.TEXT)
        await path.write_text(loaded_text, encoding="u8")
    except Exception as e:
        if not (await path.exists()):
            raise
        logger.warning(
            f"Failed to download sticker information, using cached data: {e!r}",
        )
        loaded_text = await path.read_text(encoding="u8")

    LOADED_STICKER_INFO.clear()
    LOADED_STICKER_INFO.extend(parse_raw_as(List[StickerInfo], loaded_text))
    sort_stickers()


async def check_and_download_stickers():
    semaphore = asyncio.Semaphore(10)

    @with_semaphore(semaphore)
    async def download(path_str: str):
        path = anyio.Path(RESOURCE_FOLDER) / path_str
        if not (await (dir_name := path.parent).exists()):
            await dir_name.mkdir(parents=True, exist_ok=True)

        logger.opt(colors=True).info(f"Downloading sticker <y>{path.name}</y>")
        urls = append_prefix(f"public/img/{path_str}", config.pjsk_assets_prefix)
        await path.write_bytes(await async_request(*urls))

    logger.debug("Checking and downloading sticker assets")
    tasks: List[Coroutine] = [
        download(sticker_info.img)
        for sticker_info in LOADED_STICKER_INFO
        if not (RESOURCE_FOLDER / sticker_info.img).exists()
    ]
    await asyncio.gather(*tasks)


async def check_and_download_resource():
    await load_sticker_info()
    await check_and_download_stickers()


async def prepare_resource():
    logger.debug("Checking and downloading resources")
    await asyncio.gather(
        check_and_download_resource(),
        check_and_download_font(),
    )
    logger.success("Successfully checked resources")


driver = get_driver()
driver.on_startup(prepare_resource)
