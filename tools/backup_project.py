"""Make a private, verifiable source backup outside this checkout. No credentials or DB."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".local", ".aws", ".ssh", ".codex", "node_modules", ".next",
            "__pycache__", "runtime", "dist", "backups", "debug-backups", "data-private"}
SAFE_SUFFIXES = {".md", ".py", ".js", ".mjs", ".ts", ".tsx", ".json", ".csv", ".yaml", ".yml",
                 ".toml", ".sql", ".css", ".svg", ".txt", ".patch", ".log", ".sha256"}
SAFE_NAMES = {"Dockerfile", ".dockerignore", ".gitignore", ".gitattributes"}


def backup(destination):
    destination = Path(destination).resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Backup destination must be outside the Git checkout")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = destination / stamp
    target.mkdir(parents=True, mode=0o700)
    files = {}
    with tarfile.open(target / "project-source.tar.gz", "x:gz") as archive:
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if set(relative.parts) & EXCLUDED or path.is_symlink() or not path.is_file():
                continue
            if path.name.startswith(".env") or path.name == ".initial-owner.json":
                continue
            if path.suffix not in SAFE_SUFFIXES and path.name not in SAFE_NAMES:
                continue
            if any(token in path.name.lower() for token in ("private-key", "credential", ".token", ".sqlite", ".pem")):
                continue
            files[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
            archive.add(path, arcname=str(relative), recursive=False)
    with tarfile.open(target / "project-source.tar.gz") as archive:
        for member in archive.getmembers():
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == files[member.name]
    result = subprocess.run(["git", "bundle", "create", str(target / "history.bundle"), "--all"],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    subprocess.run(["git", "bundle", "verify", str(target / "history.bundle")], cwd=ROOT,
                   capture_output=True, text=True, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)
    manifest = {"head": head, "status": status, "files": files,
                "scope": "source, untracked source, ignored organizer material, and Git history",
                "excluded": "databases, env, credentials, keys, dependencies and build/runtime outputs",
                "verified": True}
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("Verified private backup:", target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    backup(parser.parse_args().destination)
