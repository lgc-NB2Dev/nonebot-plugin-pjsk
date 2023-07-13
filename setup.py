from setuptools import find_packages, setup

setup(
    name="nonebot_plugin_pjsk",
    version="0.0.2",
    author="Agnes4m <Z735803792@163.com>",
    author_email="Z735803792@163.com",
    description="pjsk表情包生成,适配nonebot2的插件",
    python_requires=">=3.8.0",
    packages=find_packages(),
    url="https://github.com/Agnes4m/nonebot_plugin_pjsk",
    package_data={"nonebot_plugin_pjsk": ["resource/*","resource/*/*"]},
    # 设置依赖包
    install_requires=["pillow", "nonebot2", "nonebot-adapter-onebot"],
)
