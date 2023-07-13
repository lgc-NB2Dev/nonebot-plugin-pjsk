import aiohttp
import shutil

from .config import module_path, background_path, download_url

zip_path = module_path.joinpath("res.zip")


async def get_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            if res.status == 200:
                return await res.read()
            else:
                return None


async def check_res():
    if not background_path.exists():
        with open(zip_path, mode="wb", encoding="utf-8") as f:
            f.write(await get_url(download_url))
        shutil.make_archive(module_path, "zip", zip_path)
        return "初始化完成，成功下载资源"
    else:
        return "检测到已下载资源，跳过下载"
