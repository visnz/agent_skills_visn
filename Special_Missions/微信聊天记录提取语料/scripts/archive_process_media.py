#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体处理脚本：解密图片、复制文件/视频、建立表情描述映射、语音索引。

分阶段执行（通过 --stage 参数控制），每阶段可独立重跑：

  python process_media.py --stage emoji_map    # 构建表情 md5→描述词映射（快）
  python process_media.py --stage voice_index  # 语音索引（快）
  python process_media.py --stage images       # 图片解密+转码（慢，后台跑）
  python process_media.py --stage files        # 文件/视频复制（中）
  python process_media.py --stage all          # 全部

关键密钥（已破解）：
  账号 A: UIN=<十进制UIN>, XOR=<从缩略图尾部反推>, AES=MD5(UIN+wxid)[:16]
  账号 B: 同上

【导出前必须替换的占位符】本脚本为模板，以下字段均为占位符，填入真实值：
  - DATA_ROOT          → 微信数据根目录（微信「设置→文件管理」里的 xwechat_files 路径）
  - ACCOUNTS[].dir     → 账号目录名（xwechat_files 下的 <wxid>_<后缀> 子目录）
  - ACCOUNTS[].wxid    → 账号 wxid（从目录名或 contact.db 获取）
  - ACCOUNTS[].uin     → 账号 UIN（十进制数字字符串，用于 md5(UIN+wxid) 派生图片 AES key）
  - ACCOUNTS[].xor_key → 图片 XOR key（从缩略图 _t.dat 尾部反推，JPEG 尾 FF D9）
  新账号的 uin / xor_key 需重新破解，不能沿用模板里的占位值。
"""
import os
import sys
import json
import hashlib
import shutil
import sqlite3
import subprocess
import re
from pathlib import Path
from datetime import datetime

from Crypto.Cipher import AES

BASE = Path(__file__).resolve().parent
MEDIA_DIR = BASE / "media"

# 原始微信数据根
DATA_ROOT = Path(r"E:\Documents\WechatFiles\xwechat_files")

# 账号配置（占位符，导出前替换）
ACCOUNTS = {
    "da_hao": {
        "dir": "wxid_ACCOUNT_A_DIRSUFFIX",
        "wxid": "wxid_ACCOUNT_A",
        "uin": "UIN_ACCOUNT_A_PLACEHOLDER",
        "xor_key": 0xB1,
    },
    "xiao_hao": {
        "dir": "wxid_ACCOUNT_B_DIRSUFFIX",
        "wxid": "wxid_ACCOUNT_B",
        "uin": "UIN_ACCOUNT_B_PLACEHOLDER",
        "xor_key": 0x11,
    },
}

# 解密库根
DECRYPTED_ROOT = Path(r"D:\wechat-corpus-work\wechat-decrypt\decrypted")

# ffmpeg
FFMPEG = r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"


def aes_key_of(account):
    a = ACCOUNTS[account]
    return hashlib.md5((a["uin"] + a["wxid"]).encode()).hexdigest()[:16].encode("ascii")


def decrypt_v2(data, aes_key, xor_key):
    """V2 图片解密：AES-128-ECB 段 + 明文段 + XOR 尾段。"""
    if len(data) < 15 or data[:6] != b"\x07\x08\x56\x32\x08\x07":
        return None
    aes_size = int.from_bytes(data[6:10], "little")
    xor_size = int.from_bytes(data[10:14], "little")
    aes_start = 15
    aes_len = aes_size + 16
    if aes_start + aes_len > len(data):
        return None
    cipher = data[aes_start:aes_start + aes_len]
    dec = AES.new(aes_key, AES.MODE_ECB).decrypt(cipher)
    pad = dec[-1]
    if 1 <= pad <= 16:
        dec = dec[:-pad]
    plain_start = aes_start + aes_len
    plain_len = len(data) - plain_start - xor_size
    if plain_len < 0:
        return None
    plain = data[plain_start:plain_start + plain_len]
    xor_tail = bytes(b ^ xor_key for b in data[plain_start + plain_len:])
    return dec + plain + xor_tail


def image_ext(data):
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


def convert_wxgf_to_png(src_bytes, dst_path):
    """wxgf（HEVC）→ PNG，用 ffmpeg 提取首帧（通过 stdin 管道，避免临时文件）。"""
    try:
        r = subprocess.run(
            [FFMPEG, "-y", "-i", "pipe:0", "-frames:v", "1", "-update", "1", str(dst_path)],
            input=src_bytes, capture_output=True, timeout=60,
        )
        if dst_path.exists() and dst_path.stat().st_size > 0:
            return True
    except Exception:
        pass
    # 回退：提取 Annex-B 起始码后的裸流
    raw = src_bytes
    idx = raw.find(b"\x00\x00\x00\x01")
    if idx < 0:
        idx = raw.find(b"\x00\x00\x01")
    if idx >= 0:
        stream = raw[idx:]
        try:
            r = subprocess.run(
                [FFMPEG, "-y", "-f", "hevc", "-i", "pipe:0", "-frames:v", "1", "-update", "1", str(dst_path)],
                input=stream, capture_output=True, timeout=60,
            )
            if dst_path.exists() and dst_path.stat().st_size > 0:
                return True
        except Exception:
            pass
    return False


def build_emoji_map(account_key):
    """构建系统/商店表情 md5 → 描述词映射。合并所有语言，zh_cn 优先。"""
    acc = ACCOUNTS[account_key]
    db = DECRYPTED_ROOT / acc["dir"] / "db_storage" / "emoticon" / "emoticon.db"
    emoji_map = {}
    if db.exists():
        con = sqlite3.connect(str(db))
        try:
            # 先取 default，再让 zh_cn / zh_tw 覆盖（更地道中文）
            for md5, caption in con.execute(
                "SELECT md5_, caption_ FROM kStoreEmoticonCaptionsTable WHERE language_='default'"
            ):
                if caption:
                    emoji_map[md5.lower()] = caption
            for md5, caption in con.execute(
                "SELECT md5_, caption_ FROM kStoreEmoticonCaptionsTable "
                "WHERE language_ IN ('zh_cn','zh_tw')"
            ):
                if caption:
                    emoji_map[md5.lower()] = caption
        except Exception:
            pass
        finally:
            con.close()
    return emoji_map


def build_custom_emoji_md5(account_key):
    """返回自定义表情的 md5 集合（用于区分系统/自定义）。"""
    acc = ACCOUNTS[account_key]
    db = DECRYPTED_ROOT / acc["dir"] / "db_storage" / "emoticon" / "emoticon.db"
    custom = set()
    if db.exists():
        con = sqlite3.connect(str(db))
        try:
            for (md5,) in con.execute("SELECT md5 FROM kNonStoreEmoticonTable"):
                if md5:
                    custom.add(md5.lower())
        except Exception:
            pass
        finally:
            con.close()
    return custom


def find_image_file(account_key, md5):
    """在 attach 目录查找 md5 对应的图片文件路径（返回原图优先，否则缩略图）。"""
    acc = ACCOUNTS[account_key]
    attach = DATA_ROOT / acc["dir"] / "msg" / "attach"
    if not md5:
        return None, None
    # 遍历 attach 目录，md5 作为文件名前缀
    # 文件名格式: <md5>.dat, <md5>_t.dat, <md5>_h.dat 或 <localid>_<ts>.dat
    # 由于 attach 是 <conversation_hash>/<year-month>/Img/ 结构，需要全盘搜索
    # 优化：md5 前两位可作第一层 hash（但 attach 第一层是会话hash，不是md5前缀）
    # 这里用 message_resource 或 hardlink 建立 md5→路径映射更高效
    return None, None


def build_image_index(account_key):
    """遍历 attach 目录，建立 md5 → 文件路径映射。"""
    acc = ACCOUNTS[account_key]
    attach = DATA_ROOT / acc["dir"] / "msg" / "attach"
    index = {}
    if not attach.exists():
        return index
    for conv_dir in attach.iterdir():
        if not conv_dir.is_dir():
            continue
        for ym_dir in conv_dir.iterdir():
            if not ym_dir.is_dir():
                continue
            img_dir = ym_dir / "Img"
            if not img_dir.is_dir():
                continue
            for f in img_dir.iterdir():
                if not f.is_file() or not f.name.endswith(".dat"):
                    continue
                # 提取 md5（文件名前32位若是hex）
                stem = f.name[:-4]  # 去 .dat
                # 去掉 _t / _h 后缀
                base = stem
                for suf in ("_t", "_h"):
                    if base.endswith(suf):
                        base = base[:-2]
                if re.fullmatch(r"[0-9a-fA-F]{32}", base):
                    index[base.lower()] = f
                # 也记录带后缀的（缩略图/原图）
                m = re.match(r"([0-9a-fA-F]{32})(_t|_h)?", stem)
                if m:
                    md5 = m.group(1).lower()
                    kind = m.group(2) or ""
                    if kind == "_t":
                        index.setdefault(md5 + "|thumb", f)
                    elif kind == "_h":
                        index.setdefault(md5 + "|hd", f)
                    else:
                        index.setdefault(md5 + "|orig", f)
    return index


def process_images(account_key, image_index, out_subdir):
    """解密并转码该账号所有图片消息。支持断点续跑。"""
    messages = load_messages()
    acc = ACCOUNTS[account_key]
    aes_key = aes_key_of(account_key)
    xor_key = acc["xor_key"]
    out_dir = MEDIA_DIR / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 收集该账号所有图片消息的 md5
    md5_set = set()
    for conv_key, msgs in messages["conversations"].items():
        if not conv_key.startswith(account_key):
            continue
        for m in msgs:
            if m["kind"] == "image" and m.get("media") and m["media"].get("md5"):
                md5_set.add(m["media"]["md5"])

    # 断点续跑：加载已有结果
    result_file = BASE / f"image_results_{account_key}.json"
    results = {}
    if result_file.exists():
        try:
            results = json.load(open(result_file, encoding="utf-8"))
        except Exception:
            results = {}

    done = 0
    total = len(md5_set)
    for i, md5 in enumerate(sorted(md5_set)):
        # 已成功处理过的跳过
        if md5 in results and results[md5]["status"] == "ok":
            continue
        # 优先原图，其次缩略图
        src = None
        for key_suf, prefer in (("|orig", 0), ("|hd", 1), ("", 2), ("|thumb", 3)):
            k = md5 + key_suf if key_suf else md5
            if k in image_index:
                src = image_index[k]
                break
        if src is None:
            results[md5] = {"status": "not_found"}
            continue
        try:
            data = src.read_bytes()
        except OSError:
            results[md5] = {"status": "read_fail"}
            continue
        dec = decrypt_v2(data, aes_key, xor_key)
        if dec is None:
            results[md5] = {"status": "decrypt_fail"}
            continue
        ext = image_ext(dec)
        if ext is None:
            results[md5] = {"status": "unknown_format"}
            continue
        if ext == "wxgf":
            png_dst = out_dir / f"{md5}.png"
            if png_dst.exists():
                results[md5] = {"status": "ok", "file": f"{md5}.png"}
            elif convert_wxgf_to_png(dec, png_dst):
                results[md5] = {"status": "ok", "file": f"{md5}.png"}
            else:
                results[md5] = {"status": "wxgf_convert_fail"}
        else:
            dst = out_dir / f"{md5}.{ext}"
            dst.write_bytes(dec)
            results[md5] = {"status": "ok", "file": f"{md5}.{ext}"}
        done += 1
        # 每 200 张保存一次进度
        if done % 200 == 0:
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False)
            print(f"  [{account_key}] 进度 {i+1}/{total} (本轮 {done})")

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    return results


def process_files(account_key, out_subdir):
    """按需复制文件（type=6，明文）和视频（type=43，明文）。

    只复制消息里实际引用的文件/视频，避免全量复制数万无关文件。
    """
    acc = ACCOUNTS[account_key]
    messages = load_messages()
    out_dir = MEDIA_DIR / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 收集该账号所有文件消息的 title 和视频消息的 md5
    file_titles = set()
    video_md5s = set()
    for conv_key, msgs in messages["conversations"].items():
        if not conv_key.startswith(account_key):
            continue
        for m in msgs:
            c = m.get("content") or ""
            if m["kind"] == "appmsg":
                mt = re.search(r"<type>(\d+)</type>", c)
                if mt and mt.group(1) == "6":
                    title = re.search(r"<title>([^<]*)</title>", c)
                    if title:
                        file_titles.add(title.group(1))
            elif m["kind"] == "video" and m.get("media") and m["media"].get("md5"):
                video_md5s.add(m["media"]["md5"])

    results = {"files": 0, "videos": 0, "file_missing": 0, "video_missing": 0}

    # 复制文件：按文件名在 msg/file/<年月>/ 下查找
    file_dir = DATA_ROOT / acc["dir"] / "msg" / "file"
    if file_dir.exists():
        # 建立 文件名 → 路径 映射
        name_index = {}
        for ym in file_dir.iterdir():
            if not ym.is_dir():
                continue
            for f in ym.iterdir():
                if f.is_file():
                    name_index.setdefault(f.name, f)
        dst_files = out_dir / "files"
        dst_files.mkdir(parents=True, exist_ok=True)
        for title in file_titles:
            if title in name_index:
                try:
                    shutil.copy2(name_index[title], dst_files / title)
                    results["files"] += 1
                except OSError:
                    results["file_missing"] += 1
            else:
                results["file_missing"] += 1

    # 复制视频：按 md5 在 msg/video/<年月>/ 下查找
    video_dir = DATA_ROOT / acc["dir"] / "msg" / "video"
    if video_dir.exists():
        dst_video = out_dir / "videos"
        dst_video.mkdir(parents=True, exist_ok=True)
        for md5 in video_md5s:
            found = False
            for ym in video_dir.iterdir():
                if not ym.is_dir():
                    continue
                mp4 = ym / f"{md5}.mp4"
                if mp4.is_file():
                    try:
                        shutil.copy2(mp4, dst_video / f"{md5}.mp4")
                        results["videos"] += 1
                        found = True
                    except OSError:
                        pass
                    break
            if not found:
                results["video_missing"] += 1

    return results


def build_voice_index(account_key):
    """建立语音索引：svr_id → {duration_ms, ...}。"""
    acc = ACCOUNTS[account_key]
    media_db = DECRYPTED_ROOT / acc["dir"] / "db_storage" / "message" / "media_0.db"
    voice_index = {}
    if media_db.exists():
        con = sqlite3.connect(str(media_db))
        try:
            for svr_id, create_time, local_id, voice_data in con.execute(
                "SELECT svr_id, create_time, local_id, voice_data FROM VoiceInfo"
            ):
                # voice_data 是 SILK_V3 二进制
                voice_index[str(svr_id)] = {
                    "create_time": create_time,
                    "local_id": local_id,
                    "has_data": bool(voice_data and len(voice_data) > 0),
                    "data_len": len(voice_data) if voice_data else 0,
                }
        except Exception:
            pass
        finally:
            con.close()
    return voice_index


def load_messages():
    with open(BASE / "messages_raw.json", encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data):
    out = BASE / name
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  已保存: {out}")


def main():
    stage = "all"
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a in ("--stage", "-s") and i + 1 < len(args):
            stage = args[i + 1]
        elif a.startswith("--stage="):
            stage = a.split("=", 1)[1]
        elif a in ("emoji_map", "voice_index", "images", "files", "all"):
            stage = a

    if stage in ("emoji_map", "all"):
        print("== 构建表情描述映射 ==")
        for acc_key in ACCOUNTS:
            emap = build_emoji_map(acc_key)
            custom = build_custom_emoji_md5(acc_key)
            save_json(f"emoji_map_{acc_key}.json", {
                "system_map": emap,
                "custom_md5": list(custom),
            })
            print(f"  {acc_key}: 系统表情描述 {len(emap)} 条, 自定义表情 {len(custom)} 个")

    if stage in ("voice_index", "all"):
        print("== 语音索引 ==")
        for acc_key in ACCOUNTS:
            vi = build_voice_index(acc_key)
            save_json(f"voice_index_{acc_key}.json", vi)
            has_data = sum(1 for v in vi.values() if v["has_data"])
            print(f"  {acc_key}: {len(vi)} 条语音, 有数据 {has_data} 条")

    if stage in ("images", "all"):
        print("== 图片解密+转码 ==")
        # 支持 --account da_hao 只跑指定账号
        acc_filter = None
        for i, a in enumerate(args):
            if a in ("--account", "-a") and i + 1 < len(args):
                acc_filter = args[i + 1]
        for acc_key in ACCOUNTS:
            if acc_filter and acc_key != acc_filter:
                continue
            print(f"  建立 {acc_key} 图片索引 ...")
            idx = build_image_index(acc_key)
            print(f"    索引 {len(idx)} 个文件")
            results = process_images(acc_key, idx, f"images_{acc_key}")
            ok = sum(1 for v in results.values() if v["status"] == "ok")
            print(f"  {acc_key}: 图片 {len(results)} 张, 成功 {ok} 张")

    if stage in ("files", "all"):
        print("== 文件/视频复制 ==")
        for acc_key in ACCOUNTS:
            r = process_files(acc_key, f"files_{acc_key}")
            print(f"  {acc_key}: 文件 {r['files']} 个, 视频 {r['videos']} 个")

    print("\n完成。")


if __name__ == "__main__":
    main()
