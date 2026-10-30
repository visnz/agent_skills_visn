#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flomo_to_moment.py — 从 flomo 导出 zip 生成 Hexo「铭记」(moment) 说说。

用法：
    1. 把 flomo 导出的 zip 放到项目的 moments_update/flomo_fetch/ 下；
    2. 运行 `python flomo_to_moment.py <项目根路径>`。

行为：
    - 解压 zip 到临时目录；
    - 解析每条 memo，生成 source/_posts/moment/YYYYMMDDHHMM.md；
    - 提取【标题】、清理 flomo 标签行 / 原文链接、搬运图片；
    - 差异化更新：只做新增与覆盖更新，不执行删除（删除请手动处理）。
"""

import os
import re
import sys
import shutil
import zipfile
import datetime

# 保证 Windows 控制台能正常输出中文
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- 路径：项目根路径用命令行参数传入，或默认当前目录 ----
PROJECT_ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
FLOMO_DIR = os.path.join(PROJECT_ROOT, 'moments_update', 'flomo_fetch')
POSTS_DIR = os.path.join(PROJECT_ROOT, 'source', '_posts', 'moment')
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'source', 'assets', 'moment')
TEMP_DIR = os.path.join(FLOMO_DIR, 'extracted')

LOG_FILE = os.path.join(PROJECT_ROOT, 'moments_update', 'flomo_to_moment.log')


class _Tee:
    """把 print 输出同时写到控制台和日志文件。"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
                st.flush()
            except Exception:
                pass

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


def filename_to_date(name):
    """YYYYMMDDHHMM_序号.md -> 'YYYY-MM-DD HH:MM:00'；不匹配返回 None。"""
    m = re.match(r'^(\d{12})(?:_\d+)?\.md$', name)
    if not m:
        return None
    ts = m.group(1)
    return '{}-{}-{} {}:{}:00'.format(ts[0:4], ts[4:6], ts[6:8], ts[8:10], ts[10:12])


def yaml_scalar(s):
    """把字符串安全地写成 YAML 标量：一般用纯文本，含特殊字符时才加引号。"""
    if s != s.strip() or '\n' in s or '"' in s or "'" in s:
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


def parse_memo(md_path, image_dir):
    """解析单个 flomo md 文件，返回 memo 字典；无法识别时返回 None。"""
    date = filename_to_date(os.path.basename(md_path))
    if not date:
        return None

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    # 1. 提取【标题】（只看第一个非空行）
    title = None
    title_idx = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        m = re.match(r'^【(.+)】$', s)
        if m:
            title = m.group(1)
            title_idx = i
        break

    # 2. 清理：删除标题行、flomo 标签行、原文链接行，其余保留（含空行）
    clean = []
    for i, line in enumerate(lines):
        if i == title_idx:
            continue
        s = line.strip()
        if not s:
            clean.append('')
            continue
        if re.match(r'^#\S', s):  # flomo 标签行（# 后无空格）
            continue
        if re.match(r'^\[[^\]]*\]\(https://flomoapp\.com/', s):  # 原文链接
            continue
        clean.append(line)

    # 3. 处理图片引用：改写路径 + 收集 photos
    photos = []

    def repl(m):
        fname = os.path.basename(m.group(1))
        photos.append('/assets/moment/' + fname)
        return '![](/assets/moment/{})'.format(fname)

    clean = [re.sub(r'!\[[^\]]*\]\((images/[^)]+)\)', repl, l) for l in clean]

    # 4. 压缩连续空行、去掉首尾空行
    body = re.sub(r'\n{3,}', '\n\n', '\n'.join(clean)).strip()

    # 5. 复制图片到 source/assets/moment/
    for p in photos:
        fname = os.path.basename(p)
        src = os.path.join(image_dir, fname)
        dst = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(src):
            os.makedirs(ASSETS_DIR, exist_ok=True)
            shutil.copy2(src, dst)

    ts = date.replace('-', '').replace(':', '').replace(' ', '')[:12]
    return {'ts': ts, 'date': date, 'title': title, 'photos': photos, 'body': body}


def build_post(memo):
    """根据 memo 生成完整帖子内容（front-matter + 正文）。"""
    lines = ['---', 'date: ' + memo['date'], 'type: moment']
    if memo['title']:
        lines.append('title: ' + yaml_scalar(memo['title']))
    if memo['photos']:
        lines.append('photos:')
        for p in memo['photos']:
            lines.append('  - ' + p)
    lines.append('---')
    lines.append('')
    if memo['body']:
        lines.append(memo['body'])
    return '\n'.join(lines) + '\n'


def read_existing():
    """读取现有说说，返回 {时间戳: 文件内容}。"""
    existing = {}
    if not os.path.isdir(POSTS_DIR):
        return existing
    for name in os.listdir(POSTS_DIR):
        if not name.endswith('.md'):
            continue
        ts = name[:-3]
        if not re.match(r'^\d{12}$', ts):
            continue
        with open(os.path.join(POSTS_DIR, name), 'r', encoding='utf-8') as f:
            existing[ts] = f.read()
    return existing


def main():
    """入口：记录运行时间到日志，并捕获异常。"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('\n' + '=' * 60 + '\n')
            f.write('运行时间：{}\n'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            f.write('=' * 60 + '\n')
    except Exception:
        pass

    log_stream = None
    original_stdout = sys.stdout
    try:
        log_stream = open(LOG_FILE, 'a', encoding='utf-8')
        sys.stdout = _Tee(original_stdout, log_stream)
        return _run()
    except Exception:
        import traceback
        traceback.print_exc()
        return 1
    finally:
        sys.stdout = original_stdout
        if log_stream:
            log_stream.close()


def _run():
    print('=' * 50)
    print('flomo -> moment 说说同步')
    print('=' * 50)

    # 1. 找 zip
    zip_path = None
    if os.path.isdir(FLOMO_DIR):
        zips = sorted(f for f in os.listdir(FLOMO_DIR) if f.lower().endswith('.zip'))
        if zips:
            zip_path = os.path.join(FLOMO_DIR, zips[0])
            if len(zips) > 1:
                print('发现多个 zip，使用第一个：{}'.format(zips[0]))
    if not zip_path:
        print('错误：{} 下未找到 zip 文件'.format(FLOMO_DIR))
        return 1

    print('解压：{}'.format(os.path.basename(zip_path)))

    # 2. 解压
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(TEMP_DIR)

    image_dir = os.path.join(TEMP_DIR, 'images')

    # 3. 解析每条 memo
    memos = {}
    for f in os.listdir(TEMP_DIR):
        if f.endswith('.md'):
            memo = parse_memo(os.path.join(TEMP_DIR, f), image_dir)
            if memo:
                if memo['ts'] in memos:
                    print('警告：时间戳 {} 有多条 memo，后者覆盖前者'.format(memo['ts']))
                memos[memo['ts']] = memo

    if not memos:
        print('未解析到任何 memo')
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        return 1

    existing = read_existing()

    added, updated, unchanged = [], [], []

    # 4. 新增 / 更新（只新增和覆盖更新，不删除）
    for ts in sorted(memos):
        memo = memos[ts]
        new_content = build_post(memo)
        path = os.path.join(POSTS_DIR, ts + '.md')
        if ts not in existing:
            os.makedirs(POSTS_DIR, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            added.append(ts)
        elif existing[ts] != new_content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated.append(ts)
        else:
            unchanged.append(ts)

    # 5. 清理临时目录
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    # 6. 报告
    print()
    print('-' * 50)
    print('同步结果：')
    print('  新增 {} 条：{}'.format(len(added), ', '.join(added) if added else '无'))
    print('  更新 {} 条：{}'.format(len(updated), ', '.join(updated) if updated else '无'))
    print('  未变 {} 条：{}'.format(len(unchanged), ', '.join(unchanged) if unchanged else '无'))
    print('-' * 50)
    print('完成。预览：npm run server，访问 http://localhost:4000/moment/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
