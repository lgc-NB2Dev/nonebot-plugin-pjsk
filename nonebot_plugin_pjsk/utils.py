import aiohttp
import shutil
import io
import zipfile

from nonebot.log import logger
from .config import module_path, background_path, download_url



async def get_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            if res.status == 200:
                return await res.read()
            else:
                return None


async def check_res():
    if not background_path.exists():
        background_path.mkdir(parents=True,exist_ok=True)
        logger.info("未检测到资源，开始下载资源")
        zip_bytes = await get_url(download_url)
        if not zip_bytes:
            return "链接错误捏"
        memory_file = io.BytesIO(zip_bytes)

        with zipfile.ZipFile(memory_file, mode="r") as z:
            z.extractall(background_path)
        return "初始化完成，成功下载资源"
    else:
        return "检测到已下载资源，跳过下载"
