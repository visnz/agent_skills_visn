#!/usr/bin/env python3
"""
自动剪藏素材分流 —— 通用骨架脚本。

把「读剪藏 → 下载 → 入库素材库 → 确认成功 → 删源词条」的闭环做成可复用骨架。
本脚本是脱敏/参数化模板：不硬编码 token、页面 ID、真实路径，全部从 config.yaml 或环境变量读取。

依赖：requests, pyyaml（下载引擎按需：XHS-Downloader / gallery-dl）
用法：
    python triage_sync.py            # 正常同步（下载 + 入库 + 删源）
    python triage_sync.py --dry-run  # 只列出识别结果，不下载不删
    python triage_sync.py --no-delete # 下载入库但不删源词条

注意：
- 本脚本为方法骨架，非开箱即用成品；接入真实平台时按 references/platform-apis.md 的字段结构适配。
- 敏感信息一律放 config.yaml（不入库），脚本内只留占位符。
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
STATE_PATH = BASE_DIR / "state.json"


def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ---------------------------------------------------------------------------
# 配置与状态
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        log("缺少 config.yaml，请参考 config.example.yaml 填写")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# MCP 通用调用（健壮处理 SSE 多行 data）
# ---------------------------------------------------------------------------

def mcp_call(mcp_url: str, token: str, method: str, args: dict) -> dict:
    """调用 MCP 工具，返回解析后的 result（尽量解出内层 text 的 JSON）。"""
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 100000,
        "method": "tools/call",
        "params": {"name": method, "arguments": args},
    }

    resp = requests.post(mcp_url, json=payload, headers=headers, timeout=60)
    text = resp.text

    # SSE：拼接连续 data: 行（可能多行），再解析
    data_parts = []
    for line in text.splitlines():
        if line.startswith("data:"):
            data_parts.append(line[5:].strip())
    if not data_parts:
        log(f"MCP 调用失败 {method}: {text[:300]}")
        return {}
    data_line = "\n".join(data_parts)

    try:
        outer = json.loads(data_line)
    except json.JSONDecodeError as e:
        log(f"MCP 返回 JSON 解析失败 {method}: {e}")
        return {}

    result = outer.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content[0], dict) and content[0].get("type") == "text":
        try:
            return json.loads(content[0]["text"])
        except json.JSONDecodeError:
            return {"_raw": content[0]["text"]}
    return result


# ---------------------------------------------------------------------------
# 链接识别（按来源类型分流；正则与字段结构按实际平台适配）
# ---------------------------------------------------------------------------

XHS_ID_PATTERN = re.compile(r"(?:discovery/item/|explore/)([A-Za-z0-9]+)")
X_ID_PATTERN = re.compile(r"(?:x\.com|twitter\.com)/[^/]+/status/(\d+)")


def is_xhs_link(url: str) -> bool:
    return "xiaohongshu.com" in url or "xhslink.com" in url


def is_x_link(url: str) -> bool:
    return bool(re.search(r"(?:x\.com|twitter\.com)/[^/]+/status/", url))


def extract_work_id(link: str) -> str:
    m = XHS_ID_PATTERN.search(link)
    return m.group(1) if m else ""


def extract_x_id(link: str) -> str:
    m = X_ID_PATTERN.search(link)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# 收集：遍历块列表，按类型归入 xhs / x / images
# 块结构与顶层回溯逻辑见 references/platform-apis.md
# ---------------------------------------------------------------------------

def find_top_toggle(blocks: list, block_id: str, page_id: str) -> str:
    """沿 parent_id 回溯到顶层 toggle_list；找不到返回块自身。"""
    by_id = {b.get("id"): b for b in blocks}
    cur = by_id.get(block_id)
    guard = 0
    while cur and guard < 50:
        guard += 1
        if cur.get("type") == "toggle_list":
            return cur.get("id")
        pid = cur.get("parent_id")
        if not pid or pid == page_id:
            break
        cur = by_id.get(pid)
    return block_id


def collect_items(blocks: list, page_id: str) -> dict:
    """返回 {'xhs': [(link, top_block_id)], 'x': [...], 'images': [(url, top_block_id)]}"""
    result = {"xhs": [], "x": [], "images": []}
    seen = {"xhs": set(), "x": set(), "images": set()}

    for b in blocks:
        btype = b.get("type", "")
        bid = b.get("id", "")
        top = find_top_toggle(blocks, bid, page_id)

        # embed 块：media.url / original_link / embed_link
        if btype == "embed":
            media = b.get("media", {})
            candidates = [media.get("url", "") if isinstance(media, dict) else "",
                          b.get("original_link", ""), b.get("embed_link", "")]
            for url in candidates:
                if url and is_xhs_link(url) and url not in seen["xhs"]:
                    seen["xhs"].add(url)
                    result["xhs"].append((url, top))
                elif url and is_x_link(url) and url not in seen["x"]:
                    seen["x"].add(url)
                    result["x"].append((url, top))

        # text 块：content[].link
        if btype == "text":
            for c in (b.get("content") or []):
                if isinstance(c, dict) and c.get("link"):
                    lk = c["link"]
                    if is_xhs_link(lk) and lk not in seen["xhs"]:
                        seen["xhs"].add(lk)
                        result["xhs"].append((lk, top))
                    elif is_x_link(lk) and lk not in seen["x"]:
                        seen["x"].add(lk)
                        result["x"].append((lk, top))

        # image 块：media.download_url
        if btype == "image":
            media = b.get("media", {})
            url = media.get("download_url", "") if isinstance(media, dict) else ""
            if url and url not in seen["images"]:
                seen["images"].add(url)
                result["images"].append((url, top))

    return result


# ---------------------------------------------------------------------------
# 入库 Eagle（关键：解析 successCount 确认成功，返回 (成功数, 总数)）
# ---------------------------------------------------------------------------

def _find_key(obj, key: str):
    """递归查找嵌套 dict 里的 key，找不到返回 None。"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def import_to_eagle(eagle_url: str, files: list, tags: list, source_url: str):
    """入库；返回 (successCount, totalCount)。中文信息只放 annotation，不放 name。"""
    if not files:
        return (0, 0)
    items = []
    for fp in files:
        item = {"source": {"type": "path", "path": fp}, "tags": tags}
        if source_url:
            item["annotation"] = source_url
        items.append(item)
    result = mcp_call(eagle_url, "", "item_add", {"items": items, "tags": tags})
    ok = _find_key(result, "successCount")
    total = _find_key(result, "totalCount")
    if ok is None or total is None:
        # 解析不出时保守返回 0，避免误删源
        log("  无法从 Eagle 返回解析 successCount，保守按失败处理")
        return (0, len(files))
    return (int(ok), int(total))


def delete_source_block(wolai_url: str, token: str, block_id: str):
    return mcp_call(wolai_url, token, "delete_block", {"block_id": block_id})


# ---------------------------------------------------------------------------
# 下载引擎（子进程调用，独立临时目录；关闭下载器内置去重）
# ---------------------------------------------------------------------------

def _collect_files(directory: Path) -> set:
    exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov"}
    return {str(p) for p in directory.rglob("*") if p.suffix.lower() in exts}


def download_xhs(link: str, image_format: str, work_dir: Path, xhs_main_py: str) -> list:
    """子进程调用 XHS-Downloader，下载到独立临时目录，返回本次新增文件。"""
    import subprocess
    before = _collect_files(work_dir)
    cmd = [sys.executable, xhs_main_py,
           "--url", link,
           "--work_path", str(work_dir),
           "--folder_name", "",
           "--image_format", image_format,
           "--download_record", "false"]  # 关闭内置去重，用 state.json 去重
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=300, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            log(f"  ✗ 下载器返回码 {r.returncode}: {(r.stderr or '')[-200:]}")
    except Exception as e:
        log(f"  下载异常: {e}")
        return []
    after = _collect_files(work_dir)
    return sorted(after - before)


def download_x_tweet(link: str, auth_token: str, work_dir: Path) -> list:
    """gallery-dl 下载单条推文（需 auth_token）。返回新增文件。"""
    import subprocess
    if not auth_token:
        log("  ✗ 未配置 auth_token，无法下载 X")
        return []
    before = _collect_files(work_dir)
    cookie_file = BASE_DIR / "gallery-dl-cookies.json"
    with open(cookie_file, "w", encoding="utf-8") as f:
        json.dump({"extractor": {"twitter": {"cookies": {"auth_token": auth_token}}}}, f)
    try:
        subprocess.run(["gallery-dl", "-d", str(work_dir), "--cookies", str(cookie_file), link],
                       capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
    except Exception as e:
        log(f"  X 下载异常: {e}")
        return []
    after = _collect_files(work_dir)
    return sorted(after - before)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只识别不下载不删")
    ap.add_argument("--no-delete", action="store_true", help="下载入库但不删源")
    args = ap.parse_args()

    cfg = load_config()
    wolai = cfg.get("wolai", {})
    eagle = cfg.get("eagle", {})
    xhs = cfg.get("xhs", {})
    x = cfg.get("x", {})

    wolai_url = wolai.get("mcp_url")
    token = os.environ.get("WOLAI_TOKEN", wolai.get("token", ""))
    page_id = wolai.get("page_id")
    eagle_url = eagle.get("mcp_url")

    if not token or not page_id:
        log("请配置 wolai.token 与 wolai.page_id（token 也可用环境变量 WOLAI_TOKEN）")
        sys.exit(1)

    log("读取剪藏页面 ...")
    blocks_resp = mcp_call(wolai_url, token, "get_page_blocks", {"page_id": page_id})
    blocks = blocks_resp.get("data", {}).get("data", []) if isinstance(blocks_resp, dict) else []
    items = collect_items(blocks, page_id)
    log(f"提取到 {len(items['xhs'])} 小红书, {len(items['x'])} X, {len(items['images'])} 图片")

    if args.dry_run:
        for lk, top in items["xhs"]:
            print(f"  [小红书] 块={top} {lk}")
        for lk, top in items["x"]:
            print(f"  [X] 块={top} {lk}")
        for url, top in items["images"]:
            print(f"  [图片] 块={top} {url[:80]}")
        return

    state = load_state()
    done = set(state.get("done_ids", []))

    work_dir = Path(cfg.get("download", {}).get("temp_dir", str(BASE_DIR / "downloads")))
    work_dir.mkdir(parents=True, exist_ok=True)

    new_done = []
    tags = eagle.get("tags", ["剪藏"])

    # 小红书
    for lk, top in items["xhs"]:
        wid = extract_work_id(lk)
        if wid and wid in done:
            log(f"跳过已处理: {wid}")
            continue
        files = download_xhs(lk, cfg.get("download", {}).get("image_format", "PNG"),
                             work_dir, xhs.get("main_py", ""))
        if not files:
            log(f"  无文件产出，保留源")
            continue
        ok, total = import_to_eagle(eagle_url, files, tags, lk)
        if ok >= total:
            log(f"  入库成功 {ok}/{total}，删源块 {top}")
            if not args.no_delete and top:
                delete_source_block(wolai_url, token, top)
            new_done.append(wid)
        else:
            log(f"  仅入库 {ok}/{total}，保留源待重试")
        time.sleep(1)

    # X
    for lk, top in items["x"]:
        xid = extract_x_id(lk)
        if xid and xid in done:
            log(f"跳过已处理 X: {xid}")
            continue
        files = download_x_tweet(lk, x.get("auth_token", ""), work_dir)
        if not files:
            log(f"  无文件产出，保留源")
            continue
        ok, total = import_to_eagle(eagle_url, files, x.get("tags", ["X"]), lk)
        if ok >= total:
            log(f"  入库成功 {ok}/{total}，删源块 {top}")
            if not args.no_delete and top:
                delete_source_block(wolai_url, token, top)
            new_done.append(xid)
        else:
            log(f"  仅入库 {ok}/{total}，保留源待重试")
        time.sleep(1)

    done.update(new_done)
    state["done_ids"] = list(done)
    save_state(state)
    log(f"完成。本次新增处理 {len(new_done)} 个。")


if __name__ == "__main__":
    main()
