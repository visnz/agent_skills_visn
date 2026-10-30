"""Use the verified local Blender addon JSON/TCP interface on an explicit port.

inspect observes state. run executes a trusted UTF-8 Python file in Blender,
after checking the exact open .blend path. No third-party Python dependencies.
"""

import argparse
import json
from pathlib import Path
import socket
import sys

MAX_RESPONSE = 32 * 1024 * 1024

INSPECT_CODE = r'''
import bpy, json
editors = []
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type != 'NODE_EDITOR':
            continue
        space = area.spaces.active
        tree = space.edit_tree
        selected = []
        if tree:
            for node in tree.nodes:
                if node.select:
                    selected.append({
                        'name': node.name, 'label': node.label,
                        'type': node.bl_idname,
                        'node_group': node.node_tree.name if node.type == 'GROUP' and node.node_tree else None,
                        'inputs': [{'name': s.name, 'identifier': s.identifier, 'linked': s.is_linked,
                                    'value': list(s.default_value) if hasattr(s, 'default_value') and hasattr(s.default_value, '__len__') and not isinstance(s.default_value, str) else getattr(s, 'default_value', None)} for s in node.inputs]
                    })
        editors.append({'screen': window.screen.name, 'tree': tree.name if tree else None,
                        'active': tree.nodes.active.name if tree and tree.nodes.active else None,
                        'selected': selected})
print(json.dumps({'file': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
                  'version': bpy.app.version_string,
                  'active_object': bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
                  'node_editors': editors,
                  'asset_libraries': [{'name': a.name, 'path': a.path} for a in bpy.context.preferences.filepaths.asset_libraries]},
                 ensure_ascii=False, default=str))
'''


def rpc(port, code, timeout):
    payload = {'type': 'execute_code', 'params': {'code': code}}
    with socket.create_connection(('127.0.0.1', port), timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(json.dumps(payload).encode('utf-8'))
        data = bytearray()
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                raise RuntimeError('Connection closed before a complete JSON response')
            data.extend(chunk)
            if len(data) > MAX_RESPONSE:
                raise RuntimeError('Response exceeds 32 MiB; request less output')
            try:
                response = json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(response, dict):
                raise RuntimeError('Unexpected addon response format')
            if response.get('status') != 'success':
                raise RuntimeError(json.dumps(response, ensure_ascii=True))
            result = response.get('result')
            if isinstance(result, dict) and result.get('executed') is False:
                raise RuntimeError(json.dumps(result, ensure_ascii=True))
            return response


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('inspect', 'run'):
        child = sub.add_parser(action)
        child.add_argument('--port', type=int, required=True)
        child.add_argument('--timeout', type=float, default=30)
        if action == 'run':
            child.add_argument('--expect-file', required=True,
                               help='Exact full path of the expected open .blend')
            child.add_argument('--code-file', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    if not 0 < args.timeout <= 60:
        parser.error('--timeout must be greater than 0 and at most 60 seconds')
    if args.action == 'run' and not Path(args.expect_file).is_absolute():
        parser.error('--expect-file must be an absolute path')
    return args


def main():
    args = parse_args()
    code = INSPECT_CODE
    if args.action == 'run':
        script = args.code_file.read_text(encoding='utf-8-sig')
        # Represent paths/code as Python literals, never as shell substitutions.
        code = (
            'import bpy, os\n'
            f'_skill_expected = {args.expect_file!r}\n'
            'if os.path.normcase(os.path.abspath(bpy.data.filepath)) != '
            'os.path.normcase(os.path.abspath(_skill_expected)):\n'
            '    raise RuntimeError("Target file mismatch: " + bpy.data.filepath)\n'
            f'exec(compile({script!r}, {str(args.code_file)!r}, "exec"))\n'
        )
    try:
        response = rpc(args.port, code, args.timeout)
    except (OSError, RuntimeError) as error:
        print(f'Blender RPC failed: {error}', file=sys.stderr)
        return 1
    # ASCII JSON keeps Windows terminals with legacy code pages usable.
    print(json.dumps(response, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
