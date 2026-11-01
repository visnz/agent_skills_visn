#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自定义表情解密脚本：解密本地收藏的自定义表情（kNonStoreEmoticonTable），
AES-128-CBC(key=md5(uin+wxid+"EMOTICON")[:16], IV=key) → wxgf/图片 → 转 PNG。
输出：media/emoji/<md5>.png
运行：wechat-decrypt/.venv/Scripts/python.exe process_emoji.py
"""
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

from Crypto.Cipher import AES

BASE = Path(__file__).resolve().parent
DECRYPTED_ROOT = Path(r"D:\wechat-corpus-work\wechat-decrypt\decrypted")
DATA_ROOT = Path(r"E:\Documents\WechatFiles\xwechat_files")
FFMPEG = r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
OUT_DIR = BASE / "media" / "emoji"

ACCOUNTS = {
    "da_hao": {"dir": "wxid_ACCOUNT_A_DIRSUFFIX", "wxid": "wxid_ACCOUNT_A", "uin": "UIN_ACCOUNT_A_PLACEHOLDER"},
    "xiao_hao": {"dir": "wxid_ACCOUNT_B_DIRSUFFIX", "wxid": "wxid_ACCOUNT_B", "uin": "UIN_ACCOUNT_B_PLACEHOLDER"},
}


def emoji_key(account_key):
    a = ACCOUNTS[account_key]
    return hashlib.md5(f"{a['uin']}{a['wxid']}EMOTICON".encode()).digest()[:16]


def detect_format(data):
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"wxgf":
        return "wxgf"
    return None


def to_png(data, dst_path):
    """把解密后的数据转成 PNG。wxgf 走 ffmpeg 裸流，其余直接写。"""
    fmt = detect_format(data)
    if fmt == "png":
        dst_path.write_bytes(data)
        return dst_path.exists() and dst_path.stat().st_size > 0
    if fmt == "jpg":
        # jpg 直接转 png 保透明/统一格式
        r = subprocess.run(
            [FFMPEG, "-y", "-i", "pipe:0", "-frames:v", "1", "-update", "1", str(dst_path)],
            input=data, capture_output=True, timeout=60,
        )
        if dst_path.exists() and dst_path.stat().st_size > 0:
            return True
        return False
    if fmt == "wxgf":
        # 先试直接吃 wxgf，失败则提取 Annex-B 裸流
        r = subprocess.run(
            [FFMPEG, "-y", "-i", "pipe:0", "-frames:v", "1", "-update", "1", str(dst_path)],
            input=data, capture_output=True, timeout=60,
        )
        if dst_path.exists() and dst_path.stat().st_size > 0:
            return True
        idx = data.find(b"\x00\x00\x00\x01")
        if idx < 0:
            idx = data.find(b"\x00\x00\x01")
        if idx >= 0:
            stream = data[idx:]
            r = subprocess.run(
                [FFMPEG, "-y", "-f", "hevc", "-i", "pipe:0", "-frames:v", "1", "-update", "1", str(dst_path)],
                input=stream, capture_output=True, timeout=60,
            )
            return dst_path.exists() and dst_path.stat().st_size > 0
        return False
    # gif/webp 直接存原格式（浏览器可显示）
    if fmt in ("gif", "webp"):
        ext = fmt
        p = dst_path.with_suffix("." + ext)
        p.write_bytes(data)
        return p.exists()
    return False


def process_account(account_key):
    acc = ACCOUNTS[account_key]
    key = emoji_key(account_key)
    db = DECRYPTED_ROOT / acc["dir"] / "db_storage" / "emoticon" / "emoticon.db"
    persist = DATA_ROOT / acc["dir"] / "business" / "emoticon" / "Persist"
    results = {}
    if not db.exists():
        return results
    con = sqlite3.connect(str(db))
    try:
        rows = con.execute(
            "SELECT md5, aes_key FROM kNonStoreEmoticonTable "
            "WHERE md5 IS NOT NULL AND aes_key IS NOT NULL AND aes_key != ''"
        ).fetchall()
    finally:
        con.close()

    for md5, aes_key in rows:
        md5 = md5.lower()
        f = persist / md5[:2] / md5
        if not f.exists():
            continue
        data = f.read_bytes()
        # 尝试解密（IV = key）
        dec = AES.new(key, AES.MODE_CBC, key).decrypt(data)
        fmt = detect_format(dec)
        if fmt is None:
            # 不是这个 key？尝试另一账号的 key（极少见，跳过）
            continue
        # 输出 png（gif/webp 会输出对应扩展名）
        out = OUT_DIR / f"{md5}.png"
        ok = to_png(dec, out)
        results[md5] = {"status": "ok" if ok else "fail", "file": out.name if ok else ""}
    return results


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {}
    for acc_key in ACCOUNTS:
        r = process_account(acc_key)
        ok = sum(1 for v in r.values() if v["status"] == "ok")
        all_results[acc_key] = r
        print(f"  {acc_key}: 自定义表情 {len(r)} 个, 成功 {ok} 个")
    json.dump(all_results, open(BASE / "emoji_results.json", "w", encoding="utf-8"), ensure_ascii=False)
    total_ok = sum(1 for acc in all_results.values() for v in acc.values() if v["status"] == "ok")
    print(f"\n完成。总计成功 {total_ok} 个")


if __name__ == "__main__":
    main()
