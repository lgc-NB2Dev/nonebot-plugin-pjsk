from io import BytesIO
from typing import Optional

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

from .resource import FONT_PATHS, RESOURCE_FOLDER, StickerInfo

FONT: Optional[Font] = None
WHITE_COLOR = Color(255, 255, 255)
WHITE_PAINT = Paint(WHITE_COLOR)
TRANSPARENT_COLOR = Color(255, 255, 255, 0)


def ensure_font() -> Font:
    if not FONT:
        global FONT
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
        actual_size[1] + padding * 2 + font_size // 2,  # 更多纵向 padding 防止文字被裁切
    )

    canvas = Canvas(*size, TRANSPARENT_COLOR)
    draw_text_multiline(
        canvas,
        text_lines,
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
        stoke_width,  # type: ignore 这里是源代码有问题
        WHITE_PAINT,
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


def i2b(image: Image.Image) -> bytes:
    b = BytesIO()
    image.save(b, format="PNG")
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
) -> bytes:
    sticker_img = await anyio.Path(RESOURCE_FOLDER / info.img).read_bytes()
    text_img = render_text(
        text or info.default_text.text,
        info.color,
        font_size or info.default_text.s,
        font_weight or 700,
        stroke_width or 9,
        line_spacing or 1.3,
    )
    final_img = paste_text_on_image(
        Image.open(BytesIO(sticker_img)).convert("RGBA"),
        text_img,
        x or info.default_text.x,
        y or info.default_text.y,
        rotate or info.default_text.r,
    )
    final_img.show()
    return i2b(final_img)
