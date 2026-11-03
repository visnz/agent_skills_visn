# 案例：2026-10-31 xhs-sync 开发实录

本次真实任务的复盘记录。保留证据链与未解决项，供未来同类任务参考判断。现场路径/参数仅代表当时环境，历史性质。

## 需求演变（关键决策轨迹）

1. 初始：用户用 Wolai 剪藏（小红书/图片/文字），想自动分流，省去每天手动清理。
2. 澄清真实痛点：**省去"回家打开链接 → 猫抓下载 → 手动拖进 Eagle"**，不是 7×24 同步。
3. 关键转折：用户有阿里云 ECS，最初设想"装浏览器维持登录 + 服务器常驻"，后被否定——**改成本地脚本，需要时跑一下**，砍掉服务器/同步盘/SSH。
4. 接口确认：Wolai 个人版**有官方 MCP**（纠正了"个人版无 API"的过时结论）；Eagle 有本地 MCP，可直接入库。

## 最终架构

```text
手机微信 → Wolai 剪藏（存链接）
  → 本地脚本（双击 bat）
    → Wolai MCP get_page_blocks 读剪藏
    → 识别小红书/X/图片三类
    → XHS-Downloader / gallery-dl 下载到独立临时目录
    → Eagle MCP item_add 入库（打标签 + annotation 存来源）
    → 解析 successCount 确认成功
    → Wolai delete_block 删已处理词条
```

## 踩坑与修复（均有实证）

| 问题 | 现象 | 根因 | 修复 |
| --- | --- | --- | --- |
| 下载"无文件产出" | 脚本跑完显示 0 产出，但手动跑能下 | 下载器内置去重库，下载过一次就"跳过" | 加 `--download_record false`，用脚本 state.json 去重 |
| 入库报 JSON 错误 | `Unterminated string` | Eagle 返回的中文 name 被错误解码 | 不传 name，中文存 annotation |
| 双击 bat 报 `No module named 'click'` | 缺依赖 | 多 Python 环境，双击命中的 Python 没装依赖 | bat 写死验证过的解释器绝对路径 |
| bat 中文乱码 | 中文被当命令执行 | cmd 用 GBK 读 UTF-8 bat | bat 用纯 ASCII |

## 验证情况

- ✅ 小红书完整跑通：视频 + 图文（50 张）下载 → 入库 Eagle → 删 Wolai 词条，端到端验证有效。
- ✅ Eagle 返回 `successCount` 字段确认存在，作为防误删依据。
- ⚠️ X/推特：代码写好（gallery-dl 分支），但用户珍惜账号未配 auth_token，**下载未实测**，仅验证链接识别。
- ⚠️ 免登录 syndication 接口：算法验证正确、偶发可通，但用户网络下 SSL 不稳，未采用。

## 未解决 / 待后续

- X 下载需 auth_token（用户暂缓，账号风险顾虑）。
- Eagle MCP 无法写「来源网址」字段（只能 annotation），待 Eagle 版本更新。
- 小红书 Cookie 未配（不配也能下，配了画质更稳，需定期刷新）。
- 其他平台（B 站、GitHub、米画师、Telegram）未接入，脚本只覆盖小红书 + X + 图片三类。
