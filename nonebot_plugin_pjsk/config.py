from PIL import ImageFont

from typing import Dict, List
from pathlib import Path

from nonebot.log import logger


# 插件资源目录
module_path = Path("data/pjsk")

# 资源目录
background_path: Path = module_path / "resource"

# 字体文件
font_file: Path = module_path / "resource/ShangShouFangTangTi.ttf"
if not font_file.is_file:
    font_file = "ShangShouFangTangTi.ttf"

# 颜色文件
config_color: Dict[str, List[str]] = {
    "pink": ["airi", "emu", "Luka", "Mizuki"],
    "brown": ["akito", "Honami", "Meiko", "Minori"],
    "grey": ["an", "ena", "Shiho"],
    "blue": ["Haruka", "Touya"],
    "navy": ["Ichika"],
    "cyan": ["KAITO", "Miku", "Shizuku"],
    "aqua": ["Kanade"],
    "orange": ["Kohane", "Nene", "Len", "Rin", "Saki", "Tsukasa"],
    "purple": ["Mafuyu", "Rui"],
}

# 资源模板, key为文件夹名，value为文件夹下的图片，都是相对路径Path对象
try:
    template: Dict[Path, List[Path]] = {
        role: [i for i in role.iterdir() if i.suffix == ".png"]
        for role in [i for i in background_path.iterdir() if i.is_dir()]
    }
except FileNotFoundError:
    logger.warning("未下载素材")
    template =None
stroke_color = "white"
stroke_width = 7
default_font_size = 50
# rotation_angle = 10

try:
    font_style: ImageFont.FreeTypeFont = ImageFont.truetype(
        str(font_file), size=default_font_size, encoding="utf-8"
    )
except OSError:
    font_style = None

gh_proxy = "https://ghproxy.com/https://github.com/Agnes4m/nonebot_plugin_pjsk"
download_url = f"{gh_proxy}/releases/download/v0.0.4/resource.zip"
