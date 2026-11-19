# 微信 3.x 旧库解密与密钥机制——技术复盘

记录一次真实的「微信 3.x 旧库解密 → 补全 4.x 迁移前历史」实操中验证有效的做法、关键结论和踩过的坑。所有路径、版本号仅为当时现场，执行前必须重新确认。

## 适用场景

微信升级到 4.x 后，迁移可能**只搬了部分历史**（例如某账号只搬了最近 18 个月），更早的记录留在旧版 3.x 的数据库里。要补全这些早期记录，就得解 3.x 旧库。3.x 和 4.x 是**两套完全不同的加密方案**，密钥互不通用，本文件只讲 3.x。

## 现场环境

- 微信当前版本：4.2.x（数据走 `xwechat_files`）；另装了旧版 3.9.12.x 用来抓 3.x 密钥
- 旧数据目录：非默认位置（系统重装后，历史数据被挪到 `E:\Documents\WeChat FilesOLD\` 这类自定义目录）
- 工具：PyWxDump（`wxdump.exe`，自带 3.9.12.x 全系列密钥偏移表，最高 3.9.12.55）
- Python：3.13（标准库 `hashlib`/`hmac` 即可，无需额外依赖做验证）

## 3.x vs 4.x 加密参数对比

| 项目 | 3.x | 4.x |
|------|-----|-----|
| 页大小 | 4096 | 4096 |
| KDF | PBKDF2-HMAC-**SHA1** | PBKDF2-HMAC-**SHA512** |
| 迭代次数 | **64000** | **256000** |
| HMAC | SHA1（20 字节） | SHA512（64 字节） |
| 加密 | AES-256-CBC | AES-256-CBC |
| 消息库路径 | `WeChat Files\<wxid>\Msg\Multi\MSG*.db` | `xwechat_files\<wxid>_<suffix>\db_storage\message\message_*.db` |
| 联系人/会话库 | `Msg\MicroMsg.db` | `db_storage\contact\contact.db` |

网上流传的「迭代 65535 次」是以讹传讹，正确是 **64000**。

## 数据库结构（3.x）

```
WeChat Files\<wxid>\
├── Msg\
│   ├── MicroMsg.db        # 联系人 Contact 表 + 会话 Session 表
│   └── Multi\
│       ├── MSG0.db ~ MSG4.db   # 消息分片，每片固定大小，按时间切
│       └── MediaMSG*.db        # 媒体索引
└── config\AccInfo.dat      # 账号配置（protobuf，含 UIN，但对解密无用）
```

关键表：

- `Contact`：username(wxid) / remark(备注) / nick_name(昵称) / alias(微信号)——三者可能完全不同，**先查这里核对**，别在会话列表按字面搜。
- `Session`：strUsrName、最后消息时间/内容摘要。
- `MSG`：`StrTalker`(对方wxid)、`CreateTime`(秒级时间戳)、`IsSender`(1=我/0=对方)、`Type`(1=文本、3=图片、47=表情)、`StrContent`(正文)、`BytesExtra`。

## 密钥机制（关键认知，与 4.x 有本质差异）

1. **密钥是「账号级」的**，不是设备级。两个账号在同一台机器、同一时期，各自一把独立密钥；拿到 A 号的 key 解不了 B 号的库（已实测交叉验证）。
2. **密钥来源 = 进程内存**（登录时生成/持有），**不是** `MD5(IMEI+UIN)`——那是安卓老版 EnMicroMsg.db 的机制，PC 3.x 不适用，无法离线推导。
3. **硬件指纹 = CPU 序列号 + 硬盘序列号 + 物理网卡 MAC，不含显卡（GPU）**。换显卡既不改密钥、也不触发风控（社区逆向结论）。
4. **重装系统后密钥可能不变**：只要核心硬件（CPU/硬盘/网卡）没换，同一账号的 3.x 密钥跨系统重装可保持稳定（实测：某账号 2023 年旧库与 2026 年新抓 key 完全一致）。
5. **密钥会因「设备异常 / DeviceID 变化 / 迁移触发」被重置**：一旦重置，旧密钥不可逆丢失，旧库永久解不开（详见下文「密钥丢失」）。

## 抓密钥方法（3.x 比 4.x 简单得多）

3.x 用 PyWxDump 直接读内存拿 key，无需 4.x 那套 Frida 硬逆向：

```text
wxdump.exe info
```

输出 `wxid` / `key`（64 位 hex）/ `wx_dir`。

要点：

- **必须登录对应版本的微信**：抓 3.x key 要装并登录 3.x（3.9.12.x），抓 4.x key 要装 4.x。两者是不同程序（`WeChat.exe` vs `Weixin.exe`），可并存。
- **刚登录可能抓不到**（`wxid: None`，内存未加载完），等 5~10 秒重试即可。
- 版本号对不上偏移表（如装出 3.9.12.57，表里最高 3.9.12.55）也没关系，PyWxDump 有内存搜索兜底。

## 验证密钥的正确做法（重要踩坑）

**不要用「AES 解密第一页 → 看 SQLite 头」来验证 3.x key**——3.x 的页结构会让这种验证误判为「不匹配」。正确做法是 **HMAC 页校验**（含 `salt XOR 58` 的二次 PBKDF2）：

```python
import hashlib, hmac

def verify_3x_key(db_path, key_hex):
    KEY = bytes.fromhex(key_hex)
    with open(db_path, 'rb') as f:
        blist = f.read(5000)
    salt = blist[:16]
    pk = hashlib.pbkdf2_hmac('sha1', KEY, salt, 64000, 32)
    first = blist[16:4096]
    mac_salt = bytes([(salt[i] ^ 58) for i in range(16)])  # 关键：salt 逐字节 XOR 0x3A
    pk2 = hashlib.pbkdf2_hmac('sha1', pk, mac_salt, 2, 32)
    h = hmac.new(pk2, first[:-32], hashlib.sha1)
    h.update(b'\x01\x00\x00\x00')
    return h.digest() == first[-32:-12]   # 页尾 HMAC 比对
```

该函数已固化为 `scripts/verify_key_3x.py`，可传入 key + 任意 db 批量验证。

## 解密命令

```text
wxdump.exe decrypt -k <key> -i <原库.db> -o <输出目录>
```

- `MicroMsg.db` 秒级解密（先解它核对联系人/会话）；`MSG0~4.db` 较大（每个 100~280MB），后台批量跑。
- 解密产物是标准 SQLite，直接 `sqlite3` 读。

## 3.x 微信安装与防强制升级

- 官方 CDN 直链（x64，3.9.12 系列，腾讯服务器下载快）：`https://dldir1v6.qq.com/weixin/Windows/WeChatSetup.exe`。注意官方 x64 目前仍是 3.9.12.x（4.x 是另一条 `Weixin` 下载链路），装前用文件属性/数字签名确认版本号。
- 装出的小版本号可能是 `.57`（非偏移表里的 `.55`），不影响抓 key。
- **防强制升级**：安装目录（如 `C:\Program Files\Tencent\WeChat\[3.9.12.57]\`）里的 `WeChatUpdate.exe` / `WeChatUpdate.bin` 改名 `.bak` 禁用。注意该目录在 `Program Files` 下，改名需要管理员权限；改不动就先登录试（通常只是弹提示框，不会自动毁掉旧版）。

## 撞库 / 暴力破解可行性结论（无需再试）

- **暴力穷举不可行**：256 位（32 字节）密钥，2²⁵⁶ 空间，物理上不可能。
- **字典撞库不适用**：密钥不是用户密码，是程序生成的随机/派生值，无「常见密钥」字典。
- **离线推导不适用**：PC 3.x 非 `MD5(IMEI+UIN)`，密钥运行时生成，缺失的随机种子无法回溯。
- 「离线验证」确实可行（SQLCipher 页校验纯本地、不联网），但卡点不在联网而在密钥空间本身。
- 已知的 KDF 参数（4000/64000/256000 迭代）试遍仍不匹配时，等于「参数级撞库」已穷尽，剩下只有 256 位密钥本身。

## 密钥丢失场景（判定「能否解密」的关键）

遇到「当前 key 能解新库、解不开旧库」时，按此判断：

1. **先排除验证方法错误**：用上面的 HMAC 验证，别用 AES 解密验证（两者结论可能相反）。
2. **交叉验证**：拿 A 号 key 试 B 号旧库、B 号 key 试 A 号旧库，确认是否账号级差异。
3. **时间线定位**：旧库最后写入时间之后，账号若经历过「3.x→4.x 迁移」「设备异常（ErrCode 1207）」「异地登录」，旧密钥可能已被重置，旧库不可恢复。
4. **硬件判断**：换显卡/内存不影响密钥；换 CPU/硬盘/网卡或换电脑，密钥必然变化。唯一可能找回旧密钥的是**旧系统的完整镜像或当时的注册表备份**（含旧 DeviceID）。

## 数据可能不在默认位置（定位经验）

- 微信数据路径不一定在 `C:\Users\<name>\Documents\WeChat Files`，尤其系统重装后。真实路径看：
  - 4.x：`%APPDATA%\Tencent\xwechat\config\*.ini` 里记录的数据目录；
  - 3.x：注册表 `HKCU\Software\Tencent\WeChat\FileSavePath`。
- 历史数据常被挪到 `WeChat FilesOLD`、`WeChat Files.old`、其他盘根目录等自定义位置，别只看默认目录。
- 旧库目录里可能散落 `MSG1.db_SQLITE_NOTADB<时间戳>`、`*.FatalErr`、`*.IOErr` 后缀的历史文件——这些是当年数据库损坏/重建留下的，同目录下正常命名的 `.db` 才是当前可用的库。
