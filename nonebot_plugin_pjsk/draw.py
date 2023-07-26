import asyncio
from io import BytesIO
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional, overload

import anyio
from imagetext_py import (
    Canvas,
    Color,
    Font,
    Paint,
    TextAlign,
    draw_text_multiline,
    text_size_multiline,
)
from numpy import rad2deg
from PIL import Image
from pil_utils import BuildImage
from pil_utils.types import ColorType
from typing_extensions import ParamSpec

from .resource import (
    CACHE_FOLDER,
    FONT_PATHS,
    LOADED_STICKER_INFO,
    RESOURCE_FOLDER,
    StickerInfo,
)
from .utils import split_list

P = ParamSpec("P")


FONT: Optional[Font] = None

DEFAULT_FONT_WEIGHT = 700
DEFAULT_STROKE_WIDTH = 9
DEFAULT_LINE_SPACING = 1.3


def ensure_font() -> Font:
    global FONT
    if not FONT:
        FONT = Font(str(FONT_PATHS[0]), [str(x) for x in FONT_PATHS[1:]])
    return FONT


def hex_to_color(hex_color: str) -> Color:
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]
    return Color.from_hex(hex_color)


def render_text(
    text: str,
    color: str,
    font_size: int,
    font_weight: int,
    stoke_width: int,
    line_spacing: float,
) -> Image.Image:
    font = ensure_font()

    text_lines = text.splitlines()
    padding = stoke_width

    actual_size = text_size_multiline(text_lines, font_size, font, line_spacing)
    size = (
        actual_size[0] + padding * 2,
        actual_size[1] + padding * 2 + font_size // 2,  # 更多纵向 padding 防止文字被裁
    )

    canvas = Canvas(*size, Color(255, 255, 255, 0))
    draw_text_multiline(
        canvas,
        text_lines,  # type: ignore 这里是源代码有问题
        size[0] // 2,
        size[1] // 2,
        0.5,
        0.5,
        font_weight,
        font_size,
        font,
        Paint(hex_to_color(color)),
        line_spacing,
        TextAlign.Center,
        stoke_width,  # type: ignore same
        Paint(Color(255, 255, 255)),
    )

    return canvas.to_image().convert("RGBA")


def paste_text_on_image(
    image: Image.Image,
    text: Image.Image,
    x: int,
    y: int,
    rotate: int,
) -> Image.Image:
    target_size = (296, 256)
    image = BuildImage(image).resize(target_size, keep_ratio=True, inside=True).image

    text_bg = Image.new("RGBA", target_size, (255, 255, 255, 0))
    text = text.rotate(-rad2deg(rotate / 10), resample=Image.BICUBIC, expand=True)
    text_bg.paste(text, (x - text.size[0] // 2, y - text.size[1] // 2), text)

    return Image.alpha_composite(image, text_bg)


def i2b(image: Image.Image, image_format: str = "PNG") -> bytes:
    image_format = image_format.upper()
    if image_format == "JPEG":
        image = image.convert("RGB")
    b = BytesIO()
    image.save(b, image_format)
    return b.getvalue()


async def draw_sticker(
    info: StickerInfo,
    text: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    rotate: Optional[int] = None,
    font_size: Optional[int] = None,
    stroke_width: Optional[int] = None,
    line_spacing: Optional[float] = None,
    font_weight: Optional[int] = None,
) -> Image.Image:
    sticker_img = await anyio.Path(RESOURCE_FOLDER / info.img).read_bytes()
    text_img = render_text(
        text or info.default_text.text,
        info.color,
        font_size or info.default_text.s,
        font_weight or DEFAULT_FONT_WEIGHT,
        stroke_width or DEFAULT_STROKE_WIDTH,
        line_spacing or DEFAULT_LINE_SPACING,
    )
    return paste_text_on_image(
        Image.open(BytesIO(sticker_img)).convert("RGBA"),
        text_img,
        x or info.default_text.x,
        y or info.default_text.y,
        rotate or info.default_text.r,
    )


def render_summary_picture(
    image_list: List[Image.Image],
    padding: int = 15,
    line_max: int = 5,
    background: Optional[ColorType] = None,
) -> Image.Image:
    lines = split_list(image_list, line_max)
    width = max(
        [sum([x.size[0] for x in line]) + padding * (len(line) + 1) for line in lines],
    )
    height = sum([max([x.size[1] for x in line]) for line in lines]) + (
        padding * (len(lines) + 1)
    )
    bg = Image.new("RGBA", (width, height), background or (0, 0, 0))

    y_offset = padding
    for line in lines:
        x_offset = padding
        for item in line:
            bg.paste(item, (x_offset, y_offset), item)
            x_offset += item.size[0] + padding
        y_offset += max([x.size[1] for x in line]) + padding

    return bg


async def render_all_characters() -> Image.Image:
    characters: Dict[str, StickerInfo] = {}
    for info in LOADED_STICKER_INFO:
        if info.character not in characters:
            characters[info.character] = info

    tasks: List[Coroutine[Any, Any, Image.Image]] = [
        draw_sticker(info, info.character.capitalize()) for info in characters.values()
    ]
    images: List[Image.Image] = await asyncio.gather(*tasks)
    return render_summary_picture(images)


async def render_character_stickers(character: str) -> Optional[Image.Image]:
    character = character.lower()

    tasks: List[Coroutine[Any, Any, Image.Image]] = [
        draw_sticker(info, info.sticker_id)
        for info in LOADED_STICKER_INFO
        if info.character.lower() == character
    ]
    if not tasks:
        return None

    images: List[Image.Image] = await asyncio.gather(*tasks)
    return render_summary_picture(images)


@overload
def use_image_cache(
    func: Callable[P, Awaitable[Image.Image]],
    filename: str,
    image_format: str = "JPEG",
) -> Callable[P, Awaitable[bytes]]:
    ...


@overload
def use_image_cache(
    func: Callable[P, Awaitable[Optional[Image.Image]]],
    filename: str,
    image_format: str = "JPEG",
) -> Callable[P, Awaitable[Optional[bytes]]]:
    ...


def use_image_cache(
    func: Callable[P, Awaitable[Optional[Image.Image]]],
    filename: str,
    image_format: str = "JPEG",
) -> Callable[P, Awaitable[Optional[bytes]]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[bytes]:
        path = anyio.Path(CACHE_FOLDER) / f"{filename}.{image_format.lower()}"
        if await path.exists():
            return await path.read_bytes()

        raw_image = await func(*args, **kwargs)
        if not raw_image:
            return None

        image = i2b(raw_image, image_format)
        await path.write_bytes(image)
        return image

    return wrapper
