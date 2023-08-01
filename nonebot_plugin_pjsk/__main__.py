from typing import List, Optional

from nonebot import logger, on_command, on_shell_command
from nonebot.exception import ParserExit
from nonebot.internal.adapter import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg, ShellCommandArgs
from nonebot.rule import ArgumentParser, Namespace
from nonebot.typing import T_State
from nonebot_plugin_saa import Image, MessageFactory, MessageSegmentFactory, Text
from numpy import rad2deg

from .config import config
from .draw import (
    DEFAULT_FONT_WEIGHT,
    DEFAULT_LINE_SPACING,
    DEFAULT_STROKE_WIDTH,
    TextTooLargeError,
    draw_sticker,
    get_all_characters,
    get_character_stickers,
    i2b,
    render_help_image,
    use_image_cache,
)
from .resource import select_or_get_random
from .utils import ResolveValueError, resolve_value

cmd_sticker_list = on_command(
    "pjsk列表",
    aliases={"啤酒烧烤列表", "pjsk表情列表", "啤酒烧烤表情列表"},
    state={"interact": False},
)

cmd_generate_parser = ArgumentParser("pjsk")
cmd_generate_parser.add_argument("text", nargs="*", help="添加的文字，为空时使用默认值")
cmd_generate_parser.add_argument(
    "-i",
    "--id",
    help="表情 ID，可以通过指令 `pjsk列表` 查询，不提供时则随机选择",
)
cmd_generate_parser.add_argument("-x", help="文字的中心 x 坐标")
cmd_generate_parser.add_argument("-y", help="文字的中心 y 坐标")
cmd_generate_parser.add_argument("-r", "--rotate", help="文字旋转的角度")
cmd_generate_parser.add_argument("-s", "--size", help="文字的大小，不指定时会以默认大小为最大值自动调整")
cmd_generate_parser.add_argument("-w", "--weight", help="文本粗细")
cmd_generate_parser.add_argument("--stroke-width", help="文本描边宽度")
cmd_generate_parser.add_argument("--line-spacing", help="文本行间距")

cmd_generate = on_shell_command(
    "pjsk",
    parser=cmd_generate_parser,
    aliases={"啤酒烧烤"},
    priority=2,
)


HELP = (
    "Project Sekai 表情生成\n"
    "\n"
    f"{cmd_generate_parser.format_help()}\n"
    "\n"
    "Tips：\n"
    "- 大部分有默认值的数值参数都可以用 ^ 开头指定相对于默认值的偏移量\n"
    "- 不提供任何指令参数时会进入交互创建模式"
)


async def handle_exit(matcher: Matcher, arg: str):
    if arg in ("0", "q", "e", "quit", "exit", "退出"):
        await matcher.finish("已退出交互创建模式")


def format_error(error: Exception) -> str:
    if isinstance(error, ResolveValueError):
        return f"提供的参数值 `{error.args[0]}` 解析出错"
    if isinstance(error, TextTooLargeError):
        return "你给的参数是不是有点太逆天了 😅"
    logger.opt(exception=error).error("Error occurred while drawing sticker")
    return "生成表情时出错，请检查后台日志"


# failed to parse args
@cmd_generate.handle()
async def _(matcher: Matcher, foo: ParserExit = ShellCommandArgs()):
    if not foo.message:
        return

    if foo.status == 0:
        if config.pjsk_help_as_image:
            try:
                img = await use_image_cache(render_help_image, "help", "JPEG")(HELP)
            except Exception:
                logger.exception("Error occurred while rendering help image")
                await matcher.finish("生成帮助图片时出错，请检查后台日志")
            await MessageFactory([Image(img)]).finish(reply=True)

        await matcher.finish(HELP)

    await matcher.finish(f"参数解析出错：{foo.message}")


# command or enter interact mode handler
@cmd_generate.handle()
async def _(matcher: Matcher, args: Namespace = ShellCommandArgs()):
    if not any(vars(args).values()):  # 没有任何参数
        matcher.skip()  # 跳过该 handler 进入交互模式

    sticker_id: Optional[str] = args.id
    selected_sticker = select_or_get_random(sticker_id)
    if not selected_sticker:
        await matcher.finish("没有找到对应 ID 的表情")

    texts: List[str] = args.text
    default_text = selected_sticker.default_text
    try:
        image = await draw_sticker(
            selected_sticker,
            text=" ".join(texts),  # if texts else default_text.text,
            x=resolve_value(args.x, default_text.x),
            y=resolve_value(args.y, default_text.y),
            rotate=resolve_value(args.rotate, rad2deg(default_text.r / 10)),
            font_size=resolve_value(args.size, default_text.s),
            stroke_width=resolve_value(args.stroke_width, DEFAULT_STROKE_WIDTH),
            line_spacing=resolve_value(args.line_spacing, DEFAULT_LINE_SPACING, float),
            font_weight=resolve_value(args.weight, DEFAULT_FONT_WEIGHT),
            auto_adjust=args.size is None,
        )
    except Exception as e:
        await matcher.finish(format_error(e))

    await MessageFactory([Image(i2b(image))]).finish(reply=True)


# interact mode or sticker list
@cmd_sticker_list.handle()
async def _(matcher: Matcher, arg: Message = CommandArg()):
    if arg.extract_plain_text().strip():
        matcher.set_arg("character", arg)


# character list
@cmd_generate.handle()
@cmd_sticker_list.handle()
async def _(matcher: Matcher, state: T_State):
    if "character" in state:
        matcher.skip()

    interact = state.get("interact", True)
    tip_text = (
        "请发送你要生成表情的角色名称，或者直接发送表情 ID，或者发送 `随机` 使用一张随机表情\nTip：你可以随时发送 `0` 退出交互模式"
        if interact
        else "Tip：发送指令 `pjsk列表 <角色名>` 查看角色下所有表情的 ID"
    )

    try:
        image = await get_all_characters()
    except Exception:
        logger.exception("Error occurred while getting character list")
        await matcher.finish("获取角色列表图片出错，请检查后台日志")

    factory = MessageFactory([Image(image), Text(tip_text)])
    await (factory.send if interact else factory.finish)(reply=True)


# sticker id list
@cmd_generate.got("character")
@cmd_sticker_list.got("character")
async def _(matcher: Matcher, state: T_State, arg_msg: Message = Arg("character")):
    character = arg_msg.extract_plain_text().strip()
    await handle_exit(matcher, character)

    interact = state.get("interact", True)

    # 交互模式
    if interact:
        if character == "随机":
            matcher.set_arg("sticker_id", type(arg_msg)())
            matcher.skip()

        elif character.isdigit():  # 直接发送了表情 ID
            if not select_or_get_random(character):
                await matcher.reject("没有找到对应 ID 的表情，请重新输入")
            matcher.set_arg("sticker_id", arg_msg)
            matcher.skip()

    try:
        image = await get_character_stickers(character)
    except Exception:
        logger.exception("Error occurred while getting sticker list")
        await matcher.finish("获取表情列表图片出错，请检查后台日志")

    if not image:
        if interact:
            await matcher.reject("没有找到对应名称的角色，请重新输入")
        await matcher.finish("没有找到对应名称的角色")

    segments: List[MessageSegmentFactory] = [Image(image)]
    if interact:
        segments.append(Text("请发送你要生成表情的 ID"))

    factory = MessageFactory(segments)
    await (factory.send if interact else factory.finish)(reply=True)


# below are interact mode handlers
@cmd_generate.got("sticker_id")
async def _(matcher: Matcher, arg: str = ArgPlainText("sticker_id")):
    arg = arg.strip()
    await handle_exit(matcher, arg)

    if not select_or_get_random(arg or None):  # 上面传过来的空消息转 None 获取随机表情
        await matcher.reject("没有找到对应 ID 的表情，请重新输入")
    await matcher.send("请发送你想要写在表情上的的文字")


@cmd_generate.got("text")
async def _(
    matcher: Matcher,
    sticker_id: str = ArgPlainText(),
    text: str = ArgPlainText(),
):
    sticker_info = select_or_get_random(sticker_id)
    assert sticker_info is not None

    try:
        image = await draw_sticker(
            sticker_info,
            text=text,
            auto_adjust=True,
        )
    except Exception as e:
        await matcher.finish(format_error(e))

    await MessageFactory([Image(i2b(image))]).finish(reply=True)
