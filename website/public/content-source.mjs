// Public content only. This module never reads organizer, accounts, submissions or scores.
export function publicDocumentPath(path) {
  return /^(?:README\.md|docs\/[a-z0-9_-]+\.md|evidence\/initial\/README\.md)$/.test(path);
}

export function parseIndex(markdown) {
  const items = [], dates = new Set(), ids = new Set();
  for (const line of markdown.split('\n')) {
    if (!line.trim().startsWith('|')) continue;
    const match = line.match(/\[([^\]]+)\]\(challenges\/(\d{4}-\d{2}-\d{2})\/README\.md\)/);
    const cells = line.split('|').slice(1, -1).map(cell => cell.trim());
    if (!match) continue;
    const date = new Date(`${match[2]}T00:00:00Z`);
    if (cells.length !== 5 || !/^#\d{3,}$/.test(cells[0]) ||
        Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== match[2] ||
        dates.has(match[2]) || ids.has(cells[0])) throw new Error('unrecognized index');
    dates.add(match[2]); ids.add(cells[0]);
    items.push({ id: cells[0], date: match[2], title: match[1], topic: cells[2],
      difficulty: cells[3], duration: cells[4], kind: cells[0] === '#000' ? 'test' : 'official' });
  }
  if (!items.length) throw new Error('empty index');
  return items.sort((a, b) => b.date.localeCompare(a.date));
}

export async function loadRepositoryIndex(readText, repo, branch = 'main') {
  // A single immutable revision avoids mixing an index and documents from different pushes.
  const value = JSON.parse(await readText(`https://api.github.com/repos/${repo}/commits/${encodeURIComponent(branch)}`));
  if (!/^[a-f0-9]{40}$/.test(value.sha)) throw new Error('invalid revision');
  const markdown = await readText(`https://raw.githubusercontent.com/${repo}/${value.sha}/README.md`);
  return { commit: value.sha, episodes: parseIndex(markdown) };
}

export function savedDocument(snapshot, path) {
  if (!/^(?:Debug 挑战赛手册\.md|challenges\/\d{4}-\d{2}-\d{2}\/(?:README\.md|docs\/[a-z0-9_-]+\.md|evidence\/initial\/README\.md))$/.test(path)) {
    throw new Error('not public');
  }
  if (typeof snapshot.documents?.[path] !== 'string') throw new Error('no saved document');
  return { text: snapshot.documents[path], saved: true, commit: snapshot.commit };
}
