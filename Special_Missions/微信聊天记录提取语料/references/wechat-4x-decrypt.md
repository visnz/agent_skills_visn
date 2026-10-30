# 微信 4.x 解密与导出——技术复盘

记录一次真实的"微信 4.x 聊天记录 → 语料"实操中验证有效的做法和踩过的坑。所有路径、版本号仅为当时现场，执行前必须重新确认。

## 现场环境

- 微信版本：4.2.x（4.x 新数据库格式）
- 数据目录：用户自定义在非系统盘（通过微信「设置 → 文件管理」查到的 `xwechat_files`）
- Python：系统装了 3.13（还有 3.8 备用）
- 工具：`freanocank/wechat-decrypt`（命令行，专做 4.x 解密）

## 数据库结构（4.x）

```
xwechat_files/
└── <账号 wxid>_<后缀>/
    └── db_storage/
        ├── message/          # 消息库分片 message_0.db ~ message_6.db（SQLCipher 加密，最大单个 700MB+）
        │   └── message_N.db  # 每个会话一个 Msg_<md5> 表，另有 Name2Id、SendInfo
        ├── contact/
        │   └── contact.db    # 联系人：username(wxid) / remark(备注) / nick_name(昵称) / alias(微信号)
        └── session/
            └── session.db    # SessionTable、Name2Id 等
```

微信 4.x 的存储模型：**每个会话一个 `Msg_<md5>` 表**，不是统一的 messages 表。消息按会话 hash 分散在多个分片里。

## 密钥派生逻辑

- `derive_key`：`PBKDF2-HMAC-SHA512(raw_key, salt[0:16], 256000, 32)`，每个库独立派生。
- SQLCipher 4 有 HMAC 页校验（`mac_key = PBKDF2-HMAC-SHA512(enc, salt_xor_0x3A, 2, 32)`），校验失败会导致工具把该库标记为 skip。

## 踩过的坑（按出现顺序）

### 1. 依赖装不上：Python 3.13 缺预编译 wheel

- 现象：`pip install pycryptodome zstandard` 报 `from versions: none`。
- 根因：不是包不存在，是 **Python 3.13 标准版缺 `cp313` wheel**，而 pip 因本地代理（`HTTP_PROXY`/`HTTPS_PROXY` 指向 `127.0.0.1` 本地代理）对 index 页解析异常。
- 解法：**手动下载 abi3 通用 wheel，用 `pip install --no-deps <本地.whl>` 强制安装**。
  - `pycryptodome` 用 `cp39-abi3-win_amd64`（abi3 向前兼容到 3.13）
  - `cryptography` 用 `cp311-abi3-win_amd64`
  - `frida` 用 `cp37-abi3-win_amd64`
  - `zstandard` 有 `cp313-cp313` 标准 wheel
  - `cffi` 有 `cp313-cp313` 标准 wheel
- 关键：**abi3 稳定 ABI 标签跨版本兼容**，`cp39-abi3` 能装到 cp313。pip 报 "none" 时，直接去 simple 页 `curl` 抓 wheel 链接手动下。

### 2. 抓密钥需要关微信重开

- 工具用 Frida hook `Weixin.dll`，在**微信重启瞬间**从内存抓 raw key。
- 流程：脚本自动 `taskkill` 微信 → 等待用户手动重开并扫码 → 抓密钥验证 → 存 `key_windows.txt`。
- 用户需要配合"关一次微信重开"，数据不会丢。杀毒软件（如火绒）可能误报内存注入，需先关闭。

### 3. 消息库"密钥不匹配"：WAL 快照读取失败

- 现象：`decrypt_all.py` 解出 16 个次要库，但 14 个 `message_*.db` 全 skip。
- 根因：微信正在运行，`message_*.db` 的 WAL 文件持续变化，工具的 `read_snapshot`（WAL 合并）抛异常 → 被标 skip。**不是密钥错**（用 raw key 直接解 `message_0.db` 第一页，SQLite 头校验通过）。
- 解法：写简化解密脚本，**绕过 WAL 合并，只用 main 文件解密**。历史消息基本都在 main 里，WAL 里只有最近未 checkpoint 的少量数据，对"提取历史语料"影响极小。

### 4. 导出需要 zstd

- `export_chat.py` 里缺 `zstandard` 会直接 `sys.exit(1)`（不是可选依赖）。
- 装 `zstandard`（有 cp313 wheel）后即可导出。

### 5. 用户口中的称呼 ≠ 微信昵称

- 用户口中对某人的称呼，可能和微信里的字段对不上：`nick_name`（昵称）、`remark`（备注）、`alias`（微信号）三者可能完全不同。
- 所以**先查 `contact.db` 核对**，别在会话列表里按字面搜。会话列表 `query.py list` 有时不显示备注，会搜不到。

## 验证解密的正确做法

```python
# 解 message_0.db 第一页，校验 SQLite 文件头
salt = data[:16]
enc = pbkdf2_hmac('sha512', raw_key, salt, 256000, 32)
pt0 = aes_cbc_decrypt(enc, data[rstart:rstart+16], data[16:rstart])
# pt0[0]==0x10 and pt0[1]==0x00 and pt0[4]==0x50 and pt0[5]==0x40 and pt0[7]==0x20
```

SQLite 文件头以 `10 00 ... 50 40 20` 开头，解密第一页后校验这几个字节即可确认密钥正确。

## 消息类型画像（供清洗脚本调参参考）

一次真实导出的单聊里，消息类型大致分布：

- 纯文字：占绝大多数（有效语料）
- Sticker（表情）：数量可观，需过滤
- Image / Video / Audio / File / 转账 / 小程序：少量，需过滤
- 系统消息（撤回、加好友）：极少，需过滤
- 引用消息：混有图片 XML 噪声（`<?xml`、`aeskey`、`cdnurl`），需剥离

清洗后纯文字大约是原始消息数的 70~85%（剥离引用/XML 噪声后）。
