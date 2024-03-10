from typing import Any, List, Optional, Set
from typing_extensions import Annotated

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, HttpUrl, validator


class ConfigModel(BaseModel):
    command_start: Set[str]

    pjsk_req_retry: int = 1
    pjsk_req_proxy: Optional[str] = None
    pjsk_req_timeout: int = 10
    pjsk_assets_prefix: List[Annotated[str, HttpUrl]] = Field(
        [
            "https://raw.gitmirror.com/TheOriginalAyaka/sekai-stickers/main/",
            "https://raw.githubusercontent.com/TheOriginalAyaka/sekai-stickers/main/",
        ],
    )
    pjsk_repo_prefix: List[Annotated[str, HttpUrl]] = Field(
        [
            "https://raw.gitmirror.com/Agnes4m/nonebot_plugin_pjsk/main/",
            "https://raw.githubusercontent.com/Agnes4m/nonebot_plugin_pjsk/main/",
        ],
    )

    pjsk_help_as_image: bool = True
    pjsk_reply: bool = True
    pjsk_use_cache: bool = True
    pjsk_clear_cache: bool = False

    @validator("pjsk_assets_prefix", "pjsk_repo_prefix", pre=True)
    def str_to_list(cls, v: Any):  # noqa: N805
        if isinstance(v, str):
            v = [v]
        if not (hasattr(v, "__iter__") and all(isinstance(x, str) for x in v)):
            raise ValueError("value should be a iterable of strings")
        return v

    @validator("pjsk_assets_prefix", "pjsk_repo_prefix")
    def append_slash(cls, v: List[str]) -> List[str]:  # noqa: N805
        return [v if v.endswith("/") else f"{v}/" for v in v]


config = get_plugin_config(ConfigModel)
