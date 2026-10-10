import json
from pathlib import Path
import tempfile
import unittest

from build_public_content import ROOT, build


class PublicContent(unittest.TestCase):
    def fixture(self, root):
        root.joinpath('README.md').write_text('| #001 | [Demo](challenges/2026-10-10/README.md) | Python | Easy | 20 分钟 |\n')
        root.joinpath('Debug 挑战赛手册.md').write_text('# Manual\n')
        challenge = root / 'challenges/2026-10-10'
        challenge.mkdir(parents=True)
        (challenge / 'README.md').write_text('# Demo\n')
        (root / 'organizer').mkdir()
        (root / 'organizer/GROUND_TRUTH.md').write_text('NEVER_PUBLIC_SECRET')
        (root / '.env').write_text('NEVER_PUBLIC_SECRET')
        return challenge

    def test_actual_material_and_date_identity(self):
        result = build()
        self.assertEqual([(r['id'], r['date'], r['kind']) for r in result['episodes']],
                         [('#001', '2026-10-10', 'official'), ('#000', '2026-10-09', 'test')])
        self.assertEqual(result['featured']['date'], '2026-10-10')
        self.assertIn('Debug 挑战赛手册.md', result['documents'])
        self.assertFalse(any('organizer' in path for path in result['documents']))

    def test_poisoned_private_material_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            self.assertNotIn('NEVER_PUBLIC_SECRET', json.dumps(build(root)))

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); challenge = self.fixture(root)
            (challenge / 'README.md').unlink()
            (challenge / 'README.md').symlink_to(root / 'organizer/GROUND_TRUTH.md')
            with self.assertRaises(ValueError): build(root)

    def test_private_links_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); challenge = self.fixture(root)
            (challenge / 'README.md').write_text('[answer](../../organizer/GROUND_TRUTH.md)')
            with self.assertRaises(ValueError): build(root)

    def test_bad_index_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            text = (root / 'README.md').read_text()
            for modified in (text + text, text.replace('2026-10-10','2026-02-30'), text.replace(' | Python',' | Extra | Python')):
                (root / 'README.md').write_text(modified)
                with self.assertRaises(ValueError): build(root)

    def test_maintainer_instructions_cannot_be_linked_into_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); challenge = self.fixture(root)
            (challenge/'docs').mkdir()
            (challenge/'docs/agents.md').write_text('NEVER_PUBLIC_SECRET')
            (challenge/'README.md').write_text('[维护者资料](docs/agents.md)')
            with self.assertRaises(ValueError): build(root)

    def test_release_ref_and_determinism(self):
        revision = 'a' * 40
        self.assertEqual(build(revision=revision), build(revision=revision))
        with self.assertRaises(ValueError): build(revision='../../organizer')


if __name__ == '__main__':
    unittest.main()
