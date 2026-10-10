"""Verify CRC, public boundaries, source bytes and standalone CLI help. No containers."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify(directory, unpack=None):
    results = []
    for archive in sorted(Path(directory).glob('debug-challenge-*.zip')):
        date = re.fullmatch(r'debug-challenge-(\d{4}-\d{2}-\d{2})\.zip', archive.name).group(1)
        prefix = 'debug-challenge-' + date
        challenge_prefix = prefix + '/challenges/' + date + '/'
        with zipfile.ZipFile(archive) as zipped:
            assert zipped.testzip() is None, 'ZIP CRC failure'
            names = zipped.namelist()
            assert len(names) == len(set(names)) and len(names) <= 260
            for item in zipped.infolist():
                path = PurePosixPath(item.filename)
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                assert ((item.external_attr >> 16) & 0o170000) != 0o120000, 'symlink in ZIP'
                assert not re.fullmatch(r'(agents(?:\..+)?|claude|gemini|codex|skill|copilot(?:-instructions)?|.*\.instructions)\.md',path.name,re.I), 'maintainer instructions in ZIP'
                body = zipped.read(item)
                if item.filename.startswith(challenge_prefix):
                    relative = item.filename[len(challenge_prefix):]
                    assert not re.search(r'(organizer|ground_truth|reference|credential|password|account|submission|score|secret|solution)',relative,re.I)
                    assert not relative.startswith(('.env','.git/','runtime/','var/','notes/'))
                    assert body == (ROOT / 'challenges' / date / relative).read_bytes(), relative
                else:
                    assert item.filename in [prefix+'/README.md',prefix+'/Debug 挑战赛手册.md']
                    if item.filename != prefix+'/README.md': assert body == (ROOT/path.name).read_bytes()
            with tempfile.TemporaryDirectory() as temporary:
                target = Path(unpack) if unpack else Path(temporary)
                target.mkdir(parents=True,exist_ok=True)
                zipped.extractall(target)
                challenge = target / prefix / 'challenges' / date
                assert (challenge/'README.md').is_file() and (challenge/'compose.yaml').is_file()
                for source in challenge.rglob('*.py'): ast.parse(source.read_bytes(),filename=str(source))
                docker = (challenge/'Dockerfile').read_text()
                entry = json.loads(re.search(r'^ENTRYPOINT (\[.*\])$',docker,re.M).group(1))
                assert entry[0] == 'python' and (challenge/entry[1]).is_file()
                result = subprocess.run([sys.executable,*entry[1:],'--help'],cwd=challenge,
                                        capture_output=True,text=True,timeout=5)
                assert result.returncode == 0 and 'usage:' in result.stdout
                fixture = challenge/'tests/fixtures.sha256.json'
                if fixture.is_file():
                    for path,digest in json.loads(fixture.read_text()).items():
                        assert hashlib.sha256((challenge/path).read_bytes()).hexdigest() == digest
                results.append({'date':date,'files':len(names),'bytes':archive.stat().st_size,
                                'crc':'ok','source_bytes':'exact','standalone_help':'passed',
                                'container':'requires exact-SHA GitHub Actions'})
    assert results, 'No packages found'
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True)
    parser.add_argument('--unpack')
    args = parser.parse_args()
    print(json.dumps(verify(args.directory,args.unpack),ensure_ascii=False,indent=2))
