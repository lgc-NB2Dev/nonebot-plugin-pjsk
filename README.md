<!-- markdownlint-disable MD026 MD031 MD033 MD036 MD041 -->

<div align="center">

<a href="https://v2.nonebot.dev/store">
  <img src="https://raw.githubusercontent.com/Agnes4m/nonebot_plugin_l4d2_server/main/image/logo.png" width="180" height="180" alt="NoneBotPluginLogo">
</a>

<p>
  <img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText">
</p>

# NoneBot-Plugin-PJSK

_✨ Project Sekai 表情包制作 ✨_

<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
<a href="https://pdm.fming.dev">
  <img src="https://img.shields.io/badge/pdm-managed-blueviolet" alt="pdm-managed">
</a>
<a href="https://jq.qq.com/?_wv=1027&k=l82tMuPG">
  <img src="https://img.shields.io/badge/QQ%E7%BE%A4-424506063-orange" alt="QQ Chat Group">
</a>

<br />

<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/Agnes4m/nonebot_plugin_pjsk.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-pjsk">
  <img src="https://img.shields.io/pypi/v/nonebot-plugin-pjsk.svg" alt="pypi">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-pjsk">
  <img src="https://img.shields.io/pypi/dm/nonebot-plugin-pjsk" alt="pypi download">
</a>

</div>

## 📖 介绍

### Wonderhoy!

![Wonderhoy](./readme/wonderhoy.png)

## 💿 安装

以下提到的方法 任选**其一** 即可

<details open>
<summary>[推荐] 使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

```bash
nb plugin install nonebot-plugin-pjsk
```

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

```bash
pip install nonebot-plugin-pjsk
```

</details>
<details>
<summary>pdm</summary>

```bash
pdm add nonebot-plugin-pjsk
```

</details>
<details>
<summary>poetry</summary>

```bash
poetry add nonebot-plugin-pjsk
```

</details>
<details>
<summary>conda</summary>

```bash
conda install nonebot-plugin-pjsk
```

</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分的 `plugins` 项里追加写入

```toml
[tool.nonebot]
plugins = [
    # ...
    "nonebot_plugin_pjsk"
]
```

</details>

## ⚙️ 配置

插件有配置项，但是一般情况下无需更改，请自行查看 [config.py](./nonebot_plugin_pjsk/config.py) 文件

## 🎉 使用

直接使用指令 `pjsk` 进入交互创建模式；  
使用指令 `pjsk -h` 了解使用 Shell-Like 指令创建表情的帮助

### 效果图

<details>
<summary>使用交互创建模式</summary>

![example](./readme/example-interact.png)

</details>

<details>
<summary>使用 Shell-Like 指令</summary>

![example](./readme/example.png)

</details>

## 🙈 碎碎念

- ~~由于本人没玩过啤酒烧烤，~~ 可能出现一些小问题，可以提 issue 或者 [加群](https://jq.qq.com/?_wv=1027&k=l82tMuPG)反馈 ~~或者单纯进来玩~~
- 本项目仅供学习使用，请勿用于商业用途，喜欢该项目可以 Star 或者提供 PR，如果构成侵权将在 24 小时内删除
- [爱发电](https://afdian.net/a/agnes_digital)

## 💡 鸣谢

### [TheOriginalAyaka/sekai-stickers](https://github.com/TheOriginalAyaka/sekai-stickers)

- 原项目 & 素材来源

## 💰 赞助

感谢大家的赞助！你们的赞助将是我继续创作的动力！

- [爱发电](https://afdian.net/a/agnes_digital)

## 📝 更新日志

### 0.2.2

- 修改了 0.2.1 版的交互创建模式的触发方式
- 试验性地支持了 Emoji

### 0.2.1

- 更改指令 `pjsk列表` 的交互方式

### 0.2.0

- 重构插件
