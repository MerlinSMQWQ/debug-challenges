import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseIndex, publicDocumentPath, loadRepositoryIndex, savedDocument } from '../public/content-source.mjs';

const readme = readFileSync(new URL('../../README.md', import.meta.url), 'utf8');
test('formal numbering differs from the retained historical date identity', () => {
  const rows = parseIndex(readme);
  assert.deepEqual(rows.map(x => [x.id, x.date, x.kind]),
    [['#001', '2026-10-10', 'official'], ['#000', '2026-10-09', 'test']]);
});
test('an existing legacy five-column index remains readable', () => {
  const rows = parseIndex('| #001 | [Old](challenges/2026-10-09/README.md) | Python | Medium | 45 分钟 |');
  assert.equal(rows[0].date, '2026-10-09');
});
test('a push cannot mix the branch index with documents from a second revision', async () => {
  const calls = [], sha = 'b'.repeat(40);
  const source = async url => {
    calls.push(url);
    if (url.includes('/commits/main')) return JSON.stringify({ sha });
    assert.equal(url, `https://raw.githubusercontent.com/example/repo/${sha}/README.md`);
    return readme;
  };
  const result = await loadRepositoryIndex(source, 'example/repo');
  assert.equal(result.commit, sha);
  assert.equal(result.episodes.length, 2);
  assert.equal(calls.length, 2);
  assert.ok(calls.every(url => !url.includes('organizer')));
});
test('API failure or invalid revision leaves caller able to select a visible snapshot', async () => {
  await assert.rejects(loadRepositoryIndex(async () => { throw new Error('offline'); }, 'example/repo'));
  await assert.rejects(loadRepositoryIndex(async () => JSON.stringify({sha:'main'}), 'example/repo'));
  const fallback = savedDocument({commit:'a'.repeat(40),documents:{'Debug 挑战赛手册.md':'saved'}}, 'Debug 挑战赛手册.md');
  assert.equal(fallback.saved, true); assert.equal(fallback.text, 'saved');
});
test('allowlist blocks answers, credentials and traversal including in saved documents', () => {
  for (const path of ['../organizer/GROUND_TRUTH.md', 'organizer/GROUND_TRUTH.md', '.env', 'docs/../../x.md', 'data/accounts.json']) {
    assert.equal(publicDocumentPath(path), false);
    assert.throws(() => savedDocument({documents:{[path]:'private'}}, path));
  }
  assert.equal(publicDocumentPath('docs/pre_read.md'), true);
});
test('malformed or duplicate identities cannot silently replace the directory', () => {
  const row = '| #001 | [New](challenges/2026-10-10/README.md) | Python | Easy | 20 分钟 |';
  assert.throws(() => parseIndex(row+'\n'+row));
  assert.throws(() => parseIndex(row.replace('2026-10-10','2026-02-30')));
  assert.throws(() => parseIndex(row.replace(' | Python',' | Extra | Python')));
});
