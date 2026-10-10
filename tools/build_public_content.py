"""Generate allowlisted public Markdown snapshots. Never traverse organizer or runtime data."""
import argparse
import datetime
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read_public(root, relative):
    path = root / relative
    if path.is_symlink() or any((root / parent).is_symlink() for parent in Path(relative).parents):
        raise ValueError("Symlinks are not public source files")
    if not path.is_file() or root.resolve() not in path.resolve().parents:
        raise ValueError("Missing or unsafe public path: " + relative)
    text = path.read_text(encoding="utf-8")
    if re.search(r'\]\([^)]*(?:organizer/|\.env|\.local/|\.sqlite|\.pem)', text, re.I):
        raise ValueError("Public document links to private material: " + relative)
    return text


def build(root=ROOT, revision="main"):
    if not re.fullmatch(r"(?:main|[a-f0-9]{40})", revision):
        raise ValueError("Use an immutable SHA for release, or main for a local draft")
    readme = read_public(root, "README.md")
    episodes, dates, ids = [], set(), set()
    for line in readme.splitlines():
        match = re.search(r"\[([^\]]+)\]\(challenges/(\d{4}-\d{2}-\d{2})/README\.md\)", line)
        if not line.strip().startswith("|") or not match:
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) != 5 or not re.fullmatch(r"#\d{3,}", cells[0]):
            raise ValueError("Index must retain five columns and a numeric display ID")
        date = datetime.date.fromisoformat(match[2]).isoformat()
        if date in dates or cells[0] in ids:
            raise ValueError("Duplicate date or display ID")
        dates.add(date); ids.add(cells[0])
        episodes.append(dict(id=cells[0], date=date, title=match[1], topic=cells[2],
                             difficulty=cells[3], duration=cells[4],
                             kind="test" if cells[0] == "#000" else "official"))
    if not episodes:
        raise ValueError("No public challenges")
    episodes.sort(key=lambda row: row["date"], reverse=True)
    documents = {"Debug 挑战赛手册.md": read_public(root, "Debug 挑战赛手册.md")}
    for episode in episodes:
        base = "challenges/" + episode["date"] + "/"
        entry = read_public(root, base + "README.md")
        documents[base + "README.md"] = entry
        paths = set(re.findall(r"\]\((docs/[a-z0-9_-]+\.md)(?:#[^)]*)?\)", entry))
        if (root / base / "evidence/initial/README.md").is_file():
            paths.add("evidence/initial/README.md")
        for path in sorted(paths):
            documents[base + path] = read_public(root, base + path)
    latest = next((item for item in episodes if item["kind"] == "official"), episodes[0])
    return {"savedDate": episodes[0]["date"], "commit": revision, "episodes": episodes,
            "featured": {"date": latest["date"], "headline": latest["title"], "summary": latest["topic"]},
            "documents": documents}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ref", default="main")
    args = parser.parse_args()
    target = Path(args.output).resolve()
    if ROOT / "organizer" == target or ROOT / "organizer" in target.parents:
        raise ValueError("Public output cannot be an organizer path")
    result = build(revision=args.ref)
    target.mkdir(parents=True, exist_ok=True)
    if any(p.name not in {"snapshot.json", "handbook.md", "app.js", "content-source.mjs"} for p in target.iterdir()):
        raise ValueError("Refusing to reuse an output directory containing unrelated files")
    (target / "snapshot.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (target / "handbook.md").write_text(result["documents"]["Debug 挑战赛手册.md"])
    print("Public snapshot:", len(result["episodes"]), "challenges,", len(result["documents"]), "documents;", args.ref)
