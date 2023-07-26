import random
from typing import List, Optional

from nonebot import logger, on_command, on_shell_command
from nonebot.exception import ParserExit
from nonebot.internal.adapter import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, ShellCommandArgs
from nonebot.rule import ArgumentParser, Namespace
from nonebot.typing import T_State
from nonebot_plugin_saa import Image, MessageFactory, MessageSegmentFactory

from .draw import (
    DEFAULT_FONT_WEIGHT,
    DEFAULT_LINE_SPACING,
    DEFAULT_STROKE_WIDTH,
    draw_sticker,
    i2b,
    render_all_characters,
    render_character_stickers,
    use_image_cache,
)
from .resource import LOADED_STICKER_INFO, StickerInfo
from .utils import ResolveValueError, resolve_value

cmd_sticker_list = on_command("pjsk列表", aliases={"啤酒烧烤列表", "pjsk表情列表"})


@cmd_sticker_list.handle()
async def _(matcher: Matcher, arg: Message = CommandArg()):
    # character = arg.extract_plain_text().strip()
    if character := arg.extract_plain_text().strip():
        try:
            img = await use_image_cache(render_character_stickers, character)(character)
        except Exception:
            logger.exception("Error occurred while rendering all characters")
            await matcher.finish("生成表情列表时出错，请检查后台日志")

        if not img:
            await matcher.finish(f"没有找到角色 {arg}")

        messages: List[MessageSegmentFactory] = [Image(img)]
        await MessageFactory(messages).finish(reply=True)
    else:
        img = await use_image_cache(render_all_characters, "all_characters")()
        await MessageFactory([Image(img)]).send(reply=True)


@cmd_sticker_list.got("character", prompt="请输入 <角色名>` 查看角色下所有表情的 ID")
async def _(matcher: Matcher, character: str = ArgPlainText()):
    img = await use_image_cache(render_character_stickers, character)(character)
    if not img:
        await matcher.finish(f"没有找到角色 {character}")
    await MessageFactory([Image(img)]).send(reply=True)


@cmd_sticker_list.got("sticker_id", prompt="请输入角色id")
async def _(state: T_State, matcher: Matcher, sticker_id: str = ArgPlainText()):
    selected_sticker = (
        next((x for x in LOADED_STICKER_INFO if sticker_id == x.sticker_id), None)
        if sticker_id
        else random.choice(LOADED_STICKER_INFO)
    )
    if not selected_sticker:
        await matcher.finish("没有找到对应 ID 的表情")
    state["selected_sticker"] = selected_sticker


@cmd_sticker_list.got("texts", prompt="请输入文字信息")
async def _(state: T_State, matcher: Matcher, texts: str = ArgPlainText()):
    selected_sticker: StickerInfo = state["selected_sticker"]
    default_text = selected_sticker.default_text
    try:
        image = await draw_sticker(
            selected_sticker,
            text=" ".join(texts) if texts else default_text.text,
            x=resolve_value(None, default_text.x),
            y=resolve_value(None, default_text.y),
            rotate=resolve_value(None, default_text.r),
            font_size=resolve_value(None, default_text.s),
            stroke_width=resolve_value(None, DEFAULT_STROKE_WIDTH),
            line_spacing=resolve_value(None, DEFAULT_LINE_SPACING, float),
            font_weight=resolve_value(None, DEFAULT_FONT_WEIGHT),
        )
    except ResolveValueError:
        await matcher.finish("参数解析出错")
    except Exception:
        logger.exception("Error occurred while drawing sticker")
        await matcher.finish("生成表情时出错，请检查后台日志")

    await MessageFactory([Image(i2b(image))]).finish(reply=True)


cmd_generate_parser = ArgumentParser(
    "pjsk",
    description="Project Sekai 表情生成",
    epilog="Tip：大部分有默认值的数值参数都可以用 `^` 开头指定相对于默认值的偏移量",
)
cmd_generate_parser.add_argument("text", nargs="*", help="添加的文字，为空时使用默认值")
cmd_generate_parser.add_argument(
    "-i",
    "--id",
    help="表情 ID，可以通过指令 `pjsk列表` 查询，不提供时则随机选择",
)
cmd_generate_parser.add_argument("-x", help="文字的中心 x 坐标")
cmd_generate_parser.add_argument("-y", help="文字的中心 y 坐标")
cmd_generate_parser.add_argument(
    "-r",
    "--rotate",
    type=str,
    help="文字旋转的角度，单位为 `(ROTATE / 10) 弧度`",
)
cmd_generate_parser.add_argument("-s", "--size", help="文字的大小")
cmd_generate_parser.add_argument("--stroke-width", help="文本描边宽度")
cmd_generate_parser.add_argument("--line-spacing", help="文本行间距")
cmd_generate_parser.add_argument("--weight", help="文本粗细")

cmd_generate = on_shell_command(
    "pjsk",
    parser=cmd_generate_parser,
    aliases={"啤酒烧烤"},
    priority=2,
)


@cmd_generate.handle()
async def _(matcher: Matcher, foo: ParserExit = ShellCommandArgs()):
    if not foo.message:
        return
    if foo.status == 0:
        await matcher.finish(foo.message)
    await matcher.finish(f"参数解析出错：{foo.message}")


@cmd_generate.handle()
async def _(matcher: Matcher, args: Namespace = ShellCommandArgs()):
    sticker_id: Optional[str] = args.id
    selected_sticker = (
        next((x for x in LOADED_STICKER_INFO if sticker_id == x.sticker_id), None)
        if sticker_id
        else random.choice(LOADED_STICKER_INFO)
    )
    if not selected_sticker:
        await matcher.finish("没有找到对应 ID 的表情")

    texts: Optional[List[str]] = args.text
    default_text = selected_sticker.default_text
    try:
        image = await draw_sticker(
            selected_sticker,
            text=" ".join(texts) if texts else default_text.text,
            x=resolve_value(args.x, default_text.x),
            y=resolve_value(args.y, default_text.y),
            rotate=resolve_value(args.rotate, default_text.r),
            font_size=resolve_value(args.size, default_text.s),
            stroke_width=resolve_value(args.stroke_width, DEFAULT_STROKE_WIDTH),
            line_spacing=resolve_value(args.line_spacing, DEFAULT_LINE_SPACING, float),
            font_weight=resolve_value(args.weight, DEFAULT_FONT_WEIGHT),
        )
    except ResolveValueError:
        await matcher.finish("参数解析出错")
    except Exception:
        logger.exception("Error occurred while drawing sticker")
        await matcher.finish("生成表情时出错，请检查后台日志")

    await MessageFactory([Image(i2b(image))]).finish(reply=True)
