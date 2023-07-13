import random
from io import BytesIO
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

from .config import (
    template,
    stroke_color,
    default_font_size,
    font_file,
    config_color,
    stroke_width,
)


class TextConfig(BaseModel):
    """图片配置"""

    image_size: Tuple[int, int]
    text: str
    text_color: str = "grey"
    font_start: Tuple[int, int] = (0, 0)
    stroke_width: int = 7
    rotation_angle: int = 10
    font_size: int


async def make_ramdom(text: str) -> bytes:
    """生成图片"""
    text_list = text.split(" ")
    role: Path = random.choice(list(template.keys()))
    random_img: Path = random.choice(template[role])
    image: Image.Image = Image.open(random_img)
    text_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_image)

    if len(text_list) == 1:
        text_config:TextConfig = await text_draw(text, image.size, draw, role)
        text_position = text_config.font_start
        draw.text(
            text_position,
            text_config.text,
            font=font_style,
            fill=stroke_color,
            stroke_width=text_config.stroke_width,
        )
        draw.text(
            xy=text_position,
            text=text_config.text,
            font=font_style,
            fill=text_config.text_color,
        )

    elif len(text_list) >= 2:
        for i, one_text in enumerate(text_list, start=0):
            text_config:TextConfig = await text_draw(one_text, image.size, draw, role)
            text_position = text_config.font_start
            text_position = (text_position[0],(text_position[-1] + (i * text_config.font_size)))
            draw.text(
                text_position,
                text_config.text,
                font=font_style,
                fill=stroke_color,
                stroke_width=text_config.stroke_width,
            )
            draw.text(
                xy=text_position,
                text=text_config.text,
                font=font_style,
                fill=text_config.text_color,
            )

    else:
        ...

    # print(text_config.font_start)

    # 旋转
    # if text_config.rotation_angle:
    #     text_bbox = draw.textbbox((0, 0), text_config.text, font_style)
    #     center = (
    #         (text_bbox[0] + text_bbox[2]) // 2,
    #         (text_bbox[1] + text_bbox[3]) // 2,
    #     )
    #     print(center)
    #     text_image = text_image.rotate(
    #         text_config.rotation_angle, expand=True, center=center
    #     )

    image.paste(text_image, (0, 0), mask=text_image)
    bytes_data = BytesIO()
    image.save(bytes_data, format="png")
    return bytes_data.getvalue()


async def text_draw(
    text: str,
    size: Tuple[int, int],
    draw: ImageDraw.ImageDraw,
    file_path: Path,
) -> TextConfig:
    """
    - text_list:文字
    - size:图片大小
    """
    global font_style
    # 根据字数调整字体大小
    if 1 <= len(text) <= 5:
        # 字数在2-5之间，使用默认字体大小
        font_size = default_font_size
        rotation_angle = 10
    else:
        # 字数超过5，需要适当减小字体大小
        font_size = int(default_font_size * (5 / len(text)))
        rotation_angle = 0

    # 重新加载字体
    font_style = await load_type(str(font_file), font_size)
    # 计算文字位置
    _, _, text_width, text_height = draw.textbbox((0, 0), text, font_style)
    text_x: int = (size[0] - text_width) // 2
    text_y: int = (size[1] - text_height) // 10

    return TextConfig(
        image_size=size,
        text=text,
        font_start=(text_x, text_y),
        stroke_width=stroke_width,
        text_color=color_check(file_path.name),
        rotation_angle=rotation_angle,
        font_size=50,
    )


def color_check(name: str) -> str:
    return next(
        (color for color, name_list in config_color.items() if name in name_list),
        "grey",
    )


async def load_type(font: str, font_size: int):
    """加载字体"""
    try:
        font_style = ImageFont.truetype(font, font_size)
    except ImageFont:
        return None
    return font_style
