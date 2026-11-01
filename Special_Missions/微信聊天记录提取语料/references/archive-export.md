# 微信 4.x 聊天记录「HTML 归档」分支——技术复盘

从解密后的微信 4.x 数据库，把聊天记录（文字、图片、语音、文件、自定义表情）导出成**可离线浏览的 HTML 归档**。这是与「语料提取」并列的另一条分支输出，共享前面「定位数据 → 解密」两个环节（见 [wechat-4x-decrypt.md](wechat-4x-decrypt.md)），本文件只记录归档分支特有的做法和踩坑。

所有路径、wxid、UIN、密钥均为当时现场，执行前必须重新确认。账号身份信息一律用占位符，交付文档不出现真实聊天对象。

## 目标与产物

- 输入：解密后的 `db_storage/`（消息库、媒体库、表情库）+ 微信原始数据目录 `xwechat_files/<账号>/`（图片/文件/表情的原始加密文件）
- 输出：
  ```
  html/
  ├── index.html            # 总入口（合并时间线 + 各会话入口）
  ├── style.css             # 共享样式
  ├── merged/<月>.html       # 合并时间线（按月分段，群聊标注来源）
  └── <账号>/<会话>/<月>.html # 单聊视图
  media/
  ├── images_<账号>/         # 解密转码后的图片
  ├── files_<账号>/          # 文件/视频（原样复制）
  ├── voice/<svr_id>.mp3    # 语音（silk→mp3）
  └── emoji/<md5>.png|gif   # 自定义表情（CBC 解密→转码）
  ```

## 完整流水线（脚本按顺序跑）

脚本在 `scripts/` 下，`archive_` 前缀，与语料分支的 `clean_corpus.py` 并列。

**使用约定**：脚本之间通过「同一工作目录下的中间 JSON」衔接（`messages_raw.json`、`merged_by_month.json` 等）。实际导出时，先把 `archive_*` 脚本拷到一个独立工作目录再跑，**不要直接在 skill 仓库目录里跑**，避免中间产物污染仓库。脚本内的 `BASE = Path(__file__).resolve().parent` 会自动以所在目录为工作目录。

1. `archive_export_all.py` —— 从消息库抽取全量消息 → `messages_raw.json`（结构见下）
2. `archive_process_media.py` —— 分阶段处理媒体（emoji_map / voice_index / images / files）
3. `archive_process_voice.py` —— 语音 silk→mp3（用独立 `voice_env`，见下）
4. `archive_process_emoji.py` —— 自定义表情 CBC 解密→转码
5. `archive_preprocess.py` —— 消息分组去重 → `merged_by_month.json` + `chat_by_month.json`
6. `archive_gen_html.py` —— 生成 HTML

图片和语音是重活，放后台跑，其余秒级完成。

## 消息库结构（4.x，区别于 3.x）

- 消息库：`db_storage/message/message_0.db` ~ `message_N.db`（SQLCipher 加密，需先解密，见 decrypt 文档）
- **每个会话一张 `Msg_<md5(username)>` 表**，不是统一 messages 表
- `local_type` 是 `(subtype << 32) | base_type` 组合值，取 `local_type & 0xFFFF` 得真实类型
- 部分 `message_content` 是 **zstd 压缩**的（由 `WCDB_CT_*` 标志位指示），需解压
- `create_time` 是**秒**（不是毫秒）

### 消息类型（base_type）

| type | 含义 | 备注 |
|---|---|---|
| 1 | 文字 | content 为明文 |
| 34 | 语音 | content 是 XML，含 `voicelength`、`voiceformat`，`server_id` 关联 VoiceInfo |
| 43 | 视频 | XML 含 md5/size |
| 47 | 表情 | XML 含 md5、cdnurl、aeskey、productid |
| 49 | 应用消息 | 引用/链接/文件/转账/红包/小程序等，全是 XML |

## 关键破解（本次实战验证）

### 1. 图片 V2 加密

`.dat` 文件格式（头 `07 08 56 32 08 07`）：

```
[6B magic: 07 08 56 32 08 07] [4B aes_size] [4B xor_size] [1B flag]
[AES-128-ECB 密文] [raw 明文] [单字节 XOR 尾部]
```

- AES key = `md5(十进制UIN + wxid)[:16]` 的 **ASCII 编码**（16 字节）
- XOR key 从缩略图 `_t.dat` 尾部反推（JPEG 尾 `FF D9`）
- 解密后**原图是 `wxgf` 容器**（头 `77786766`，即 `wxgf`），不是 jpg/png——里面是 HEVC 视频流，静态图用视频编码存
- `wxgf` 用 ffmpeg 解单帧转 PNG：`ffmpeg -i pipe:0 -frames:v 1 -update 1 out.png`；直接吃 wxgf 失败时，提取 Annex-B 起始码（`00 00 00 01`）后的裸流，用 `-f hevc` 输入

### 2. 自定义表情 CBC 解密（最卡的一关）

- 表情文件：`business/emoticon/Persist/<md5前2位>/<完整md5>`（无扩展名）
- 元数据：`emoticon.db` 的 `kNonStoreEmoticonTable`（自定义/收藏）和 `kStoreEmoticonCaptionsTable`（商店表情 md5→描述词）
- 加密：**AES-128-CBC，IV = key 本身**（`AES.new(key, AES.MODE_CBC, key)`）——这是关键顿悟，IV 不是随机、不是全零、不是首块，就是 key
- key 派生：`key = md5(f"{UIN}{wxid}EMOTICON").digest()[:16]`（UIN 即 seed，账号级）
- 解密后是 `wxgf`，同样走 ffmpeg 转 png；`gif`/`webp` 直接保留原格式
- **注意**：`aes_key` 列在 kNonStoreEmoticonTable 里存在，但**不是**解密 key，别被误导——真正的 key 走上面的 md5 派生

### 3. 语音 SILK 转码

- 语音 BLOB 在 `media_0.db` 的 `VoiceInfo` 表：`svr_id` + `voice_data`（纯 SILK_V3，头 `02 23 21 53 49 4C 4B 5F 56 33` = `\x02#!SILK_V3`）
- 消息里的 `server_id` = VoiceInfo 的 `svr_id`（关联字段）
- 解码用 **pilk** 库（`from pilk import decode`），silk→pcm→wav，再 ffmpeg 转 mp3（`libmp3lame -b:a 32k -ar 24000`）
- **环境隔离**：pilk 的 `.pyd` 是 cp38 编译的，与解密环境的 Python 版本不兼容（`ModuleNotFoundError: pilk._pilk`）。语音转码必须用独立 `voice_env`（Python 3.8）跑
- 临时文件放系统 temp 目录（`tempfile.TemporaryDirectory`），避免工作目录内反复创建/删除 wav 触发文件安全拦截

### 4. 群聊跨账号去重

- 两个账号（大号/小号）各自存了同一个群的镜像，时间戳有 ±1 秒错位，`is_me` 是相对的（各自视角）
- 去重用 **`server_id`**（服务端唯一，两账号视角一致），缺失时回退 `(create_time, sender_wxid, 文本, md5)`
- 身份判断用 `sender_wxid` 统一映射（`who_is`），**不要用 `is_me`**（群聊镜像里它相对）

### 5. 群聊 content 前缀

群聊消息的 `content` 开头带 `发送者wxid:\n` 前缀（13.9 万条），单聊没有。解码时要剥离，并用前缀 wxid 修正 sender：

```python
if is_group and content.startswith("wxid_"):
    m = re.match(r"^(wxid_[0-9a-zA-Z]+):\s*\n?", content)
    if m:
        sender_from_prefix = m.group(1)
        content = content[m.end():]
```

## messages_raw.json 结构

```json
{
  "meta": {...},
  "conversations": {
    "<账号>__<会话>": [  // 如 "da_hao__her_da", "xiao_hao__group"
      {
        "type": "1", "raw_type": 1, "create_time": 1750762727,
        "time_str": "2025-06-24 18:58:47",
        "is_me": false, "sender_wxid": "wxid_xxx",
        "local_id": 54, "server_id": 8905964321487737098,
        "db": "message_0.db", "content": "...", "text": "...",
        "kind": "text|image|voice|video|emoji|appmsg|system|call|location|card",
        "media": {"kind": "...", "md5": "...", "svr_id": "...", "duration_ms": 0}
      }
    ]
  }
}
```

## HTML 相对路径（易踩坑）

`gen_html.py` 用全局 `REL_CSS` / `REL_MEDIA` 计算层级：

- 合并时间线 `html/merged/<月>.html`：`REL_CSS="../style.css"`，`REL_MEDIA="../../media/"`
- 单聊 `html/<账号>/<会话>/<月>.html`：`REL_CSS="../../style.css"`，`REL_MEDIA="../../../media/"`

## 渲染要点

- 语音：`<audio controls preload="none" src="...">`，mp3 需转码完成
- 自定义表情：有解密图片则 `<img class="chat-emoji">`，否则显示 `[表情·描述]` 或 `[自定义表情]` 占位
- 图片：`<img loading="lazy">`，点击可放大

## 账号配置（导出朋友资料时改这里）

各脚本顶部有 `ACCOUNTS` 配置块和 `SENDER_MAP`/`MY_WXIDS`/`HER_WXIDS` 身份映射，导出他人资料时替换为对方信息：

| 脚本 | 需改的配置 | 说明 |
|---|---|---|
| archive_export_all.py | `ACCOUNTS`（账号→目录/显示名）、`CONVERSATIONS`（会话 wxid）、`MY_WXIDS` | 谁是我、谁是对方 |
| archive_preprocess.py | `MY_WXIDS`、`HER_WXIDS` | 身份映射 |
| archive_gen_html.py | `SENDER_MAP`、`ACCOUNT_LABELS`、`CONV_LABELS` | 显示名 |
| archive_process_media.py | `ACCOUNTS`（uin/xor_key）、`DATA_ROOT` | 图片解密密钥 |
| archive_process_voice.py | `ACCOUNTS`（dir）、`DECRYPTED_ROOT` | 语音库路径 |
| archive_process_emoji.py | `ACCOUNTS`（dir/wxid/uin）、`DATA_ROOT` | 表情解密密钥 |

新账号的 `uin` 和 `xor_key` 需重新破解（图片 AES key = `md5(UIN+wxid)[:16]`，XOR key 从缩略图尾部反推）。`wxid` 从账号目录名或 `contact.db` 获取。

## 现场环境（历史，仅供参考）

- 微信 4.2.x，数据目录在非系统盘 `E:\Documents\WechatFiles\xwechat_files`
- 两个账号（wxid 后缀 `_0d04`、`_0516`），各 18 个库
- 消息量：37.9 万条 → 去重后 29.4 万条合并时间线，71 个月
- 媒体量：图片 1.7 万张、语音 4808 条、自定义表情 1443 个、文件/视频 2578 个（约 34GB）
- 环境：解密/图片/表情用 `wechat-decrypt/.venv`（含 pycryptodome），语音用 `voice_env`（Python 3.8 + pilk），ffmpeg 在 `C:\Program Files\ffmpeg\bin`
