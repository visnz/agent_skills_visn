#!/usr/bin/env python3
"""Sync a supported flomo Markdown ZIP into this Hexo blog. Preview by default.

python flomo_to_moment.py PROJECT [--zip EXPORT.zip] [--apply]
Only standard library. Does not extract ZIPs, delete posts, commit, or publish.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from urllib.parse import parse_qs, quote, unquote, urlparse
import uuid
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scalar(value):
    # A JSON double-quoted string is also a YAML string scalar.
    return json.dumps(value, ensure_ascii=False)


def safe_member(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or p.is_absolute() or '..' in p.parts or ':' in name:
        raise ValueError('不支持或不安全的 ZIP 路径：' + name)
    return p


def local(root, relative):
    p = root / relative
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('目标路径超出项目：' + relative)
    # Refuse links even when they point elsewhere inside the project.
    for item in (p, *p.parents):
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise ValueError('目标路径包含链接：' + relative)
    return p


def parse_memo(name, data, members):
    match = re.fullmatch(r'(\d{12})(?:_\d+)?\.md', PurePosixPath(name).name)
    if not match:
        raise ValueError('不支持的 memo 文件名：' + name)
    ts = match[1]
    date = datetime.strptime(ts, '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:00')
    lines = data.decode('utf-8-sig').splitlines()
    title, title_index = None, None
    for i, line in enumerate(lines):
        if line.strip():
            m = re.fullmatch(r'【(.+)】', line.strip())
            if m:
                title, title_index = m[1], i
            break
    links = []
    for line in lines:
        m = re.fullmatch(r'\[[^\]]*\]\((https://flomoapp\.com/[^)]+)\)', line.strip())
        if m:
            ids = parse_qs(urlparse(m[1]).query).get('memo_id', [])
            if ids:
                links.append(ids[0])
    if len(set(links)) > 1:
        raise ValueError('一条 memo 含多个原文身份：' + name)
    key = 'memo:' + links[0] if links else 'minute:' + ts
    photos, assets = [], {}

    def image(m):
        raw = m[1]
        if re.match(r'^(?:[a-z][\w+.-]*:|//)', raw, re.I):
            return m[0]  # Remote images are kept, never fetched.
        decoded = unquote(raw)
        member = str(safe_member(str(PurePosixPath(name).parent / decoded)))
        if member not in members:
            raise ValueError('图片缺失：' + member)
        content = members[member]
        ext = PurePosixPath(member).suffix.lower()
        if ext not in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.svg'}:
            raise ValueError('不支持的本地图片：' + member)
        # Content-addressed names avoid overwriting an unrelated same-name image.
        relative = 'source/assets/moment/' + digest(content) + ext
        assets[relative] = content
        url = '/assets/moment/' + quote(PurePosixPath(relative).name)
        if url not in photos:
            photos.append(url)
        return '![](' + url + ')'

    last = max((i for i, s in enumerate(lines) if s.strip()), default=-1)
    clean = []
    for i, line in enumerate(lines):
        s = line.strip()
        if i == title_index or re.fullmatch(r'(?:#\S+\s*)+', s):
            continue
        if i == last and re.fullmatch(r'\[[^\]]*\]\(https://flomoapp\.com/[^)]+\)', s):
            continue
        # Only simple inline Markdown destinations are supported. Reject rather than half-convert.
        converted = re.sub(r'!\[[^\]]*\]\(([^\s()]+)\)', image, line)
        for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', converted):
            if not target.startswith('/assets/moment/') and not re.match(r'^(?:[a-z][\w+.-]*:|//)', target, re.I):
                raise ValueError('本地图片语法不受支持：' + name)
        if re.search(r'!\[[^\]]*\]\[', converted) or re.search(r'<img\b', converted, re.I):
            raise ValueError('引用式或 HTML 图片需先转为支持的内联格式：' + name)
        clean.append(converted)
    body = re.sub(r'\n{3,}', '\n\n', '\n'.join(clean)).strip()
    front = ['---', 'date: ' + date, 'type: moment']
    if title is not None:
        front.append('title: ' + scalar(title))
    if photos:
        front += ['photos:'] + ['  - ' + scalar(p) for p in photos]
    post = ('\n'.join(front) + '\n---\n\n' + body + '\n').encode('utf-8')
    return {'key': key, 'ts': ts, 'post': post, 'assets': assets, 'source': name}


def load_zip(file):
    with zipfile.ZipFile(file) as archive:
        entries = [i for i in archive.infolist() if not i.is_dir()]
        if sum(i.file_size for i in entries) > 512 * 1024 * 1024:
            raise ValueError('解压内容超过 512 MiB，需先评估规模并拆分输入')
        members = {}
        for info in entries:
            name = str(safe_member(info.filename))
            if name in members:
                raise ValueError('ZIP 内有重复路径：' + name)
            members[name] = archive.read(info)
    memos = [parse_memo(name, data, members) for name, data in members.items()
             if name.lower().endswith('.md')]
    if not memos:
        raise ValueError('未找到支持的 Markdown memo')
    if len({m['key'] for m in memos}) != len(memos):
        raise ValueError('存在重复 memo 身份，未写入')
    if len({m['ts'] for m in memos}) != len(memos):
        raise ValueError('同一分钟存在多条 memo；当前兼容命名会冲突，需先确认不同命名或迁移方案，不保留任意一条')
    return memos


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        f.write(data)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def sync(root, zip_path=None, apply=False):
    root = Path(root).resolve()
    if not (root / 'source').is_dir():
        raise ValueError('项目根目录缺少 source')
    if zip_path is None:
        choices = sorted((root / 'moments_update/flomo_fetch').glob('*.zip'))
        if len(choices) != 1:
            raise ValueError('需要恰好一个导出 ZIP，或用 --zip 明确指定输入包')
        zip_path = choices[0]
    memos = load_zip(Path(zip_path))
    state_file = local(root, 'moments_update/flomo-state.json')
    before_state = state_file.read_bytes() if state_file.exists() else None
    state = json.loads(before_state) if before_state else {'version': 1, 'records': {}, 'assets': {}}
    if state.get('version') != 1 or not isinstance(state.get('records'), dict) or not isinstance(state.get('assets'), dict):
        raise ValueError('不支持的同步状态格式')
    writes, counts = {}, {'新增': [], '更新': [], '未变': [], '接管': []}

    def plan(relative, wanted, previous_hash):
        target = local(root, relative)
        old = target.read_bytes() if target.exists() else None
        if old == wanted:
            return old
        if old is not None and (previous_hash is None or digest(old) != previous_hash):
            raise ValueError('检测到手工修改或未受管理的同名文件，未写入：' + relative)
        if old is None and previous_hash is not None:
            raise ValueError('受管理文件已被外部删除，未自动重建：' + relative)
        writes[relative] = (old, wanted)
        return old

    # Preflight *all* posts/assets; validation failure cannot partially import a batch.
    for memo in sorted(memos, key=lambda m: m['ts']):
        relative = 'source/_posts/moment/' + memo['ts'] + '.md'
        prev = state['records'].get(memo['key'])
        if any(k != memo['key'] and r['post'] == relative for k, r in state['records'].items()):
            raise ValueError('时间戳被另一 memo 身份占用，未写入：' + memo['ts'])
        if prev and prev['post'] != relative:
            raise ValueError('同一 memo 创建时间改变，需人工确认迁移')
        old = plan(relative, memo['post'], prev['hash'] if prev else None)
        kind = '新增' if old is None else '更新' if old != memo['post'] else '未变' if prev else '接管'
        counts[kind].append(memo['ts'])
        for asset, data in memo['assets'].items():
            plan(asset, data, state['assets'].get(asset))
            state['assets'][asset] = digest(data)
        state['records'][memo['key']] = {'post': relative, 'hash': digest(memo['post']), 'source': memo['source']}
    present = {m['key'] for m in memos}
    absent = sorted(k for k in state['records'] if k not in present)
    report = {'mode': 'apply' if apply else 'preview', **counts, '本次未含历史记录数': len(absent), '待写文件数': len(writes)}
    if not apply:
        return report
    # Detect intervening edits before writing. No global rollback guarantee is claimed.
    if (state_file.read_bytes() if state_file.exists() else None) != before_state:
        raise ValueError('同步状态发生并发变化')
    backup = 'moments_update/flomo-backups/' + uuid.uuid4().hex
    for relative, (old, _) in writes.items():
        target = local(root, relative)
        if (target.read_bytes() if target.exists() else None) != old:
            raise ValueError('目标在预检后发生变化：' + relative)
    for relative, (old, wanted) in writes.items():
        if old is not None:
            atomic(local(root, backup + '/' + relative), old)
        atomic(local(root, relative), wanted)
    if before_state:
        atomic(local(root, backup + '/flomo-state.json'), before_state)
    atomic(state_file, (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    log = local(root, 'moments_update/flomo_to_moment.log')
    with log.open('a', encoding='utf-8') as f:
        f.write(datetime.now().astimezone().isoformat() + ' ' + json.dumps(report, ensure_ascii=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--zip', dest='zip_path', type=Path)
    parser.add_argument('--apply', action='store_true', help='明确写入；默认只预览且不写日志或状态')
    args = parser.parse_args()
    try:
        print(json.dumps(sync(args.project, args.zip_path, args.apply), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, KeyError) as error:
        print('同步失败：' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
