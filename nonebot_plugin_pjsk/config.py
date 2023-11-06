from typing import List, Optional, Set

from imagetext_py import EmojiSource
from nonebot import get_driver
from pydantic import BaseModel, Field, HttpUrl, validator


class ConfigModel(BaseModel):
    command_start: Set[str]

    pjsk_req_retry: int = 2
    pjsk_req_proxy: Optional[str] = None
    pjsk_req_timeout: int = 10
    pjsk_assets_prefix: List[HttpUrl] = Field(
        [
            "https://ghproxy.com/https://raw.githubusercontent.com/TheOriginalAyaka/sekai-stickers/main/",
            "https://raw.gitmirror.com/TheOriginalAyaka/sekai-stickers/main/",
            "https://raw.githubusercontent.com/TheOriginalAyaka/sekai-stickers/main/",
        ],
    )
    pjsk_repo_prefix: List[HttpUrl] = Field(
        [
            "https://ghproxy.com/https://raw.githubusercontent.com/Agnes4m/nonebot_plugin_pjsk/main/",
            "https://raw.gitmirror.com/Agnes4m/nonebot_plugin_pjsk/main/",
            "https://raw.githubusercontent.com/Agnes4m/nonebot_plugin_pjsk/main/",
        ],
    )

    pjsk_emoji_source: str = "Apple"
    pjsk_help_as_image: bool = True
    pjsk_reply: bool = True
    pjsk_sticker_format: str = "PNG"

    @validator("pjsk_assets_prefix", "pjsk_repo_prefix", pre=True)
    def str_to_list(cls, v):  # noqa: N805
        if isinstance(v, str):
            v = [v]
        return v

    @validator("pjsk_assets_prefix", "pjsk_repo_prefix")
    def append_slash(cls, v):  # noqa: N805
        return [v if v.endswith("/") else f"{v}/" for v in v]

    @validator("pjsk_emoji_source", pre=True)
    def check_emoji_source(cls, v):  # noqa: N805
        try:
            getattr(EmojiSource, v)
        except AttributeError as e:
            raise ValueError("Invalid emoji source") from e
        return v

    def get_emoji_source(self) -> EmojiSource:
        return getattr(EmojiSource, self.pjsk_emoji_source)


config: ConfigModel = ConfigModel.parse_obj(get_driver().config.dict())
