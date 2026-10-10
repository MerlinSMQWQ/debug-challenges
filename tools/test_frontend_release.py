import json
from pathlib import Path
import tempfile
import unittest
from prepare_frontend_release import prepare, PUBLIC


class FrontendRelease(unittest.TestCase):
    def fixture(self, root, sha):
        root.mkdir()
        for name in PUBLIC:
            (root/name).write_text('public content')
        (root/'snapshot.json').write_text(json.dumps({'commit':sha,'documents':{'challenges/2026-10-10/README.md':'public'}}))

    def test_public_bytes_are_pinned_and_existing_release_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sha='b'*40;self.fixture(root/'input',sha)
            result=prepare(root/'input',root/'output',sha)
            self.assertEqual(result['activation_file'],'public/snapshot.json')
            self.assertEqual(len(result['files']),10)
            for name in PUBLIC:
                self.assertEqual((root/'output/public'/name).read_bytes(),(root/'output/public/releases'/sha/name).read_bytes())
            with self.assertRaises(ValueError):prepare(root/'input',root/'output',sha)

    def test_private_or_instruction_files_and_mixed_snapshot_fail_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sha='b'*40;self.fixture(root/'input',sha)
            (root/'input/AGENTS.md').write_text('private instructions')
            with self.assertRaises(ValueError):prepare(root/'input',root/'output',sha)
            (root/'input/AGENTS.md').unlink()
            for docs in [{'organizer/GROUND_TRUTH.md':'private'},{'challenges/2026-10-10/docs/agents.md':'instructions'}]:
                (root/'input/snapshot.json').write_text(json.dumps({'commit':sha,'documents':docs}))
                with self.assertRaises(ValueError):prepare(root/'input',root/'output',sha)
            self.assertFalse((root/'output').exists())

    def test_revision_and_symlink_cannot_redirect_the_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sha='b'*40;self.fixture(root/'input',sha)
            with self.assertRaises(ValueError):prepare(root/'input',root/'output','main')
            with self.assertRaises(ValueError):prepare(root/'input',root/'output','c'*40)
            (root/'outside').write_text('private')
            (root/'input/handbook.md').unlink();(root/'input/handbook.md').symlink_to(root/'outside')
            with self.assertRaises(ValueError):prepare(root/'input',root/'output',sha)


if __name__ == '__main__':unittest.main()
