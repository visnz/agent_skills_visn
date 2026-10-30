"""Download selected, pinned community skill files to a cache outside this repo.

This prepares instruction files; it never executes downloaded scripts or installs
global skills. The agent must READ the returned load_order before doing the task.
Python 3.9+ standard library only.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 4 * 1024 * 1024


def within(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def load_catalog():
    catalog = json.loads((ROOT / 'community-skills.json').read_text(encoding='utf-8'))
    source = catalog['source']
    if catalog.get('schema_version') != 1:
        raise ValueError('Unsupported community catalog schema')
    if not re.fullmatch(r'[0-9a-f]{40}', source['commit']):
        raise ValueError('Source must be pinned to a full Git commit SHA')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', source['repository_slug']):
        raise ValueError('Invalid GitHub repository identifier')
    names = [s['name'] for s in catalog['skills']]
    if len(names) != len(set(names)) or catalog['base_skill'] not in names:
        raise ValueError('Invalid or duplicate skill names')
    for skill in catalog['skills']:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', skill['name']):
            raise ValueError('Invalid skill name')
        if skill['entrypoint'] not in skill['files']:
            raise ValueError('Skill entrypoint is not covered by file hashes')
        for relative, digest in skill['files'].items():
            path = PurePosixPath(relative)
            if path.is_absolute() or '..' in path.parts or '\\' in relative:
                raise ValueError('Unsafe source path')
            if not relative.startswith('skills/' + skill['name'] + '/'):
                raise ValueError('File is outside its declared skill')
            if not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise ValueError('Invalid SHA-256 digest')
    if source['license_file'] != 'LICENSE' or not re.fullmatch(r'[0-9a-f]{64}', source['license_sha256']):
        raise ValueError('Invalid license record')
    return catalog


def check_cache_location(cache):
    cache = cache.expanduser().resolve()
    # Reject this skill tree and the containing checkout, including a junction target.
    if within(cache, ROOT):
        raise ValueError('Cache must be outside the personal skill directory')
    for parent in ROOT.parents:
        if (parent / '.git').exists() and within(cache, parent):
            raise ValueError('Cache must be outside the Git checkout')
    # Also avoid placing remote skills in an unrelated checkout.
    for parent in (cache, *cache.parents):
        if (parent / '.git').exists():
            raise ValueError('Cache must not be inside a Git checkout')
    return cache


def fetch_one(item, *, destination, source, offline):
    relative, digest = item
    target = destination.joinpath(*PurePosixPath(relative).parts)
    if not within(target, destination):
        raise ValueError('Resolved cache path escaped its root')
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError('Cache file differs from pinned source; inspect it before removing or replacing: ' + str(target))
        return 'cached'
    if offline:
        raise FileNotFoundError('Not cached; network required: ' + relative)
    url = f"https://raw.githubusercontent.com/{source['repository_slug']}/{source['commit']}/{relative}"
    request = Request(url, headers={'User-Agent': 'visn-blender-skill-loader/1.0'})
    with urlopen(request, timeout=20) as response:
        if response.geturl() != url:
            raise ValueError('Unexpected redirect while downloading ' + relative)
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('Remote file exceeds size limit: ' + relative)
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Remote SHA-256 mismatch: ' + relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.download-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)  # Only the temporary file created by this invocation.
    return 'downloaded'


def prepare(catalog, names, cache, offline):
    by_name = {s['name']: s for s in catalog['skills']}
    selected = list(dict.fromkeys([catalog['base_skill'], *names]))
    missing = [n for n in selected if n not in by_name]
    if missing:
        raise ValueError('Unknown skills: ' + ', '.join(missing) + '; use --list')
    cache = check_cache_location(cache)
    source = catalog['source']
    destination = cache / source['repository_slug'].replace('/', '--') / source['commit']
    files = {source['license_file']: source['license_sha256']}
    for name in selected:
        files.update(by_name[name]['files'])
    # Validate the whole existing/missing set before any network or cache mutation.
    for relative, digest in files.items():
        file = destination.joinpath(*PurePosixPath(relative).parts)
        if not within(file, destination):
            raise ValueError('Cache file escaped the expected root')
        if file.exists() and hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError('Modified cache file: ' + str(file))
        if offline and not file.exists():
            raise FileNotFoundError('Not cached in offline mode: ' + relative)
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(lambda item: fetch_one(item, destination=destination, source=source, offline=offline), files.items()))
    load_order = [str(destination / by_name[name]['entrypoint']) for name in selected]
    load_order.append(str(ROOT / 'SKILL.md'))
    return {'ok': True, 'source': source['repository'], 'commit': source['commit'],
            'cache_root': str(destination), 'skills': selected,
            'downloaded_files': statuses.count('downloaded'), 'cached_files': statuses.count('cached'),
            'load_order': load_order,
            'next_action': 'Read every load_order file in order; follow task-relevant references. No remote code has been executed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='List registered skills; no download')
    parser.add_argument('--skills', nargs='*', default=[], help='Specialist names; blender-core is always included')
    parser.add_argument('--cache-dir', type=Path, default=Path(tempfile.gettempdir()) / 'visn-agent-skills',
                        help='Writable cache outside any Git checkout (default: system temp/visn-agent-skills)')
    parser.add_argument('--offline', action='store_true', help='Verify and reuse cached files without network access')
    args = parser.parse_args()
    try:
        catalog = load_catalog()
        if args.list:
            result = {'source': catalog['source'], 'base_skill': catalog['base_skill'],
                      'skills': [{'name':s['name'], 'entrypoint':s['entrypoint']} for s in catalog['skills']]}
        else:
            result = prepare(catalog, args.skills, args.cache_dir, args.offline)
    except Exception as error:
        print(json.dumps({'ok': False, 'error': f'{type(error).__name__}: {error}'}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
