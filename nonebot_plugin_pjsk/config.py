from imagetext_py import EmojiSource
from nonebot import get_driver
from pydantic import BaseModel, validator


class ConfigModel(BaseModel):
    pjsk_assets_prefix: str = (
        "https://raw.gitmirror.com/TheOriginalAyaka/sekai-stickers/main/"
    )
    pjsk_repo_prefix: str = "https://raw.gitmirror.com/Agnes4m/nonebot_plugin_pjsk/main/"

    pjsk_emoji_source: str = "Apple"
    """Emoji 来源，可选值见 https://github.com/nathanielfernandes/imagetext-py/blob/master/imagetext_py/imagetext_py.pyi#L217"""

    @validator("pjsk_assets_prefix", "pjsk_repo_prefix")
    def check_url(cls, v):  # noqa: N805
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if not v.endswith("/"):
            v = f"{v}/"
        return v

    @validator("pjsk_emoji_source")
    def check_emoji_source(cls, v):  # noqa: N805
        if not getattr(EmojiSource, v, None):
            raise ValueError("Invalid emoji source")


config: ConfigModel = ConfigModel.parse_obj(get_driver().config.dict())
