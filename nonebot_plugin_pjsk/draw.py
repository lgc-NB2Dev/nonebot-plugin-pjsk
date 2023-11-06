import asyncio
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
    overload,
)
from typing_extensions import ParamSpec

import anyio
from anyio import to_thread
from imagetext_py import (
    Canvas,
    Color,
    EmojiOptions,
    Font,
    Paint,
    TextAlign,
    draw_text_multiline,
    text_size_multiline,
)
from numpy import deg2rad, rad2deg
from PIL import Image
from pil_utils import BuildImage, Text2Image
from pil_utils.fonts import DEFAULT_FALLBACK_FONTS
from pil_utils.types import ColorType

from .config import config
from .resource import (
    CACHE_FOLDER,
    FONT_PATH,
    LOADED_STICKER_INFO,
    RESOURCE_FOLDER,
    StickerInfo,
)
from .utils import chunks, qor

P = ParamSpec("P")

DEFAULT_STROKE_WIDTH = 9
DEFAULT_LINE_SPACING = 1.3
DEFAULT_STROKE_COLOR = "#ffffff"

CANVAS_SIZE = (296, 256)
MAX_TEXT_IMAGE_SIZE = 2048

TRANSPARENT = (0, 0, 0, 0)
ONE_DARK_BLACK = "#282c34"
ONE_DARK_WHITE = "#abb2bf"


class TextTooLargeError(ValueError):
    pass


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


def get_ax_by_align(align: TextAlign) -> float:
    if align is TextAlign.Left:
        return 0
    if align is TextAlign.Right:
        return 1
    return 0.5  # center


# 暂时想不到办法换了……
# pil_utils 的 stroke 会覆盖到前面的字
# python-skia 的 font fallback 不会写
async def render_text(
    text: str,
    color: str,
    font_size: int,
    stoke_width: int = DEFAULT_STROKE_WIDTH,
    stroke_color: ColorType = "#ffffff",
    line_spacing: float = DEFAULT_LINE_SPACING,
    align: TextAlign = TextAlign.Center,
    max_width: Optional[int] = None,
    will_rotate: Optional[float] = None,
    min_size: int = 8,
) -> Image.Image:
    font = Font(
        str(FONT_PATH),
        emoji_options=EmojiOptions(source=config.get_emoji_source()),
    )

    text_lines = text.splitlines()
    padding = stoke_width

    while True:
        actual_size = await to_thread.run_sync(
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

    if size[0] > MAX_TEXT_IMAGE_SIZE or size[1] > MAX_TEXT_IMAGE_SIZE:
        raise TextTooLargeError

    canvas = Canvas(*size, Color(*TRANSPARENT))
    stroke_color_obj = (
        hex_to_color(stroke_color)
        if isinstance(stroke_color, str)
        else Color(*stroke_color)
    )
    await to_thread.run_sync(
        partial(
            draw_text_multiline,
            canvas=canvas,
            lines=text_lines,
            x=size[0] // 2,
            y=size[1] // 2,
            ax=get_ax_by_align(align),
            ay=0.5,
            width=700,
            size=font_size,
            font=font,
            fill=Paint(hex_to_color(color)),
            line_spacing=line_spacing,
            align=align,
            stroke=stoke_width,  # type: ignore 源码 type 有问题
            stroke_color=Paint(stroke_color_obj),
            draw_emojis=True,
        ),
    )
    return canvas.to_image().convert("RGBA")


def paste_text_on_image(
    image: Image.Image,
    text: Image.Image,
    x: int,
    y: int,
    rotate: float,
) -> Image.Image:
    image = BuildImage(image).resize(CANVAS_SIZE, keep_ratio=True, inside=True).image

    text_bg = Image.new("RGBA", CANVAS_SIZE, TRANSPARENT)
    text = text.rotate(-rotate, resample=Image.BICUBIC, expand=True)
    text_bg.paste(text, (x - text.size[0] // 2, y - text.size[1] // 2), text)

    return Image.alpha_composite(image, text_bg)


def clean_image(image: Image.Image) -> Image.Image:
    import numpy

    # replace transparent pixels to black transparent pixels
    data = numpy.array(image.convert("RGBA"))
    alpha = data[:, :, 3]
    data[:, :, :3][alpha == 0] = [0, 0, 0]
    return Image.fromarray(data)


def i2b(
    image: Image.Image,
    image_format: str = config.pjsk_sticker_format,
    background: Optional[ColorType] = None,
) -> bytes:
    image_format = image_format.upper()

    if image_format == "JPEG":
        if background:
            new_image = Image.new("RGBA", image.size, background)
            image = Image.alpha_composite(new_image, image)
        image = image.convert("RGB")

    b = BytesIO()
    image.save(b, image_format)
    return b.getvalue()


async def draw_sticker(
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
    auto_adjust: bool = False,  # noqa: FBT001
) -> Image.Image:
    default_text = info.default_text
    x = qor(x, default_text.x)
    y = qor(y, default_text.y)
    font_size = qor(font_size, default_text.s)
    canvas_w = CANVAS_SIZE[0]
    center_x_offset = round(abs(canvas_w / 2 - x))

    sticker_img = await anyio.Path(RESOURCE_FOLDER / info.img).read_bytes()
    text_img = await render_text(
        qor(text, default_text.text),
        qor(font_color, info.color),
        font_size,
        qor(stroke_width, DEFAULT_STROKE_WIDTH),
        qor(stroke_color, DEFAULT_STROKE_COLOR),
        qor(line_spacing, DEFAULT_LINE_SPACING),
        max_width=canvas_w - center_x_offset if auto_adjust else None,
        will_rotate=rotate,
    )
    return paste_text_on_image(
        Image.open(BytesIO(sticker_img)).convert("RGBA"),
        text_img,
        x,
        y,
        qor(rotate, lambda: rad2deg(default_text.r / 10)),
    )
    # return clean_image(image) # 没用


def render_summary_picture(
    image_list: List[Image.Image],
    padding: int = 15,
    line_max: int = 5,
    background: Optional[ColorType] = None,
) -> Image.Image:
    lines = list(chunks(image_list, line_max))
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
    width = 1080
    font_size = 24
    padding = 24
    return (
        Text2Image.from_text(
            text,
            fontsize=font_size,
            fill=ONE_DARK_WHITE,
            fallback_fonts=[*DEFAULT_FALLBACK_FONTS, str(FONT_PATH)],
        )
        .wrap(width)
        .to_image(ONE_DARK_BLACK, padding=(padding, padding))
    )


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

    return await render_summary_from_tasks(
        draw_sticker(info, character) for character, info in character_dict.items()
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
