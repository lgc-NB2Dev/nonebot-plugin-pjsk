from nonebot import get_driver
from pydantic import BaseModel, validator


class ConfigModel(BaseModel):
    pjsk_assets_prefix: str = (
        "https://raw.gitmirror.com/TheOriginalAyaka/sekai-stickers/main/"
    )
    pjsk_repo_prefix: str = (
        "https://raw.gitmirror.com/Agnes4m/nonebot_plugin_pjsk/main/"
    )

    @validator("pjsk_assets_prefix", "pjsk_repo_prefix")
    def check_url(cls, v):  # noqa: N805
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if not v.endswith("/"):
            v = f"{v}/"
        return v


config: ConfigModel = ConfigModel.parse_obj(get_driver().config.dict())
