import asyncio
from functools import partial
from io import BytesIO
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    overload,
)
from typing_extensions import ParamSpec

import anyio
from imagetext_py import (
    Canvas,
    Color,
    EmojiOptions,
    EmojiSource,
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

from .config import config
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
        FONT = Font(
            str(FONT_PATHS[0]),
            [str(x) for x in FONT_PATHS[1:]],
            emoji_options=EmojiOptions(
                source=getattr(EmojiSource, config.pjsk_emoji_source),
            ),
        )
    return FONT


def hex_to_color(hex_color: str) -> Color:
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]
    return Color.from_hex(hex_color)


async def render_text(
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

    actual_size = await anyio.to_thread.run_sync(
        partial(
            text_size_multiline,
            lines=text_lines,
            size=font_size,
            font=font,
            line_spacing=line_spacing,
            draw_emojis=True,
        ),
    )
    size = (
        actual_size[0] + padding * 2,
        actual_size[1] + padding * 2 + font_size // 2,  # 更多纵向 padding 防止文字被裁
    )

    canvas = Canvas(*size, Color(255, 255, 255, 0))
    await anyio.to_thread.run_sync(
        partial(
            draw_text_multiline,
            canvas=canvas,
            lines=text_lines,
            x=size[0] // 2,
            y=size[1] // 2,
            ax=0.5,
            ay=0.5,
            width=font_weight,
            size=font_size,
            font=font,
            fill=Paint(hex_to_color(color)),
            line_spacing=line_spacing,
            align=TextAlign.Center,
            stroke=stoke_width,  # type: ignore 源码 type 有问题
            stroke_color=Paint(Color(255, 255, 255)),
            draw_emojis=True,
        ),
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
    text_img = await render_text(
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


async def render_summary_from_tasks(
    tasks: Iterable[Awaitable[Image.Image]],
    padding: int = 15,
    line_max: int = 5,
    background: Optional[ColorType] = None,
) -> Image.Image:
    return render_summary_picture(
        await asyncio.gather(*tasks),
        padding,
        line_max,
        background,
    )


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


async def render_all_characters() -> Image.Image:
    characters: Dict[str, StickerInfo] = {}
    for info in LOADED_STICKER_INFO:
        if info.character not in characters:
            characters[info.character] = info
    return await render_summary_from_tasks(
        draw_sticker(info, info.character.capitalize()) for info in characters.values()
    )


async def get_all_characters() -> bytes:
    return await use_image_cache(render_all_characters, "all_characters")()


async def render_character_stickers(character: str) -> Optional[Image.Image]:
    character = character.lower()
    tasks: List[Coroutine[Any, Any, Image.Image]] = [
        draw_sticker(info, info.sticker_id)
        for info in LOADED_STICKER_INFO
        if info.character.lower() == character
    ]
    return (await render_summary_from_tasks(tasks)) if tasks else None


async def get_character_stickers(character: str) -> Optional[bytes]:
    return await use_image_cache(render_character_stickers, character)(character)
