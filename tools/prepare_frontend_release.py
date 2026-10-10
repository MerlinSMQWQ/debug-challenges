"""Prepare only four public assets and the two reviewed Next bootstrap sources."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

PUBLIC = {'app.js', 'content-source.mjs', 'snapshot.json', 'handbook.md'}
BOOTSTRAP = {'site-client.tsx', 'release-loader.mjs'}
ROOT = Path(__file__).resolve().parents[1]


def prepare(artifact, output, revision, source=ROOT / 'website/next'):
    if not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Use a committed release SHA')
    artifact, output, source = Path(artifact), Path(output), Path(source)
    if artifact.is_symlink() or source.is_symlink():
        raise ValueError('Source directories cannot be symlinks')
    if {p.name for p in artifact.iterdir()} != PUBLIC:
        raise ValueError('Public artifact must contain exactly the four allowed files')
    snapshot = json.loads((artifact / 'snapshot.json').read_text())
    if snapshot.get('commit') != revision:
        raise ValueError('Snapshot and release SHA differ')
    for name in snapshot['documents']:
        if not re.fullmatch(r'Debug 挑战赛手册\.md|challenges/\d{4}-\d{2}-\d{2}/(?:README\.md|docs/(?:pre_read|operations|rules|incident|validation)\.md|evidence/initial/README\.md)', name):
            raise ValueError('Unexpected public document')
    if output.exists():
        raise ValueError('Release staging directory must be new')
    # Validate everything before creating any output, including source symlinks.
    pairs = [(artifact / name, 'public/' + name) for name in sorted(PUBLIC)]
    pairs += [(artifact / name, 'public/releases/' + revision + '/' + name) for name in sorted(PUBLIC)]
    pairs += [(source / name, 'next-bootstrap/' + name) for name in sorted(BOOTSTRAP)]
    if any(p.is_symlink() or not p.is_file() for p, _ in pairs):
        raise ValueError('Only regular source files may be packaged')
    files = {}
    for path, name in pairs:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        files[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = {'commit': revision, 'files': files, 'immutable_directory': 'public/releases/' + revision,
                'activation_file': 'public/snapshot.json', 'public_files_per_release': 4}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ref', required=True)
    args = parser.parse_args()
    result = prepare(args.artifact, args.output, args.ref)
    print('Prepared immutable frontend release:', result['commit'], len(result['files']), 'allowlisted files')
