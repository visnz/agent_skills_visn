"""Synthetic regression tests; no real chat data or external dependencies."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'clean_corpus.py'
if not SCRIPT.exists():
    SCRIPT = HERE.parent / 'scripts' / 'clean_corpus.py'
spec = importlib.util.spec_from_file_location('corpus', SCRIPT)
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)


class CorpusTests(unittest.TestCase):
    def test_unknown_or_identical_roles_rejected(self):
        with self.assertRaises(ValueError):
            corpus.read_messages(['[2026-10-31 10:00:00] [Third] text'], 'A', 'B')
        with self.assertRaises(ValueError):
            corpus.read_messages([], 'A', 'A')

    def test_multiline_gap_and_filtered_barrier(self):
        lines = ['[2026-10-31 10:00:00] [A] first\n', 'second\n',
                 '[2026-10-31 10:01:00] [B] reply\n',
                 '[2026-10-31 12:00:00] [B] later\n',
                 '[2026-10-31 12:01:00] [A] question\n',
                 '[2026-10-31 12:02:00] [B] [Image]\n',
                 '[2026-10-31 12:03:00] [B] after image\n']
        messages, stats = corpus.read_messages(lines, 'A', 'B')
        self.assertEqual(messages[0]['content'], 'first\nsecond')
        self.assertEqual(stats['continuation_lines'], 1)
        self.assertEqual(stats['filtered_records'], 1)
        turns = corpus.build_turns(messages, 30)
        self.assertNotEqual(turns[1]['session'], turns[2]['session'])
        self.assertNotEqual(turns[3]['session'], turns[4]['session'])

    def test_malformed_and_out_of_order_rejected(self):
        for lines in [['unparsed preface'], ['[2026-10-31 10:00:00] [A] hi', '[2026-10-30 10:00:00] [B] earlier'],
                      ['[2026-10-31 bad] broken']]:
            with self.assertRaises(ValueError):
                corpus.read_messages(lines, 'A', 'B')

    def test_cli_outputs_and_failure_no_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input.txt'
            source.write_text('[2026-10-31 10:00:00] [A] first\nsecond\n[2026-10-31 10:01:00] [B] reply\n[2026-10-31 12:00:00] [A] unpaired\n', encoding='utf-8-sig')
            command = [sys.executable, '-B', str(SCRIPT), str(source), '--a', 'A', '--b', 'B', '--out', str(root/'out')]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((root/'out'/'chat_classified.json').read_text(encoding='utf-8'))
            self.assertEqual(data['stats']['pairs'], 1)
            self.assertEqual(data['stats']['unpaired_turns'], 1)
            pair = next(iter(data['scenes'].values()))[0]
            self.assertEqual(pair['user'], 'first\nsecond')
            self.assertEqual(pair['source_lines'], [1, 3])
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            source.write_text('[2026-10-31 10:00:00] [Third] unknown', encoding='utf-8')
            command[-1] = str(root/'bad')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((root/'bad').exists())


if __name__ == '__main__':
    unittest.main()
