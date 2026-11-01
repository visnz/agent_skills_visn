#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息预处理：把 481MB 的 messages_raw.json 转成轻量的按月分组结构。

输出：
  - 合并时间线（4单聊+群聊去重，按月分组）
  - 每个账号每个会话的单聊（按月分组）
  - 表情描述替换、媒体引用路径

产物：
  merged_by_month.json     # 合并时间线
  chat_by_month.json       # 单聊（key: account__conv -> month -> messages）
"""
import os
import sys
import json
import re
import hashlib
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

# 发送者 wxid → 身份（"me" 我 / "her" 她）
MY_WXIDS = {"wxid_ACCOUNT_A", "wxid_ACCOUNT_B"}
HER_WXIDS = {"wxid_CONTACT_A", "wxid_CONTACT_B"}

def who_is(sender_wxid):
    """根据发送者 wxid 判断身份，返回 "me" / "her" / "unknown"。"""
    if not sender_wxid:
        return "unknown"
    if sender_wxid in MY_WXIDS:
        return "me"
    if sender_wxid in HER_WXIDS:
        return "her"
    return "unknown"

# 加载表情映射
def load_emoji_maps():
    maps = {}
    for acc in ("da_hao", "xiao_hao"):
        p = os.path.join(BASE, f"emoji_map_{acc}.json")
        if os.path.exists(p):
            maps[acc] = json.load(open(p, encoding="utf-8"))
        else:
            maps[acc] = {"system_map": {}, "custom_md5": []}
    return maps

def load_image_results():
    results = {}
    for acc in ("da_hao", "xiao_hao"):
        p = os.path.join(BASE, f"image_results_{acc}.json")
        if os.path.exists(p):
            results[acc] = json.load(open(p, encoding="utf-8"))
        else:
            results[acc] = {}
    return results


def load_emoji_results():
    """加载自定义表情解密结果：{account: {md5: {status, file}}}。"""
    p = os.path.join(BASE, "emoji_results.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {}


# 自定义表情解密结果的全局缓存（build_message_display 内使用）
EMOJI_RESULTS = {}


def month_of(ts):
    if not ts:
        return "unknown"
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        return "unknown"
    if ts <= 0:
        return "unknown"
    return datetime.fromtimestamp(ts).strftime("%Y-%m")


def format_time_str(ts):
    if not ts:
        return ""
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        return ""
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def resolve_emoji(msg, emoji_maps, account_key):
    """系统表情 → 描述词，自定义表情 → 占位。返回最终文本。"""
    if msg.get("kind") != "emoji":
        return msg.get("text", "")
    media = msg.get("media") or {}
    md5 = (media.get("md5") or "").lower()
    emap = emoji_maps.get(account_key, {})
    custom_md5 = set(emap.get("custom_md5", []))
    system_map = emap.get("system_map", {})
    if md5 and md5 in custom_md5:
        return "[自定义表情]"
    if md5 and md5 in system_map:
        return f"[表情·{system_map[md5]}]"
    # 有 productid 的判定为系统表情
    if media.get("system"):
        return "[表情]"
    return "[自定义表情]"


def build_message_display(msg, account_key, emoji_maps, image_results):
    """构造用于 HTML 展示的消息 dict（精简字段 + 媒体引用）。"""
    kind = msg.get("kind", "text")
    sender_wxid = msg.get("sender_wxid", "")
    # 用发送者 wxid 统一判断身份（群聊镜像里 is_me 是相对的，不能直接用）
    who = who_is(sender_wxid)
    # 单聊里若 sender_wxid 为空，回退用原始 is_me
    if who == "unknown" and msg.get("is_me"):
        who = "me"
    elif who == "unknown" and not msg.get("is_me") and kind not in ("system",):
        # 单聊非系统消息且 sender 未知：默认对方（她）
        who = "her"
    m = {
        "time": msg.get("time_str") or format_time_str(msg.get("create_time")),
        "ts": msg.get("create_time"),
        "kind": kind,
        "is_me": (who == "me"),
        "who": who,
        "sender": sender_wxid,
    }
    if kind == "text":
        m["text"] = msg.get("text", "")
    elif kind == "emoji":
        m["text"] = resolve_emoji(msg, emoji_maps, account_key)
        # 自定义表情若有解密图片则引用
        media = msg.get("media") or {}
        md5 = (media.get("md5") or "").lower()
        if md5:
            m["emoji_md5"] = md5
            # 查自定义表情解密结果（本账号优先，两号合并兜底）
            er = EMOJI_RESULTS.get(account_key, {})
            entry = er.get(md5)
            if not entry:
                for acc_key in EMOJI_RESULTS:
                    if md5 in EMOJI_RESULTS[acc_key]:
                        entry = EMOJI_RESULTS[acc_key][md5]
                        break
            if entry and entry.get("status") == "ok" and entry.get("file"):
                m["emoji_file"] = entry["file"]
    elif kind == "image":
        media = msg.get("media") or {}
        md5 = (media.get("md5") or "").lower()
        m["md5"] = md5
        # 查图片结果，确定文件路径
        ir = image_results.get(account_key, {})
        if md5 and md5 in ir and ir[md5].get("status") == "ok":
            m["image_file"] = ir[md5].get("file", "")
        else:
            m["image_file"] = ""
    elif kind == "voice":
        media = msg.get("media") or {}
        m["duration_ms"] = media.get("duration_ms", 0)
        m["svr_id"] = media.get("svr_id", "")
    elif kind == "video":
        media = msg.get("media") or {}
        m["md5"] = (media.get("md5") or "").lower()
    elif kind == "appmsg":
        m["text"] = msg.get("text", "")
    elif kind == "system":
        m["text"] = msg.get("text", "")
    elif kind == "call":
        m["text"] = msg.get("text", "")
    elif kind == "location":
        m["text"] = "[位置]"
    elif kind == "card":
        m["text"] = "[名片]"
    else:
        m["text"] = msg.get("text", "")
    return m


def main():
    print("加载 messages_raw.json ...")
    with open(os.path.join(BASE, "messages_raw.json"), encoding="utf-8") as f:
        data = json.load(f)

    emoji_maps = load_emoji_maps()
    image_results = load_image_results()
    global EMOJI_RESULTS
    EMOJI_RESULTS = load_emoji_results()

    conversations = data["conversations"]

    # 单聊按月分组
    chat_by_month = {}
    # 合并时间线按月分组
    merged_by_month = defaultdict(list)

    # 群聊去重 key 集合（跨两个账号的群聊镜像去重）
    group_seen = set()

    print("分组处理消息 ...")
    for conv_key, msgs in conversations.items():
        account_key, conv = conv_key.split("__", 1)
        is_group = (conv == "group")
        month_groups = defaultdict(list)
        for msg in msgs:
            month = month_of(msg.get("create_time"))
            disp = build_message_display(msg, account_key, emoji_maps, image_results)
            disp["account"] = account_key
            disp["conv"] = conv
            month_groups[month].append(disp)
        chat_by_month[conv_key] = {m: v for m, v in month_groups.items()}

        # 合并时间线
        for msg in msgs:
            month = month_of(msg.get("create_time"))
            disp = build_message_display(msg, account_key, emoji_maps, image_results)
            disp["account"] = account_key
            disp["conv"] = conv
            if is_group:
                # 群聊去重：用 server_id（服务端唯一，两账号视角一致）作 key
                sid = msg.get("server_id")
                if sid:
                    if sid in group_seen:
                        continue
                    group_seen.add(sid)
                else:
                    # server_id 缺失时回退用 (ts, sender, 文本)
                    key = (msg.get("create_time"), msg.get("sender_wxid", ""), disp.get("text", ""), disp.get("md5", ""))
                    if key in group_seen:
                        continue
                    group_seen.add(key)
            merged_by_month[month].append(disp)

    # 每个月的合并时间线按时间排序
    print("排序合并时间线 ...")
    for month in merged_by_month:
        merged_by_month[month].sort(key=lambda x: (x.get("ts") or 0, x.get("time", "")))

    # 单聊内部也排序（其实原始已按时间排好，但保险）
    for conv_key in chat_by_month:
        for month in chat_by_month[conv_key]:
            chat_by_month[conv_key][month].sort(key=lambda x: (x.get("ts") or 0, x.get("time", "")))

    # 统计
    total_merged = sum(len(v) for v in merged_by_month.values())
    print(f"合并时间线：{total_merged:,} 条，{len(merged_by_month)} 个月份")

    # 输出
    out1 = os.path.join(BASE, "merged_by_month.json")
    with open(out1, "w", encoding="utf-8") as f:
        json.dump(merged_by_month, f, ensure_ascii=False)
    print(f"已保存: {out1}")

    out2 = os.path.join(BASE, "chat_by_month.json")
    with open(out2, "w", encoding="utf-8") as f:
        json.dump(chat_by_month, f, ensure_ascii=False)
    print(f"已保存: {out2}")

    # 月份列表
    months = sorted(merged_by_month.keys())
    with open(os.path.join(BASE, "months.json"), "w", encoding="utf-8") as f:
        json.dump(months, f, ensure_ascii=False)
    print(f"月份范围: {months[0]} ~ {months[-1]}" if months else "无数据")


if __name__ == "__main__":
    main()
