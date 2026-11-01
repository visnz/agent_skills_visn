#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音转码脚本：把消息里引用的语音 SILK_V3 BLOB 转成 mp3，供 HTML <audio> 播放。
- 用 voice_env 的 pilk 解码 silk -> wav
- 用 ffmpeg 转 wav -> mp3（压缩体积，适合归档）
- 只转码 messages_raw.json 里实际出现的 svr_id
运行：voice_env/Scripts/python.exe process_voice.py
"""
import json
import sqlite3
import sys
import tempfile
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parent
DECRYPTED_ROOT = Path(r"D:\wechat-corpus-work\wechat-decrypt\decrypted")
FFMPEG = r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
OUT_DIR = BASE / "media" / "voice"

ACCOUNTS = {
    "da_hao": {"dir": "wxid_ACCOUNT_A_DIRSUFFIX"},
    "xiao_hao": {"dir": "wxid_ACCOUNT_B_DIRSUFFIX"},
}

try:
    from pilk import decode as silk_decode
except ImportError:
    print("错误：请在 voice_env 环境下运行本脚本", file=sys.stderr)
    sys.exit(1)


def collect_needed_svr_ids():
    """从 messages_raw.json 收集所有语音 svr_id。"""
    msgs = json.load(open(BASE / "messages_raw.json", encoding="utf-8"))
    svr_ids = set()
    for ckey, mlist in msgs["conversations"].items():
        for m in mlist:
            if m.get("kind") == "voice":
                sid = m.get("media", {}).get("svr_id")
                if sid:
                    svr_ids.add(str(sid))
    return svr_ids


def load_voice_blob_map(account_key):
    """返回 {svr_id(str): voice_data(bytes)}。"""
    acc = ACCOUNTS[account_key]
    db = DECRYPTED_ROOT / acc["dir"] / "db_storage" / "message" / "media_0.db"
    blob_map = {}
    if not db.exists():
        return blob_map
    con = sqlite3.connect(str(db))
    try:
        for svr_id, voice_data in con.execute(
            "SELECT svr_id, voice_data FROM VoiceInfo WHERE voice_data IS NOT NULL"
        ):
            if voice_data:
                blob_map[str(svr_id)] = bytes(voice_data)
    finally:
        con.close()
    return blob_map


def silk_bytes_to_wav(silk_bytes, wav_path, rate=24000):
    """把 SILK_V3 二进制转成 wav 文件。pilk 的 decode 需要文件路径，用临时文件。"""
    # pilk.decode 接受文件路径，写临时 silk 文件
    with tempfile.NamedTemporaryFile(suffix=".silk", delete=False) as f:
        silk_path = f.name
        f.write(silk_bytes)
    pcm_path = silk_path + ".pcm"
    try:
        silk_decode(silk_path, pcm_path, pcm_rate=rate)
        with open(pcm_path, "rb") as pcm:
            with wave.open(str(wav_path), "wb") as wf:
                wf.setparams((1, 2, rate, 0, "NONE", "NONE"))
                wf.writeframes(pcm.read())
    finally:
        for p in (silk_path, pcm_path):
            try:
                Path(p).unlink()
            except Exception:
                pass


def wav_to_mp3(wav_path, mp3_path):
    import subprocess
    subprocess.run(
        [FFMPEG, "-y", "-i", str(wav_path), "-acodec", "libmp3lame",
         "-b:a", "32k", "-ar", "24000", str(mp3_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    needed = collect_needed_svr_ids()
    print(f"需要转码的语音 svr_id: {len(needed)} 个")

    # 合并两号 blob 映射（同 svr_id 可能两号都有，取大号优先）
    blob_map = {}
    for acc_key in ACCOUNTS:
        m = load_voice_blob_map(acc_key)
        print(f"  {acc_key}: VoiceInfo 有数据 {len(m)} 条")
        for sid, data in m.items():
            blob_map.setdefault(sid, data)

    # 已存在的跳过
    existing = {p.stem for p in OUT_DIR.glob("*.mp3")}
    todo = needed - existing
    print(f"已完成 {len(needed & existing)} 个, 待转码 {len(todo)} 个")

    ok = 0
    fail = 0
    total = len(todo)
    # wav 临时文件统一放系统临时目录，退出时由 TemporaryDirectory 自动清理
    with tempfile.TemporaryDirectory(prefix="voice_wav_") as tmp_name:
        tmp_dir = Path(tmp_name)
        for i, sid in enumerate(sorted(todo), 1):
            data = blob_map.get(sid)
            if not data:
                fail += 1
                continue
            mp3_path = OUT_DIR / f"{sid}.mp3"
            wav_path = tmp_dir / f"{sid}.wav"
            try:
                silk_bytes_to_wav(data, wav_path)
                wav_to_mp3(wav_path, mp3_path)
                ok += 1
            except Exception:
                fail += 1
            if i % 200 == 0 or i == total:
                print(f"  进度 {i}/{total} (成功 {ok}, 失败 {fail})")

    print(f"\n完成。成功 {ok}, 失败 {fail}（无 BLOB 或解码失败）")


if __name__ == "__main__":
    main()
