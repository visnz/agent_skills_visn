# 平台接口与字段结构

本文件记录这次任务实际验证过的平台接口、字段结构和调用方式，供按需读取。路径、token、页面 ID 均为当时的现场值，历史性质，不作为默认配置。

## Wolai MCP

- 地址：`https://api.wolai.com/v1/mcp`
- 认证：`Authorization: Bearer <token>`（token 从 Wolai「空间相关 → 应用设置」创建应用获取，或 MCP 连接 token）
- 协议：JSON-RPC 2.0，`tools/call` 形式；返回 SSE，`data:` 后是单行 JSON（内层 `text` 是二次 JSON 字符串）。

关键方法：

| 方法 | 用途 | 关键参数 |
| --- | --- | --- |
| `tools/list` | 列可用方法 | — |
| `list_docs` | 列空间顶级页面 | — |
| `get_page_blocks` | **一次性拿整页扁平块列表**（深度优先，比逐块递归高效） | `page_id` |
| `get_doc` | 读单个块/页面 | `doc_id`, `include_blocks` |
| `delete_block` | 删块 | `block_id`, `forever`(默认 false=回收站) |

数据结构要点：

- `get_page_blocks` 返回 `data.data` 是块数组，每块有 `id`、`parent_id`、`type`、`content`、`media`、`children`。
- 剪藏页的每条剪藏通常是一个 `toggle_list`（折叠块，即"三角箭头"），其子块里才有实际内容。
- 链接所在字段因类型而异：
  - `embed` 块：`media.url` / `original_link` / `embed_link`
  - `text` 块：`content[0].link`
  - `image` 块：`media.download_url`（可直接下载，但带 auth_key、约 1800 秒过期）
- 删除一条剪藏 = 删其顶层 `toggle_list` 块。裸链接（直接挂页面根、无折叠块包裹）则删块自身。

回溯顶层块的方法：沿 `parent_id` 向上找 `type == "toggle_list"` 的块；找不到（裸块）则返回块自身。

## Eagle MCP

- 地址：`http://127.0.0.1:41596/mcp`（Eagle 桌面端需开启）
- 认证：无（本地）
- 协议：JSON-RPC 2.0；返回 SSE，`data:` 后是完整单行 JSON，但**含中文时可能被错误解码导致损坏**。

关键方法：

| 方法 | 用途 | 关键参数 |
| --- | --- | --- |
| `tools/list` | 列可用方法 | — |
| `item_add` | 导入素材 | `items: [{source: {type:"path", path}, tags, annotation}]`, `tags` |
| `item_get` | 查素材 | `ids` 或 `tags` |
| `item_count` | 统计 | `tags` |
| `item_update` | 更新素材 | `items: [{id, ...}]` |
| `get_app_info` / `folder_get` | 应用信息 / 文件夹列表 | — |

`item_add` 返回里有 **`successCount` / `totalCount` / `message: "Added N/M items"`**，这是确认入库成功、判断是否删源的关键依据。

字段注意：

- 图片/文件用 `source.type = "path"` 导入。
- **不传中文 `name` 字段**（会触发编码问题，返回 JSON 损坏）；中文信息放 `annotation`（安全）。
- Eagle MCP 目前**不支持直接写「来源网址」字段**（`item_update` 传 `url` 也不生效），只能用 `annotation` 存来源链接。

## 下载引擎

### XHS-Downloader（小红书）

- 来源：`github.com/JoeanAmier/XHS-Downloader`
- 关键：导入是 `from source import XHS`（不是 `source.application.app`）；CLI 是 `python main.py --url <链接> --work_path <目录> --folder_name "" --image_format PNG`，**没有 `download` 子命令**。
- **内置去重库**（记录作品 ID，下载过就跳过），和脚本自身去重冲突时加 `--download_record false` 关闭。
- 不带 Cookie 也能下（画质低），带 `web_session` Cookie 提画质。
- 链接形态：`xhslink.com` 短链和完整长链（含 `xsec_token` 等追踪参数）本质同一作品，工具只取作品 ID；带 `xsec_token` 的链接可能需有效 Cookie。

### gallery-dl（X/推特）

- 安装：`pip install gallery-dl`
- X 对未登录访问限制严，需 `auth_token`（+ 可选 `ct0`）Cookie 才能稳定下载。
- 免登录公开接口 `cdn.syndication.twimg.com/tweet-result`（token = `(id/1e15*pi)` 转 base36 去小数点/前导零）可拿图片原图/视频地址，但国内网络访问该 CDN 不稳，不可靠。

## 通用踩坑速查

- 多 Python 环境：bat 写死解释器绝对路径。
- SSE 多行 `data:`：拼接连续 `data:` 行再 `json.loads`。
- MCP 中文返回：不传中文 name，用 annotation。
- 下载器去重：用脚本 state 去重，关下载器内置去重。
