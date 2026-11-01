#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成离线可读的聊天记录 HTML。

输出结构：
  html/
  ├── index.html              # 总入口
  ├── style.css               # 共享样式
  ├── merged/                 # 合并时间线（按月）
  │   └── 2020-12.html ...
  ├── da_hao/
  │   ├── her_da/2020-12.html
  │   ├── her_xiao/...
  │   └── group/...
  └── xiao_hao/...
"""
import os
import json
import html
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE, "html")

CONV_LABELS = {
    "her_da": "她（CONTACT_A_NAME）",
    "her_xiao": "她（CONTACT_B_NAME）",
    "group": "群聊·GROUP_NAME",
}
ACCOUNT_LABELS = {
    "da_hao": "你（大号）",
    "xiao_hao": "你（小号）",
}

# 发送者 wxid → 显示名
SENDER_MAP = {
    "wxid_ACCOUNT_A": "你（大号）",
    "wxid_ACCOUNT_B": "你（小号）",
    "wxid_CONTACT_A": "她（CONTACT_A_NAME）",
    "wxid_CONTACT_B": "她（CONTACT_B_NAME）",
}


def esc(text):
    return html.escape(str(text or ""), quote=True)


def render_message(msg, view_mode="single"):
    """渲染单条消息为 HTML。"""
    kind = msg.get("kind", "text")
    is_me = msg.get("is_me", False)
    time_str = msg.get("time", "")

    # 发送者标签 + 左右侧判断
    sender_tag = ""
    side = "me" if is_me else "other"

    if view_mode == "merged":
        conv = msg.get("conv", "")
        if conv == "group":
            # 群聊：显示具体发送者
            sender = SENDER_MAP.get(msg.get("sender", ""), "群成员")
            sender_tag = f'<div class="sender">{esc(sender)}</div>'
        else:
            # 单聊：显示 "你大号 ↔ 她CONTACT_A_NAME" 来源标注
            acc = msg.get("account", "")
            acc_label = ACCOUNT_LABELS.get(acc, acc)
            conv_label = CONV_LABELS.get(conv, conv)
            sender_tag = f'<div class="sender">{esc(acc_label)} ↔ {esc(conv_label)}</div>'
    else:
        # 单聊视图：群聊里显示具体发送者，单聊不显示（左右已区分）
        if msg.get("conv") == "group":
            sender = SENDER_MAP.get(msg.get("sender", ""), "群成员")
            sender_tag = f'<div class="sender">{esc(sender)}</div>'

    # 消息内容
    content_html = ""
    if kind == "text":
        content_html = esc(msg.get("text", ""))
    elif kind == "emoji":
        text = msg.get("text", "[表情]")
        emoji_file = msg.get("emoji_file", "")
        if emoji_file:
            rel = f"{REL_MEDIA}emoji/{emoji_file}"
            content_html = (
                f'<img src="{rel}" loading="lazy" class="chat-emoji" alt="表情">'
                f'<div class="emoji-caption">{esc(text)}</div>'
            )
        else:
            content_html = f'<span class="emoji-text">{esc(text)}</span>'
    elif kind == "image":
        md5 = msg.get("md5", "")
        image_file = msg.get("image_file", "")
        if image_file:
            # 图片文件在 media/images_<account>/ 下，html 在 html/ 下，用全局 REL_MEDIA 计算层级
            acc = msg.get("account", "")
            rel = f"{REL_MEDIA}images_{acc}/{image_file}"
            content_html = f'<a href="{rel}" target="_blank"><img src="{rel}" loading="lazy" class="chat-img" alt="图片"></a>'
        else:
            content_html = '<span class="placeholder">[图片]</span>'
    elif kind == "voice":
        dur = msg.get("duration_ms", 0)
        dur_str = f"{dur//1000}\""
        svr_id = msg.get("svr_id", "")
        if svr_id:
            rel = f"{REL_MEDIA}voice/{svr_id}.mp3"
            content_html = (
                f'<span class="voice">🔊 语音 {dur_str}</span>'
                f'<audio controls preload="none" src="{rel}"></audio>'
            )
        else:
            content_html = f'<span class="voice">🔊 语音 {dur_str}</span>'
    elif kind == "video":
        content_html = '<span class="placeholder">🎬 [视频]</span>'
    elif kind == "appmsg":
        content_html = f'<span class="appmsg">{esc(msg.get("text", "[分享]"))}</span>'
    elif kind == "system":
        content_html = f'<span class="system-msg">{esc(msg.get("text", "[系统消息]"))}</span>'
    elif kind == "call":
        content_html = f'<span class="call">{esc(msg.get("text", "[通话]"))}</span>'
    elif kind == "location":
        content_html = '<span class="placeholder">📍 [位置]</span>'
    elif kind == "card":
        content_html = '<span class="placeholder">👤 [名片]</span>'
    else:
        content_html = esc(msg.get("text", ""))

    # 系统消息不套气泡
    if kind == "system":
        return f'<div class="sys-row"><span class="sys-time">{esc(time_str)}</span><span class="sys-text">{content_html}</span></div>'

    return (
        f'<div class="msg-row {side}">'
        f'<div class="bubble">'
        f'{sender_tag}'
        f'<div class="content">{content_html}</div>'
        f'<div class="time">{esc(time_str)}</div>'
        f'</div>'
        f'</div>'
    )


def gen_header(title, back_link=None):
    back = f'<a class="back" href="{back_link}">← 返回</a>' if back_link else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{get_css_path()}">
</head>
<body>
<div class="page-header">
  {back}
  <h1>{esc(title)}</h1>
</div>
"""


def get_css_path():
    # 根据当前文件层级计算 CSS 相对路径（由调用处设置全局）
    return REL_CSS


REL_CSS = "style.css"
REL_MEDIA = "media/"


def write_html(path, title, messages, back_link=None, nav_months=None, current_month=None):
    """写一个月份的 HTML 文件。"""
    parts = [gen_header(title, back_link)]
    if nav_months:
        parts.append('<div class="month-nav">')
        for m in nav_months:
            cls = "active" if m == current_month else ""
            parts.append(f'<a class="month-link {cls}" href="{m}.html">{m}</a>')
        parts.append('</div>')
    parts.append('<div class="chat-container">')
    for msg in messages:
        parts.append(render_message(msg, "merged" if "merged" in path else "single"))
    parts.append('</div>')
    parts.append('<div class="page-footer">共 ' + str(len(messages)) + ' 条消息</div>')
    parts.append('</body></html>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def gen_index(months, chat_months_map):
    """生成总入口页。"""
    parts = [gen_header("聊天记录归档")]
    parts.append('<div class="index-intro">')
    parts.append('<p>与她的全部聊天记录（2020-12 ~ 2026-10）</p>')
    parts.append('<p>共 ' + str(len(months)) + ' 个月份，离线可读</p>')
    parts.append('</div>')

    # 合并时间线
    parts.append('<h2>📅 合并时间线（全部对话按时间混排）</h2>')
    parts.append('<div class="month-nav index-nav">')
    for m in months:
        parts.append(f'<a class="month-link" href="merged/{m}.html">{m}</a>')
    parts.append('</div>')

    # 单聊视图
    for acc in ("da_hao", "xiao_hao"):
        parts.append(f'<h2>👤 {esc(ACCOUNT_LABELS[acc])} 的对话</h2>')
        for conv in ("her_da", "her_xiao", "group"):
            key = f"{acc}__{conv}"
            conv_months = chat_months_map.get(key, [])
            parts.append(f'<h3>{esc(CONV_LABELS[conv])}</h3>')
            parts.append('<div class="month-nav index-nav">')
            for m in conv_months:
                parts.append(f'<a class="month-link" href="{acc}/{conv}/{m}.html">{m}</a>')
            parts.append('</div>')

    parts.append('</body></html>')
    with open(os.path.join(HTML_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main():
    global REL_CSS, REL_MEDIA
    print("加载数据 ...")
    merged = json.load(open(os.path.join(BASE, "merged_by_month.json"), encoding="utf-8"))
    chat = json.load(open(os.path.join(BASE, "chat_by_month.json"), encoding="utf-8"))
    months = sorted(merged.keys())

    # 1. 合并时间线
    print("生成合并时间线 ...")
    REL_CSS = "../style.css"
    REL_MEDIA = "../../media/"
    for m in months:
        path = os.path.join(HTML_DIR, "merged", f"{m}.html")
        write_html(path, f"合并时间线 · {m}", merged[m], back_link="../index.html",
                   nav_months=months, current_month=m)

    # 2. 单聊视图
    print("生成单聊视图 ...")
    chat_months_map = {}
    for conv_key, month_groups in chat.items():
        acc, conv = conv_key.split("__", 1)
        conv_months = sorted(month_groups.keys())
        chat_months_map[conv_key] = conv_months
        for m in conv_months:
            REL_CSS = "../../style.css"
            REL_MEDIA = "../../../media/"
            path = os.path.join(HTML_DIR, acc, conv, f"{m}.html")
            title = f"{ACCOUNT_LABELS[acc]} · {CONV_LABELS[conv]} · {m}"
            write_html(path, title, month_groups[m],
                       back_link=f"../../index.html",
                       nav_months=conv_months, current_month=m)

    # 3. 总入口
    print("生成总入口 ...")
    REL_CSS = "style.css"
    REL_MEDIA = "media/"
    gen_index(months, chat_months_map)

    # 4. 写 CSS
    write_css()
    print("完成！")


def write_css():
    css = """* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f0f2f5;
  color: #1a1a1a;
  line-height: 1.6;
}
.page-header {
  background: #fff;
  padding: 16px 24px;
  border-bottom: 1px solid #e4e6eb;
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 16px;
}
.page-header h1 { font-size: 20px; font-weight: 600; }
.back { color: #1877f2; text-decoration: none; font-size: 14px; white-space: nowrap; }
.back:hover { text-decoration: underline; }
.month-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e6eb;
}
.month-link {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  background: #f0f2f5;
  color: #333;
  text-decoration: none;
  font-size: 13px;
}
.month-link:hover { background: #e4e6eb; }
.month-link.active { background: #1877f2; color: #fff; }
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.msg-row { display: flex; }
.msg-row.me { justify-content: flex-end; }
.msg-row.other { justify-content: flex-start; }
.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 16px;
  position: relative;
  word-break: break-word;
}
.msg-row.me .bubble { background: #95ec69; border-top-right-radius: 4px; }
.msg-row.other .bubble { background: #fff; border-top-left-radius: 4px; }
.sender { font-size: 12px; color: #65676b; margin-bottom: 2px; }
.content { font-size: 15px; white-space: pre-wrap; }
.time { font-size: 11px; color: #888; margin-top: 4px; text-align: right; }
.chat-img { max-width: 260px; max-height: 320px; border-radius: 8px; display: block; }
.chat-emoji { max-width: 120px; max-height: 120px; border-radius: 4px; display: block; }
.emoji-caption { font-size: 11px; color: #999; margin-top: 2px; }
.emoji-text { font-size: 15px; color: #555; }
.placeholder { color: #888; font-style: italic; }
.voice { color: #1877f2; }
audio { width: 220px; height: 36px; margin-top: 4px; display: block; }
.appmsg { color: #1877f2; }
.system-msg { color: #65676b; }
.call { color: #65676b; }
.sys-row {
  text-align: center;
  font-size: 13px;
  color: #65676b;
  padding: 4px 0;
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sys-time { color: #999; }
.sys-text { color: #65676b; }
.page-footer {
  text-align: center;
  color: #999;
  font-size: 12px;
  padding: 20px;
}
.index-intro { padding: 20px 24px; background: #fff; margin-bottom: 8px; }
.index-intro p { margin: 4px 0; color: #555; }
h2 { font-size: 17px; padding: 16px 24px 8px; color: #333; }
h3 { font-size: 15px; padding: 8px 24px 4px; color: #555; }
.index-nav { margin-bottom: 8px; }
"""
    with open(os.path.join(HTML_DIR, "style.css"), "w", encoding="utf-8") as f:
        f.write(css)


if __name__ == "__main__":
    main()
