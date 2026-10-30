#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清洗单聊语料 —— 通用版（不绑定具体人名）

输入：export_chat.py 导出的 TXT（格式 `[时间] [说话人] 内容`）
输出：
  1. <prefix>_slices.txt       —— A/B 对话切片（忠实原文，不提炼）
  2. <prefix>_classified.json  —— 按场景分类
  3. <prefix>_privacy.txt      —— 疑似隐私提示（只提示，不删除）

用法：
  python clean_corpus.py 输入.txt --a "我的显示名" --b "对方显示名" \
      --alias "对方称呼" --out 输出目录 [--prefix 文件名前缀]

角色映射：A = 我（--a 指定），B = 对方（--b 指定）。A 的话作为 user 输入，
B 的话作为 assistant 输出，组成 A→B 对话对。
"""

import argparse
import json
import os
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

# 需要过滤的非文字消息（内容完全匹配这些占位符的）
NON_TEXT_EXACT = {
    "[Sticker]", "[Image]", "[Video]", "[Audio]", "[File]", "[Link]",
    "[动画表情]", "[图片]", "[语音]", "[视频]", "[文件]",
}

# 需要过滤的非文字前缀（消息内容以这些开头的）
NON_TEXT_PREFIX = [
    "[Sticker]", "[Image]", "[Video]", "[Audio]", "[File]",
    "[聊天记录]", "[小程序]", "[分享", "[名片]", "[转账]", "[红包]",
    "[位置]", "[语音]", "[视频分享]", "[视频号]",
]

# 系统消息
SYSTEM_PREFIX = ["[系统"]

# 需要剥离的引用/XML 噪声（引用图片、链接等产生的原始标记）
NOISE_PATTERNS = [
    r"\[引用消息\][\s\S]*?(?=\[引用消息\]|$)",  # 引用消息块
    r"<\?xml[\s\S]*?>",                        # XML 片段
    r"<msg>[\s\S]*?</msg>",                    # msg 标签
    r"<img[^>]*/>",                            # img 标签（含 aeskey）
    r"aeskey=\"[^\"]*\"",                       # aeskey 属性
    r"cdnurl=\"[^\"]*\"",                       # cdnurl 属性
    r"<[a-zA-Z]+[^>]*>",                       # 残留 XML 标签
]

# 疑似隐私关键词（用于提示，不自动删除）
PRIVACY_PATTERNS = [
    (r"\b1[3-9]\d{9}\b", "手机号"),
    (r"\b\d{17}[\dXx]\b", "身份证号"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "邮箱"),
    (r"(?<![0-9a-fA-F])\d{6}(?![0-9a-fA-F])", "6位数字（可能是密码/验证码）"),
    (r"密码|银行卡|住址|家庭住址|身份证号|账号", "敏感词"),
]

# 场景关键词（可自行扩充；未命中的归"未分类"）
SCENE_RULES = [
    ("日常闲聊", ["今天", "昨天", "吃", "喝", "睡", "天气", "在哪", "干嘛", "忙",
                  "上班", "下班", "周末", "游戏", "电影", "音乐", "推荐", "好看",
                  "最近", "怎么样", "还好", "还行"]),
    ("认真讨论", ["我觉得", "你认为", "其实", "问题是", "道理", "逻辑", "分析", "结论",
                  "不同意", "但是", "不过", "说白了", "认真", "讲道理", "客观",
                  "实际上", "换个角度", "观点", "看法", "思考"]),
    ("安慰关心玩笑", ["哈哈", "哈哈哈", "笑死", "没事", "别难过", "抱抱", "加油", "心疼",
                      "辛苦", "好好休息", "没事的", "我懂", "别担心", "摸摸", "不哭",
                      "哈哈哈", "笑", "逗", "梗", "😊", "😂", "🤣", "😭", "🥺"]),
]


def strip_noise(content):
    """剥离引用消息和 XML 噪声，返回清理后的纯文字。"""
    text = content
    for pat in NOISE_PATTERNS:
        text = re.sub(pat, "", text)
    text = text.replace("</msg>", "").replace("<msg>", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_line(line, a_name, b_name):
    """解析一行 -> (时间, 说话人, 内容) 或 None。"""
    line = line.strip()
    if not line:
        return None
    m = re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(.+?)\]\s?(.*)$", line)
    if not m:
        return None
    ts, speaker, content = m.group(1), m.group(2).strip(), m.group(3).strip()

    # 过滤系统消息
    if any(content.startswith(p) for p in SYSTEM_PREFIX) or speaker.startswith("系统"):
        return None

    # 过滤非文字（精确匹配 / 前缀）
    if content in NON_TEXT_EXACT:
        return None
    if any(content.startswith(p) for p in NON_TEXT_PREFIX):
        return None
    if not content:
        return None

    # 剥离引用/XML 噪声
    content = strip_noise(content)
    if not content:
        return None

    # 判定角色
    if speaker == a_name:
        role = "A"
    elif speaker == b_name:
        role = "B"
    else:
        role = "B" if speaker != a_name else "A"

    return {"ts": ts, "speaker": speaker, "role": role, "content": content}


def classify_scene(text):
    """给文本打场景标签，返回场景名或 None。"""
    scores = defaultdict(int)
    for scene, kws in SCENE_RULES:
        for kw in kws:
            if kw in text:
                scores[scene] += 1
    if not scores:
        return None
    return max(scores, key=scores.get)


def detect_privacy(content):
    """检测隐私，返回 [类型]。基于已剥离噪声的纯文字。"""
    return [label for pattern, label in PRIVACY_PATTERNS if re.search(pattern, content)]


def main():
    ap = argparse.ArgumentParser(description="清洗单聊语料为 A/B 对话")
    ap.add_argument("input", help="导出的 TXT 路径")
    ap.add_argument("--a", required=True, help="我（A）的显示名")
    ap.add_argument("--b", required=True, help="对方（B）的显示名")
    ap.add_argument("--alias", default=None, help="对方称呼（用于切片标注，可省略）")
    ap.add_argument("--out", default=".", help="输出目录")
    ap.add_argument("--prefix", default="chat", help="输出文件名前缀")
    args = ap.parse_args()

    a_name, b_name = args.a, args.b
    b_label = args.alias or b_name
    os.makedirs(args.out, exist_ok=True)

    # 1. 解析
    messages = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            p = parse_line(line, a_name, b_name)
            if p:
                messages.append(p)

    a_count = sum(1 for m in messages if m["role"] == "A")
    b_count = sum(1 for m in messages if m["role"] == "B")
    print(f"解析出 {len(messages)} 条纯文字消息（A={a_count}, B={b_count}）")

    # 2. 切片成轮次（连续同角色合并）
    turns = []
    cur = None
    for m in messages:
        if cur is None:
            cur = {"role": m["role"], "ts": m["ts"], "content": m["content"]}
        elif m["role"] == cur["role"]:
            cur["content"] += "\n" + m["content"]
        else:
            turns.append(cur)
            cur = {"role": m["role"], "ts": m["ts"], "content": m["content"]}
    if cur:
        turns.append(cur)
    print(f"切片成 {len(turns)} 轮")

    # 3. 组成 A->B 对话对
    pairs = []
    i = 0
    while i < len(turns) - 1:
        if turns[i]["role"] == "A" and turns[i + 1]["role"] == "B":
            pairs.append({"user": turns[i]["content"], "assistant": turns[i + 1]["content"], "ts": turns[i]["ts"]})
            i += 2
        else:
            i += 1
    print(f"组成 {len(pairs)} 组 A→B 对话对")

    # 4. 输出切片（忠实原文）
    slices_path = os.path.join(args.out, f"{args.prefix}_slices.txt")
    with open(slices_path, "w", encoding="utf-8") as f:
        f.write(f"# 单聊切片（A={a_name}/我，B={b_name}/{b_label}）\n")
        f.write(f"# 共 {len(turns)} 轮，{len(pairs)} 组 A→B 对话对\n")
        f.write("#" + "=" * 70 + "\n\n")
        for t in turns:
            who = "A(我)" if t["role"] == "A" else f"B({b_label})"
            f.write(f"[{t['ts']}] {who}：\n{t['content']}\n\n")
    print(f"[OK] 切片 -> {slices_path}")

    # 5. 场景分类
    classified = defaultdict(list)
    for p in pairs:
        scene = classify_scene(p["assistant"]) or classify_scene(p["user"])
        classified[scene or "未分类"].append(p)
    cls_path = os.path.join(args.out, f"{args.prefix}_classified.json")
    with open(cls_path, "w", encoding="utf-8") as f:
        json.dump({"scenes": {k: v for k, v in classified.items()}}, f, ensure_ascii=False, indent=2)
    print(f"[OK] 场景分类 -> {cls_path}")
    for scene, items in sorted(classified.items(), key=lambda x: -len(x[1])):
        print(f"    {scene}: {len(items)} 组")

    # 6. 隐私检测（只提示，不删除）
    privacy = []
    for m in messages:
        for label in detect_privacy(m["content"]):
            privacy.append({"ts": m["ts"], "role": m["role"], "type": label, "content": m["content"][:80]})
    priv_path = os.path.join(args.out, f"{args.prefix}_privacy.txt")
    with open(priv_path, "w", encoding="utf-8") as f:
        f.write(f"疑似隐私内容提示（共 {len(privacy)} 处，请人工判断是否删除）\n")
        f.write("=" * 60 + "\n\n")
        for h in privacy:
            who = "A(我)" if h["role"] == "A" else f"B({b_label})"
            f.write(f"[{h['ts']}] [{who}] ({h['type']})\n  {h['content']}\n\n")
    print(f"[OK] 隐私提示 -> {priv_path}（{len(privacy)} 处）")

    print("\n完成。请查看切片文件和隐私提示文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
