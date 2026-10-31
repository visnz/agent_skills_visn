"""Synthetic regression fixtures; never reads real exports or the user's blog."""
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'flomo_to_moment.py'
if not SCRIPT.exists():
    SCRIPT = HERE.parent / 'scripts/flomo_to_moment.py'
spec = importlib.util.spec_from_file_location('flomo_sync', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='visn-flomo-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'source').mkdir()

    def package(self, entries, name='export.zip'):
        file = self.root/name
        with zipfile.ZipFile(file, 'w') as z:
            for key, content in entries.items():
                z.writestr(key, content)
        return file

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.suffix != '.zip'}

    def test_preview_apply_rerun_update_and_no_delete(self):
        entries = {'202610311200_1.md': '【Title: #safe】\n正文\n#tag #索引/test\n# Markdown heading\n![x](images/same.png)\n[日期](https://flomoapp.com/mine/?memo_id=one)',
                   '202610311201_2.md': 'another', 'images/same.png': b'fake image data'}
        z = self.package(entries)
        before = self.snapshot()
        self.assertEqual(mod.sync(self.root, z)['新增'], ['202610311200','202610311201'])
        self.assertEqual(self.snapshot(), before)
        mod.sync(self.root,z,True)
        post = self.root/'source/_posts/moment/202610311200.md'
        text = post.read_text(encoding='utf-8')
        self.assertIn('title: "Title: #safe"', text)
        self.assertIn('# Markdown heading', text)
        self.assertNotIn('#tag',text)
        self.assertNotIn('memo_id=',text)
        self.assertEqual(len(list((self.root/'source/assets/moment').glob('*'))),1)
        self.assertEqual(len(mod.sync(self.root,z,True)['未变']),2)
        entries['202610311200_1.md'] = entries['202610311200_1.md'].replace('正文','new body')
        del entries['202610311201_2.md']
        z = self.package(entries)
        self.assertEqual(mod.sync(self.root,z,True)['更新'],['202610311200'])
        self.assertTrue((post.parent/'202610311201.md').exists())
        self.assertTrue(list((self.root/'moments_update/flomo-backups').rglob('202610311200.md')))

    def test_cli_preview_and_failure_status(self):
        z = self.package({'202610311200.md':'cli sample'})
        command = [sys.executable, '-X', 'utf8', '-B', str(SCRIPT), str(self.root), '--zip', str(z)]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['mode'], 'preview')
        self.assertFalse((self.root/'moments_update').exists())
        z = self.package({'202610311200.md':'![missing](images/x.png)'})
        result = subprocess.run(command + ['--apply'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root/'source/_posts').exists())

    def test_manual_edit_stops_entire_batch(self):
        z = self.package({'202610311200.md':'original'})
        mod.sync(self.root,z,True)
        p = self.root/'source/_posts/moment/202610311200.md'
        p.write_text('manual',encoding='utf-8')
        z = self.package({'202610311200.md':'changed','202610311201.md':'new post'})
        before = self.snapshot()
        with self.assertRaises(ValueError): mod.sync(self.root,z,True)
        self.assertEqual(self.snapshot(),before)

    def test_unmanaged_post_and_identical_adoption(self):
        z = self.package({'202610311200.md':'hello'})
        p = self.root/'source/_posts/moment/202610311200.md'
        p.parent.mkdir(parents=True)
        p.write_text('handwritten',encoding='utf-8')
        with self.assertRaises(ValueError): mod.sync(self.root,z,True)
        expected = mod.load_zip(z)[0]['post']
        p.write_bytes(expected)
        self.assertEqual(mod.sync(self.root,z,True)['接管'], ['202610311200'])

    def test_invalid_packages_write_nothing(self):
        for entries in [
            {'202610311200_1.md':'one','202610311200_2.md':'two'},
            {'202610311200.md':'![missing](images/x.png)'},
            {'202613311200.md':'invalid date'},
            {'../202610311200.md':'traversal'},
            {'202610311200.md':'![x](images/../../secret.png)'},
            {'202610311200.md':'![x](images/space name.png)'},
        ]:
            with self.subTest(entries=list(entries)):
                z = self.package(entries)
                before=self.snapshot()
                with self.assertRaises(ValueError): mod.sync(self.root,z,True)
                self.assertEqual(self.snapshot(),before)

    def test_multiple_packages_require_selection(self):
        folder = self.root/'moments_update/flomo_fetch'
        folder.mkdir(parents=True)
        self.package({'202610311200.md':'one'},'moments_update/flomo_fetch/a.zip')
        z = self.package({'202610311200.md':'two'},'moments_update/flomo_fetch/b.zip')
        with self.assertRaises(ValueError): mod.sync(self.root)
        self.assertEqual(len(mod.sync(self.root,z)['新增']),1)

    def test_first_line_title_and_yaml_strings(self):
        memo = mod.parse_memo('202610311200.md', 'first\n【not title】\n'.encode(),{})
        self.assertNotIn(b'title:',memo['post'])
        self.assertIn('【not title】'.encode(),memo['post'])
        for value in ['#start','a: b','true','[array]','"quote"','反斜线\\text']:
            self.assertEqual(json.loads(mod.scalar(value)),value)

    def test_nested_exports_and_same_image_names(self):
        z = self.package({'a/202610311200.md':'![x](images/same.png)\n![remote](https://example.com/x.png)',
                          'a/images/same.png':b'a', 'b/202610311201.md':'![x](images/same.png)',
                          'b/images/same.png':b'b'})
        mod.sync(self.root,z,True)
        self.assertEqual(len(list((self.root/'source/assets/moment').glob('*'))),2)

    def test_identity_collision_across_runs_and_deleted_managed_file(self):
        z = self.package({'202610311200.md':'one\n[link](https://flomoapp.com/mine/?memo_id=one)'})
        mod.sync(self.root,z,True)
        z = self.package({'202610311200.md':'two\n[link](https://flomoapp.com/mine/?memo_id=two)'})
        with self.assertRaises(ValueError): mod.sync(self.root,z,True)
        z = self.package({'202610311200.md':'one\n[link](https://flomoapp.com/mine/?memo_id=one)'})
        (self.root/'source/_posts/moment/202610311200.md').unlink()
        with self.assertRaises(ValueError): mod.sync(self.root,z,True)


if __name__ == '__main__':
    unittest.main()
