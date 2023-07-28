from nonebot import require
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_saa")

from . import __main__ as __main__  # noqa: E402
from .config import ConfigModel  # noqa: E402

__version__ = "0.2.1"
__plugin_meta__ = PluginMetadata(
    name="Sekai Stickers",
    description="基于 NoneBot2 的 Project Sekai 表情包制作插件",
    usage="使用指令 `pjsk -h` 获取指令帮助",
    type="application",
    homepage="https://github.com/Agnes4m/nonebot_plugin_pjsk",
    config=ConfigModel,
    supported_adapters={
        "~onebot.v11",
        "~onebot.v12",
        "~kaiheila",
        "~qqguild",
        "~telegram",
    },
    extra={
        "version": __version__,
        "author": ["Agnes4m <Z735803792@163.com>", "student_2333 <lgc2333@126.com>"],
    },
)
