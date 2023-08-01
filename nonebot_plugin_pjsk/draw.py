import asyncio
import itertools
from functools import partial
from io import BytesIO
from math import cos, sin
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
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
    text_wrap,
)
from numpy import deg2rad, rad2deg
from PIL import Image

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
ColorType = Union[str, Tuple[int, int, int], Tuple[int, int, int, int]]


FONT: Optional[Font] = None
SYSTEM_FONT: Optional[Font] = None

DEFAULT_FONT_WEIGHT = 700
DEFAULT_STROKE_WIDTH = 9
DEFAULT_LINE_SPACING = 1.3

CANVAS_SIZE = (296, 256)
MAX_TEXT_IMAGE_SIZE = 2048

ONE_DARK_BLACK = "282c34"
ONE_DARK_WHITE = "abb2bf"


class TextTooLargeError(ValueError):
    pass


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


def calc_rotated_size(width: int, height: int, rotate_deg: float) -> Tuple[int, int]:
    rotate_rad = deg2rad(rotate_deg)
    return (
        int(abs(width * cos(rotate_rad)) + abs(height * sin(rotate_rad))),
        int(abs(width * sin(rotate_rad)) + abs(height * cos(rotate_rad))),
    )


def resize_sticker(image: Image.Image, size: Tuple[int, int], **kwargs) -> Image.Image:
    width, height = size
    ratio = min(width / image.width, height / image.height)
    width = int(image.width * ratio)
    height = int(image.height * ratio)

    image = image.resize((width, height), resample=Image.BICUBIC, **kwargs)
    new_image = Image.new("RGBA", size, (255, 255, 255, 0))
    new_image.paste(image, ((size[0] - width) // 2, (size[1] - height) // 2))
    return new_image


def get_ax_by_align(align: TextAlign) -> float:
    if align is TextAlign.Left:
        return 0
    if align is TextAlign.Right:
        return 1
    return 0.5  # center


async def render_text(
    text: str,
    color: str,
    font_size: int,
    font_weight: int = DEFAULT_FONT_WEIGHT,
    stoke_width: int = DEFAULT_STROKE_WIDTH,
    line_spacing: float = DEFAULT_LINE_SPACING,
    align: TextAlign = TextAlign.Center,
    max_width: Optional[int] = None,
    will_rotate: Optional[float] = None,
    min_size: int = 8,
    error_when_too_large: bool = True,  # noqa: FBT001
) -> Image.Image:
    font = ensure_font()

    text_lines = text.splitlines()
    padding = stoke_width

    while True:
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

        if (not max_width) or font_size <= min_size:
            break

        rotated_width = (
            size[0]
            if (will_rotate is None)
            else calc_rotated_size(*size, will_rotate)[0]
        )
        if rotated_width <= max_width:
            break
        font_size -= 1

    if error_when_too_large and (
        size[0] > MAX_TEXT_IMAGE_SIZE or size[1] > MAX_TEXT_IMAGE_SIZE
    ):
        raise TextTooLargeError

    canvas = Canvas(*size, Color(255, 255, 255, 0))
    await anyio.to_thread.run_sync(
        partial(
            draw_text_multiline,
            canvas=canvas,
            lines=text_lines,
            x=size[0] // 2,
            y=size[1] // 2,
            ax=get_ax_by_align(align),
            ay=0.5,
            width=font_weight,
            size=font_size,
            font=font,
            fill=Paint(hex_to_color(color)),
            line_spacing=line_spacing,
            align=align,
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
    image = resize_sticker(image, CANVAS_SIZE)

    text_bg = Image.new("RGBA", CANVAS_SIZE, (255, 255, 255, 0))
    text = text.rotate(-rotate, resample=Image.BICUBIC, expand=True)
    text_bg.paste(text, (x - text.size[0] // 2, y - text.size[1] // 2), text)

    return Image.alpha_composite(image, text_bg)


def i2b(
    image: Image.Image,
    image_format: str = "PNG",
    background: Optional[ColorType] = None,
) -> bytes:
    image_format = image_format.upper()

    if image_format == "JPEG":
        if background:
            new_image = Image.new("RGBA", image.size, background)
            new_image.paste(image, mask=image)
            image = new_image.convert("RGB")
        else:
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
    auto_adjust: bool = False,  # noqa: FBT001
) -> Image.Image:
    sticker_img = await anyio.Path(RESOURCE_FOLDER / info.img).read_bytes()
    text_img = await render_text(
        text or info.default_text.text,
        info.color,
        font_size or info.default_text.s,
        font_weight or DEFAULT_FONT_WEIGHT,
        stroke_width or DEFAULT_STROKE_WIDTH,
        line_spacing or DEFAULT_LINE_SPACING,
        max_width=CANVAS_SIZE[0] if auto_adjust else None,
        will_rotate=rotate,
    )
    return paste_text_on_image(
        Image.open(BytesIO(sticker_img)).convert("RGBA"),
        text_img,
        x or info.default_text.x,
        y or info.default_text.y,
        rotate or rad2deg(info.default_text.r / 10),
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
    bg = Image.new("RGBA", (width, height), background or ONE_DARK_BLACK)

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


async def render_help_image(text: str) -> Image.Image:
    font = ensure_font()
    font_size = 24
    line_spacing = 1.2
    width = 950
    padding = 24

    # 这个空行还有缩进的处理，实属无奈
    wrapped = [
        x[1:] if x.startswith(">") else x
        for x in itertools.chain.from_iterable(
            (
                text_wrap(
                    f">{x}" if x.startswith(" ") else x,
                    width - padding * 2,
                    font_size,
                    font,
                )
                if x
                else " "
            )
            for x in text.splitlines()
        )
    ]
    size = text_size_multiline(wrapped, font_size, font, line_spacing)

    canvas = Canvas(width, size[1] + padding * 2, Color.from_hex(ONE_DARK_BLACK))
    draw_text_multiline(
        canvas,
        wrapped,
        padding,
        padding,
        0,
        0,
        400,
        font_size,
        font,
        Paint(Color.from_hex(ONE_DARK_WHITE)),
        line_spacing,
    )

    return canvas.to_image()


@overload
def use_image_cache(
    func: Callable[P, Awaitable[Image.Image]],
    filename: str,
    image_format: str = "JPEG",
    background: Optional[ColorType] = None,
) -> Callable[P, Awaitable[bytes]]:
    ...


@overload
def use_image_cache(
    func: Callable[P, Awaitable[Optional[Image.Image]]],
    filename: str,
    image_format: str = "JPEG",
    background: Optional[ColorType] = None,
) -> Callable[P, Awaitable[Optional[bytes]]]:
    ...


def use_image_cache(
    func: Callable[P, Awaitable[Optional[Image.Image]]],
    filename: str,
    image_format: str = "JPEG",
    background: Optional[ColorType] = None,
) -> Callable[P, Awaitable[Optional[bytes]]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[bytes]:
        path = anyio.Path(CACHE_FOLDER) / f"{filename}.{image_format.lower()}"
        if await path.exists():
            return await path.read_bytes()

        raw_image = await func(*args, **kwargs)
        if not raw_image:
            return None

        image = i2b(raw_image, image_format, background)
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
