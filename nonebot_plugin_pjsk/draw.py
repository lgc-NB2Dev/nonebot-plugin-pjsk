import json
import random
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

# 插件目录
module_path = Path(__file__).parent

# 资源目录
background_path: Path = module_path / "resource"

# 字体文件
font_file: Path = module_path / "resource/ShangShouFangTangTi.ttf"

# 配置文件
with open(module_path / "config.json", mode="r", encoding="utf-8") as f:
    config_color: Dict[str, List[str]] = json.load(f)

# 资源模板, key为文件夹名，value为文件夹下的图片，都是相对路径Path对象
template: Dict[Path, List[Path]] = {
    role: [i for i in role.iterdir() if i.suffix == ".png"]
    for role in [i for i in background_path.iterdir() if i.is_dir()]
}

stroke_color = "white"
stroke_width = 7
default_font_size = 50
# rotation_angle = 10


font_style: ImageFont.FreeTypeFont = ImageFont.truetype(
    str(font_file), size=default_font_size, encoding="utf-8"
)


class TextConfig(BaseModel):
    """图片配置"""

    image_size: Tuple[int, int]
    text: str
    text_color: str
    font_start: Tuple[int, int] = (0, 0)
    stroke_width: int = 7
    rotation_angle: int = 10
    font_size: int


async def make_ramdom(text: str) -> bytes:
    """生成图片"""
    text = text.replace("\n", "")
    role: Path = random.choice(list(template.keys()))
    random_img: Path = random.choice(template[role])
    image: Image.Image = Image.open(random_img)
    text_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    text_config = text_draw(text, image.size, draw, role)
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
    bytes_data = BytesIO()
    image.save(bytes_data, format="png")
    return bytes_data.getvalue()


def text_draw(
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
    font_style = ImageFont.truetype(str(font_file), font_size)

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
