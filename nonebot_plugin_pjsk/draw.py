from PIL import Image, ImageFont, ImageDraw
from pathlib import Path
from pydantic import BaseModel
from typing import Tuple, List, Dict
import random
import json

background_path = Path().joinpath("data/pjsk/img")
background_path.mkdir(exist_ok=True, parents=True)
font_file = Path().joinpath("data/pjsk/ShangShouFangTangTi.ttf")
png_path = Path("pjsk.png")
with open(
    Path(__file__).parent.joinpath("config.json"), mode="r", encoding="utf-8"
) as f:
    config_color: Dict[str, List[str]] = json.load(f)
stroke_color = "white"
stroke_width = 7
default_font_size = 50
# rotation_angle = 10
font_style: ImageFont.FreeTypeFont = ImageFont.truetype(
    str(font_file), size=default_font_size, encoding="utf-8"
)


class Text_Config(BaseModel):
    """图片配置"""

    image_size: Tuple[int, int]
    text: str
    text_color: str
    font_start: Tuple[int, int] = (0, 0)
    stroke_width: int = 7.0
    rotation_angle: int = 10.0
    font_size: int


async def make_ramdom(text: str):
    text_list = text.split("\n")

    first_path = random.choice(list(background_path.iterdir()))
    random_img = random.choice(list(first_path.iterdir()))
    image = Image.open(random_img)
    text_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    text_config = text_draw(text_list, image.size, draw, first_path, len(text))
    text_position = text_config.font_start

    # print(text_config.font_start)
    draw.text(
        text_position,
        text_config.text,
        font=font_style,
        fill=stroke_color,
        stroke_width=text_config.stroke_width,
    )
    draw.text(
        text_position, text_config.text, font=font_style, fill=text_config.text_color
    )

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
    image.save(png_path)
    # return image


def text_draw(
    text_list: List[str],
    size: Tuple[int, int],
    draw: ImageDraw.ImageDraw,
    file_path: Path,
    i: int = 1,
):
    """
    - text_list:文字
    - size:图片大小
    - i:默认就是1"""
    global font_style
    if len(text_list) == 1:
        text = text_list[0]
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
        font_style = ImageFont.truetype(str(font_file), font_size)

        # 计算文字位置
        text_width, text_height = draw.textsize(text, font_style)
        text_x = (size[0] - text_width) // 2
        text_y = (size[1] - text_height) // 10

        text_config = Text_Config(
            image_size=size,
            text=text,
            font_start=(text_x, text_y),
            stroke_width=stroke_width,
            text_color=color_check(file_path.name),
            rotation_angle=rotation_angle,
            font_size=50,
        )
    return text_config


def color_check(name: str):
    for color, name_list in config_color.items():
        if name in name_list:
            return color
    return "grey"
