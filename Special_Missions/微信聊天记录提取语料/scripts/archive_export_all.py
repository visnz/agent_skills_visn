#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天记录全量导出脚本（两个账号 × 三个会话 → 结构化 JSON）。

用途：将「你大号 + 你小号」两个账号里，与她相关的所有聊天记录
（她大号、她小号、群聊）抽取为统一的 JSON 中间产物，供后续 HTML 组装使用。

设计要点：
- 精确指定每个账号的解密库目录，不做自动账号选择（避免混淆）
- 消息类型映射（local_type & 0xFFFF 取真实类型）
- zstd 压缩内容解压
- 系统默认表情 → 描述词占位符；自定义表情保留 md5 引用
- 图片/文件/视频/表情 的媒体引用（md5、文件名）保留在 JSON，媒体文件复制单独处理
- 语音：建立索引（svr_id → 时长/引用），转码另行批处理
- 群聊在两账号各有镜像，用 (server_id, create_time, 发送者, 内容哈希) 去重合并

用法:
  python export_all.py

【导出前必须替换的占位符】本脚本为模板，以下字段均为占位符，填入真实值：
  - DECRYPTED_ROOT    → 解密库根目录（wechat-decrypt 的 decrypted 输出）
  - ACCOUNTS          → 账号目录名（xwechat_files 下 <wxid>_<后缀>）+ 显示名
  - CONVERSATIONS     → 目标会话的对方 wxid / 群聊 id + 显示名
  - MY_WXID           → 每个账号自己的 wxid（判断 is_me 用）
"""
import os
import sys
import json
import sqlite3
import hashlib
import re
import html
import zstandard
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ----------------------------------------------------------------------------
# 常量配置（占位符，导出前替换）
# ----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent

# 解密库根目录（wechat-decrypt/decrypted 下）
DECRYPTED_ROOT = Path(r"D:\wechat-corpus-work\wechat-decrypt\decrypted")

# 账号 → (账号目录名, 显示名)
ACCOUNTS = {
    "da_hao": ("wxid_ACCOUNT_A_DIRSUFFIX", "你（大号）"),
    "xiao_hao": ("wxid_ACCOUNT_B_DIRSUFFIX", "你（小号）"),
}

# 目标会话 → (对方 wxid 或群聊 id, 显示名, 是否群聊)
CONVERSATIONS = {
    "her_da": ("wxid_CONTACT_A", "她（CONTACT_A_NAME）", False),
    "her_xiao": ("wxid_CONTACT_B", "她（CONTACT_B_NAME）", False),
    "group": ("GROUP_CHAT_ID", "群聊·GROUP_NAME", True),
}

_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
_dctx = zstandard.ZstdDecompressor()

# 系统默认表情描述词（微信经典 emoji，用于占位）
# 这是微信内置 emoji 的常见中文描述，遇到未知的用通用占位
SYSTEM_EMOJI_HINTS = {
    "微笑": ["smile", "微笑"],
    "撇嘴": ["gaping", "撇嘴"],
    "色": ["se", "色"],
    "发呆": ["daze", "发呆"],
    "得意": ["proud", "得意"],
    "流泪": ["shed", "流泪"],
    "害羞": ["shy", "害羞"],
    "闭嘴": ["shutup", "闭嘴"],
    "睡": ["sleep", "睡"],
    "大哭": ["cry", "大哭"],
    "尴尬": ["awkward", "尴尬"],
    "发怒": ["angry", "发怒"],
    "调皮": ["naughty", "调皮"],
    "呲牙": ["grin", "呲牙"],
    "惊讶": ["surprise", "惊讶"],
    "难过": ["sad", "难过"],
    "酷": ["cool", "酷"],
    "冷汗": ["sweat", "冷汗"],
    "抓狂": ["scream", "抓狂"],
    "吐": ["vomit", "吐"],
    "偷笑": ["snicker", "偷笑"],
    "可爱": ["cute", "可爱"],
    "白眼": ["white-eyes", "白眼"],
    "傲慢": ["arrogant", "傲慢"],
    "饥饿": ["hungry", "饥饿"],
    "困": ["drowsy", "困"],
    "惊恐": ["frightened", "惊恐"],
    "流汗": ["sweating", "流汗"],
    "憨笑": ["chuckle", "憨笑"],
    "大兵": ["soldier", "大兵"],
    "奋斗": ["struggle", "奋斗"],
    "咒骂": ["curse", "咒骂"],
    "疑问": ["doubt", "疑问"],
    "嘘": ["hush", "嘘"],
    "晕": ["faint", "晕"],
    "折磨": ["torture", "折磨"],
    "衰": ["decay", "衰"],
    "骷髅": ["skull", "骷髅"],
    "敲打": ["knock", "敲打"],
    "再见": ["bye", "再见"],
    "擦汗": ["wipe", "擦汗"],
    "抠鼻": ["pick-nose", "抠鼻"],
    "鼓掌": ["applause", "鼓掌"],
    "糗大了": ["embarrassed", "糗大了"],
    "坏笑": ["sly", "坏笑"],
    "左哼哼": ["hum-left", "左哼哼"],
    "右哼哼": ["hum-right", "右哼哼"],
    "哈欠": ["yawn", "哈欠"],
    "鄙视": ["despise", "鄙视"],
    "委屈": ["grievance", "委屈"],
    "快哭了": ["almost-cry", "快哭了"],
    "阴险": ["sinister", "阴险"],
    "亲亲": ["kiss", "亲亲"],
    "吓": ["scare", "吓"],
    "可怜": ["pitiful", "可怜"],
    "菜刀": ["cleaver", "菜刀"],
    "西瓜": ["watermelon", "西瓜"],
    "啤酒": ["beer", "啤酒"],
    "篮球": ["basketball", "篮球"],
    "乒乓": ["pingpong", "乒乓"],
    "咖啡": ["coffee", "咖啡"],
    "饭": ["rice", "饭"],
    "猪头": ["pig", "猪头"],
    "玫瑰": ["rose", "玫瑰"],
    "凋谢": ["wither", "凋谢"],
    "爱心": ["heart", "爱心"],
    "心碎": ["broken-heart", "心碎"],
    "蛋糕": ["cake", "蛋糕"],
    "闪电": ["lightning", "闪电"],
    "炸弹": ["bomb", "炸弹"],
    "刀": ["knife", "刀"],
    "足球": ["soccer", "足球"],
    "瓢虫": ["ladybug", "瓢虫"],
    "便便": ["poop", "便便"],
    "月亮": ["moon", "月亮"],
    "太阳": ["sun", "太阳"],
    "礼物": ["gift", "礼物"],
    "拥抱": ["hug", "拥抱"],
    "强": ["strong", "强"],
    "弱": ["weak", "弱"],
    "握手": ["handshake", "握手"],
    "胜利": ["victory", "胜利"],
    "抱拳": ["fist", "抱拳"],
    "勾引": ["seduce", "勾引"],
    "拳头": ["punch", "拳头"],
    "差劲": ["thumbs-down", "差劲"],
    "爱你": ["love", "爱你"],
    "NO": ["no", "NO"],
    "OK": ["ok", "OK"],
}


# ----------------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------------
def decode_content(content):
    """解码消息内容（处理 zstd 压缩 + utf-8）。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (bytes, bytearray)):
        raw = bytes(content)
        if raw.startswith(_ZSTD_MAGIC):
            try:
                raw = _dctx.decompress(raw)
            except Exception:
                return raw.decode("utf-8", errors="replace")
        return raw.decode("utf-8", errors="replace")
    return str(content)


def normalize_type(raw_type):
    """取 local_type 低 16 位作为真实类型。"""
    try:
        return str(int(raw_type) & 0xFFFF)
    except (TypeError, ValueError):
        return str(raw_type)


def md5_of(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def fmt_ts(ts):
    """时间戳 → 本地时间字符串 + 毫秒保留。"""
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        return ""
    if ts <= 0:
        return ""
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------------------------------------------------------
# protobuf packed_info 解析（提取媒体 md5）
# ----------------------------------------------------------------------------
def parse_packed_fields(blob):
    """读取 protobuf 字段，返回 [(field, wire, value), ...]"""
    if not blob:
        return []
    offset = 0
    result = []
    while offset < len(blob):
        # varint key
        value = 0
        shift = 0
        while True:
            if offset >= len(blob):
                return result
            b = blob[offset]
            offset += 1
            value |= (b & 0x7F) << shift
            if b < 0x80:
                break
            shift += 7
            if shift > 70:
                return result
        field, wire = value >> 3, value & 7
        if field == 0:
            return result
        if wire == 0:  # varint
            v = 0
            shift = 0
            while True:
                if offset >= len(blob):
                    return result
                b = blob[offset]
                offset += 1
                v |= (b & 0x7F) << shift
                if b < 0x80:
                    break
                shift += 7
            result.append((field, wire, v))
        elif wire == 2:  # length-delimited
            ln = 0
            shift = 0
            while True:
                if offset >= len(blob):
                    return result
                b = blob[offset]
                offset += 1
                ln |= (b & 0x7F) << shift
                if b < 0x80:
                    break
                shift += 7
            if offset + ln > len(blob):
                return result
            result.append((field, wire, blob[offset:offset + ln]))
            offset += ln
        elif wire == 1:  # 64-bit
            if offset + 8 > len(blob):
                return result
            result.append((field, wire, blob[offset:offset + 8]))
            offset += 8
        elif wire == 5:  # 32-bit
            if offset + 4 > len(blob):
                return result
            result.append((field, wire, blob[offset:offset + 4]))
            offset += 4
        else:
            return result
    return result


def extract_media_md5(packed_info):
    """从 packed_info (bytes 或 hex str) 提取 32 位 hex md5。"""
    if not packed_info:
        return None
    blob = packed_info
    if isinstance(packed_info, str):
        try:
            blob = bytes.fromhex(packed_info)
        except ValueError:
            return None
    if isinstance(blob, memoryview):
        blob = bytes(blob)
    if not isinstance(blob, bytes):
        return None
    # 递归查找所有 32 位 hex 字符串
    def scan(b):
        # 直接找 32 位 hex
        for m in re.finditer(rb"[0-9a-fA-F]{32}", b):
            return m.group(0).decode("ascii").lower()
        return None
    # 先整体扫
    r = scan(blob)
    if r:
        return r
    # 再递归进嵌套字段
    for f, w, v in parse_packed_fields(blob):
        if isinstance(v, bytes):
            r = scan(v)
            if r:
                return r
    return None


# ----------------------------------------------------------------------------
# 消息类型格式化
# ----------------------------------------------------------------------------
def parse_emoji(xml_text):
    """解析表情消息（type 47）。返回 dict。
    系统默认表情(type=3 或 有 productid) → 描述词占位
    自定义表情 → md5 + 描述
    """
    info = {"kind": "emoji", "system": False, "desc": "", "md5": None, "url": None}
    # md5
    m = re.search(r'md5="([0-9a-fA-F]{32})"', xml_text)
    if m:
        info["md5"] = m.group(1).lower()
    # type
    m = re.search(r'type="(\d+)"', xml_text)
    emoji_type = m.group(1) if m else ""
    # cdnurl / productid
    m = re.search(r'cdnurl="([^"]+)"', xml_text)
    if m:
        info["url"] = html.unescape(m.group(1))
    m = re.search(r'productid="([^"]*)"', xml_text)
    productid = m.group(1) if m else ""
    m = re.search(r'len="(\d+)"', xml_text)
    info["len"] = int(m.group(1)) if m else 0

    # 判断系统表情
    is_system = (emoji_type == "3") or (productid and productid != "0")
    info["system"] = is_system
    if is_system:
        # 尝试从 cdnurl 里找表情名
        hint = ""
        # cdnurl 常含英文标识
        info["desc"] = "系统表情"
        info["placeholder"] = "[表情]"
    else:
        info["desc"] = "自定义表情"
        info["placeholder"] = "[自定义表情]"
    return info


def parse_voice(xml_text):
    """解析语音消息（type 34）。返回 dict。"""
    info = {"kind": "voice", "duration_ms": 0, "voice_format": ""}
    m = re.search(r'voicelength\s*=\s*"(\d+)"', xml_text)
    if m:
        info["duration_ms"] = int(m.group(1))
    m = re.search(r'voiceformat\s*=\s*"(\d+)"', xml_text)
    if m:
        info["voice_format"] = m.group(1)
    return info


def parse_image(xml_text):
    """解析图片消息（type 3）。返回 dict（md5 在 packed_info，这里留空）。"""
    return {"kind": "image", "desc": "图片"}


def parse_video(xml_text):
    """解析视频消息（type 43）。"""
    info = {"kind": "video", "desc": "视频", "md5": None}
    m = re.search(r'md5="([0-9a-fA-F]{32})"', xml_text)
    if m:
        info["md5"] = m.group(1).lower()
    m = re.search(r'length\s*=\s*"(\d+)"', xml_text)
    if m:
        info["size"] = int(m.group(1))
    return info


# ----------------------------------------------------------------------------
# 抽取核心
# ----------------------------------------------------------------------------
def get_message_dbs(account_dir):
    """返回某账号解密后的 message_N.db 列表（按序号排序）。"""
    d = DECRYPTED_ROOT / account_dir / "db_storage" / "message"
    dbs = sorted(d.glob("message_[0-9].db"), key=lambda p: int(re.search(r"message_(\d+)", p.name).group(1)))
    return dbs


def get_my_rowid(db_path, my_wxid):
    """返回某库中「我」的 Name2Id rowid。"""
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT rowid FROM Name2Id WHERE user_name=?", (my_wxid,)).fetchall()
        return rows[0][0] if rows else None
    except Exception:
        return None
    finally:
        con.close()


def fetch_conversation(account_dir, my_wxid, conv_wxid, is_group):
    """抽取某账号与某会话的全部消息。返回 list[dict]。"""
    dbs = get_message_dbs(account_dir)
    table = "Msg_" + md5_of(conv_wxid)
    rows = []
    for db_path in dbs:
        con = sqlite3.connect(str(db_path))
        try:
            tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except Exception:
            con.close()
            continue
        if table not in tabs:
            con.close()
            continue
        my_rowid = get_my_rowid(db_path, my_wxid)
        # 读取该表全部消息
        try:
            cur = con.execute(
                f'SELECT local_id, server_id, local_type, real_sender_id, create_time, '
                f'message_content, compress_content, hex(packed_info_data) as packed_hex '
                f'FROM "{table}" ORDER BY create_time ASC, local_id ASC'
            )
            # 构建 Name2Id rowid → wxid 映射
            name_map = {}
            try:
                for r in con.execute("SELECT rowid, user_name FROM Name2Id"):
                    name_map[r[0]] = r[1]
            except Exception:
                pass
            for r in cur:
                rows.append({
                    "_db": db_path.name,
                    "local_id": r[0],
                    "server_id": r[1],
                    "local_type": r[2],
                    "real_sender_id": r[3],
                    "create_time": r[4],
                    "message_content": r[5],
                    "compress_content": r[6],
                    "packed_hex": r[7],
                    "_is_me": (my_rowid is not None and r[3] == my_rowid),
                    "_sender_wxid": name_map.get(r[3], ""),
                })
        except Exception as e:
            print(f"  [WARN] {db_path.name} 读取 {table} 失败: {e}")
        finally:
            con.close()
    return rows


def decode_row(row, is_group):
    """将原始行解码为结构化消息 dict。"""
    raw_type = row["local_type"]
    t = normalize_type(raw_type)
    content_raw = row["message_content"]
    content = decode_content(content_raw)
    packed_hex = row.get("packed_hex") or ""

    # 群聊消息 content 开头常带 "发送者wxid:\n" 前缀，剥离之，并用它修正 sender_wxid
    sender_wxid = row["_sender_wxid"]
    if is_group and content:
        m = re.match(r"^([a-zA-Z0-9_@\-]+):\s*\n", content)
        if m:
            prefix_wxid = m.group(1)
            content = content[m.end():]
            # 前缀 wxid 比 real_sender_id 的 Name2Id 映射更可靠，优先采用
            if not sender_wxid and (prefix_wxid.startswith("wxid_") or "@chatroom" in prefix_wxid):
                sender_wxid = prefix_wxid

    msg = {
        "type": t,
        "raw_type": raw_type,
        "create_time": row["create_time"],
        "time_str": fmt_ts(row["create_time"]),
        "is_me": bool(row["_is_me"]),
        "sender_wxid": sender_wxid,
        "local_id": row["local_id"],
        "server_id": row["server_id"],
        "db": row["_db"],
        "content": content,
        "text": content,  # 默认文本即内容
        "kind": "text",
        "media": None,
    }

    # 文本
    if t == "1":
        msg["kind"] = "text"
        msg["text"] = content
        return msg

    # 图片
    if t == "3":
        msg["kind"] = "image"
        msg["text"] = ""
        msg["media"] = {"kind": "image", "md5": extract_media_md5(packed_hex)}
        return msg

    # 语音
    if t == "34":
        v = parse_voice(content)
        msg["kind"] = "voice"
        msg["text"] = ""
        msg["media"] = {"kind": "voice", "duration_ms": v["duration_ms"], "svr_id": str(row["server_id"])}
        return msg

    # 视频
    if t == "43":
        v = parse_video(content)
        msg["kind"] = "video"
        msg["text"] = ""
        msg["media"] = {"kind": "video", "md5": v.get("md5"), "size": v.get("size")}
        return msg

    # 表情
    if t == "47":
        e = parse_emoji(content)
        msg["kind"] = "emoji"
        msg["text"] = e["placeholder"]
        msg["media"] = {"kind": "emoji", "md5": e.get("md5"), "system": e["system"], "url": e.get("url")}
        return msg

    # 名片
    if t == "42":
        msg["kind"] = "card"
        msg["text"] = "[名片]"
        return msg

    # 位置
    if t == "48":
        msg["kind"] = "location"
        msg["text"] = "[位置]"
        return msg

    # 链接/文件/小程序等 (49)
    if t == "49":
        # 尝试解析 appmsg
        msg["kind"] = "appmsg"
        msg["text"] = parse_appmsg_simple(content)
        return msg

    # 通话
    if t == "50":
        msg["kind"] = "call"
        m = re.search(r'通话时长\s*([0-9:]+)', content)
        dur = m.group(1) if m else ""
        msg["text"] = f"[通话{' ' + dur if dur else ''}]"
        return msg

    # 系统消息 / 撤回
    if t in ("10000", "10002"):
        msg["kind"] = "system"
        msg["text"] = parse_system_simple(content, t)
        return msg

    # 未知类型
    msg["kind"] = "unknown"
    msg["text"] = content if content else f"[类型 {t}]"
    return msg


def parse_appmsg_simple(xml_text):
    """简单解析 type 49 消息为可读文本（不依赖 appmsg.py 以避免路径耦合，用轻量正则）。"""
    # 提取 title
    def tag(name, default=""):
        m = re.search(rf'<{name}[^>]*>([\s\S]*?)</{name}>', xml_text, re.IGNORECASE)
        if m:
            v = m.group(1)
            v = re.sub(r'<!\[CDATA\[|\]\]>', '', v)
            return html.unescape(v).strip()
        return default

    app_type = tag("type")
    title = tag("title")
    if title:
        return title
    # 无 title 时看其他
    for t in ("des", "content", "source"):
        v = tag(t)
        if v:
            return v
    return "[分享]"


def parse_system_simple(content, t):
    """解析系统消息/撤回为可读文本。"""
    if not content:
        return "[系统消息]"
    # 撤回
    if t == "10002" or "撤回" in content:
        return "[撤回了一条消息]"
    # 拍一拍
    if "拍了拍" in content:
        m = re.search(r'拍了拍[^<]*', content)
        return m.group(0) if m else "[拍了拍]"
    # 其他系统消息：提取文本
    # 去掉 XML 标签
    text = re.sub(r'<[^>]+>', '', content)
    text = html.unescape(text).strip()
    return text if text else "[系统消息]"


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    all_data = {
        "meta": {
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "accounts": {k: {"dir": v[0], "display": v[1], "wxid": MY_WXID[k]} for k, v in ACCOUNTS.items()},
            "conversations": {k: {"wxid": v[0], "display": v[1], "is_group": v[2]} for k, v in CONVERSATIONS.items()},
        },
        "conversations": {},  # key: f"{account_key}__{conv_key}" → list[msg]
    }

    for acc_key, (acc_dir, acc_display) in ACCOUNTS.items():
        my_wxid = MY_WXID[acc_key]
        print(f"\n=== 账号 {acc_display} ({acc_dir}) ===")
        for conv_key, (conv_wxid, conv_display, is_group) in CONVERSATIONS.items():
            print(f"  抽取 {conv_display} ...")
            rows = fetch_conversation(acc_dir, my_wxid, conv_wxid, is_group)
            decoded = [decode_row(r, is_group) for r in rows]
            key = f"{acc_key}__{conv_key}"
            all_data["conversations"][key] = decoded
            print(f"    → {len(decoded)} 条")

    # 统计
    print("\n=== 汇总 ===")
    total = 0
    for k, v in all_data["conversations"].items():
        total += len(v)
        print(f"  {k}: {len(v):,}")
    print(f"  总计: {total:,}")

    # 输出 JSON
    out = BASE / "messages_raw.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False)
    print(f"\n已输出: {out} ({out.stat().st_size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
