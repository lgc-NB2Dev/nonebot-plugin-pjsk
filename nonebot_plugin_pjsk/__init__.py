from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Message
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot import on_command
from nonebot.plugin import PluginMetadata

from .draw import *

__version__ = "0.0.2"
__plugin_meta__ = PluginMetadata(
    name="pjsk表情",
    description="pjsk表情",
    usage="pjsk表情",
    type="application",
    homepage="https://github.com/Agnes4m/nonebot_plugin_pjsk",
    supported_adapters={"~onebot.v11"},
    extra={
        "version": __version__,
        "author": "Agnes4m <Z735803792@163.com>",
    },
)

pjsk = on_command("pjsk", aliases={"啤酒烧烤"}, priority=10)


@pjsk.handle()
async def _(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    text = arg.extract_plain_text()
    if text:
        await make_ramdom(text)
        await matcher.send(MessageSegment.image(png_path))
