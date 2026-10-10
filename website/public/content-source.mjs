// Public content only. This module never reads organizer, accounts, submissions or scores.
export function publicDocumentPath(path) {
  return !maintainerInstruction(path) && /^(?:README\.md|docs\/[a-z0-9_-]+\.md|evidence\/initial\/README\.md)$/.test(path);
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
  if (maintainerInstruction(path)) throw new Error('not public');
  if (typeof snapshot.documents?.[path] !== 'string') throw new Error('no saved document');
  return { text: snapshot.documents[path], saved: true, commit: snapshot.commit };
}

export function materialLabel(path, label) {
  return ({'README.md':'赛题入口','docs/pre_read.md':'赛前知识','docs/operations.md':'运行指南',
    'docs/rules.md':'比赛规则','docs/incident.md':'事故说明','docs/validation.md':'验证记录'})[path] || label.split(/[：:]/)[0];
}

const PACKAGE_LIMIT = 16 * 1024 * 1024;
const FILE_LIMIT = 2 * 1024 * 1024;
const SHARED_FILES = ['Debug 挑战赛手册.md'];
const PRIVATE_PART = /(?:^|[-_.])(organizer|reference|fixed|fix|answer|solution|credential|secret|token|password|account|submission|score|private|user|participant|member|login|auth|session|key|api[_-]?key|ground[_-]?truth)s?(?:$|[-_.])/i;

function maintainerInstruction(path) {
  return typeof path === 'string' && /^(?:agents(?:\..+)?|claude|gemini|codex|skill|copilot(?:-instructions)?|.*\.instructions)\.md$/i.test(path.split('/').pop());
}

export function publicChallengeFile(path) {
  if (typeof path !== 'string' || maintainerInstruction(path) || path.includes('\\') || path.includes('%') ||
      path.split('/').some(part => !part || part === '.' || part === '..' || PRIVATE_PART.test(part))) return false;
  if (/^(?:README\.md|Dockerfile|compose\.ya?ml|pyproject\.toml|\.dockerignore|\.gitignore)$/.test(path)) return true;
  if (/^[a-z][a-z0-9_]*\.py$/.test(path)) return true;
  if (/^docs\/[a-z0-9_-]+\.md$/.test(path)) return true;
  if (/^evidence\/initial\/[a-z0-9_-]+\.(?:md|log|json)$/.test(path)) return true;
  if (/^tests\/(?:[a-z0-9_]+\.py|fixtures\.sha256\.json)$/.test(path)) return true;
  if (/^(?:data|config)\/(?:[a-z0-9_-]+\/)*[a-z0-9_-]+\.(?:csv|json|toml|yaml|yml)$/.test(path)) return true;
  return /^(?:scripts|[a-z][a-z0-9_]*)\/(?:[a-z][a-z0-9_]*\/)*[a-z0-9_]+\.py$/.test(path) &&
    !/^(?:runtime|var|notes|organizer|reference|answers|solutions|credentials|submissions|scores|accounts|private)\//.test(path);
}

function validDate(date) {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) &&
    !Number.isNaN(new Date(`${date}T00:00:00Z`).valueOf()) &&
    new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date;
}

export function selectChallengeEntries(tree) {
  if (!tree || tree.truncated !== false || !Array.isArray(tree.tree)) throw new Error('incomplete package tree');
  const names = new Set(), files = [];
  for (const entry of tree.tree) {
    if (entry.type === 'tree' || !publicChallengeFile(entry.path)) continue;
    if (entry.type !== 'blob' || !['100644','100755'].includes(entry.mode) ||
        !/^[a-f0-9]{40}$/.test(entry.sha) || !Number.isInteger(entry.size) || entry.size < 0 || entry.size > FILE_LIMIT ||
        names.has(entry.path)) throw new Error('unsafe package file');
    names.add(entry.path); files.push(entry);
  }
  if (!['README.md','Dockerfile','compose.yaml'].every(name => names.has(name)) ||
      !files.some(file => file.path.endsWith('.py')) || files.length > 256 ||
      files.reduce((sum, file) => sum + file.size, 0) > PACKAGE_LIMIT) throw new Error('incomplete or oversized package');
  return files.sort((a,b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
}

// ZIP32, stored entries, UTF-8 names. No dependency or server-side archive endpoint.
const ENCODER = new TextEncoder();
const CRC_TABLE = Uint32Array.from({length:256}, (_, value) => {
  for (let bit = 0; bit < 8; bit++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  return value >>> 0;
});
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) crc = CRC_TABLE[(crc ^ byte) & 255] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function zipArchive(files) {
  const local = [], central = [], names = new Set(); let offset = 0, directorySize = 0;
  for (const file of files) {
    if (names.has(file.path) || file.path.split('/').some(part => !part || part === '.' || part === '..') ||
        /[\\\x00-\x1f]/.test(file.path) || !(file.bytes instanceof Uint8Array)) throw new Error('unsafe archive entry');
    names.add(file.path);
    const name = ENCODER.encode(file.path), crc = crc32(file.bytes);
    if (name.length > 1024 || file.bytes.length > FILE_LIMIT) throw new Error('oversized archive entry');
    const header = new Uint8Array(30 + name.length), view = new DataView(header.buffer);
    view.setUint32(0,0x04034b50,true); view.setUint16(4,20,true); view.setUint16(6,0x800,true);
    view.setUint16(12,33,true); view.setUint32(14,crc,true);
    view.setUint32(18,file.bytes.length,true); view.setUint32(22,file.bytes.length,true);
    view.setUint16(26,name.length,true); header.set(name,30);
    const record = new Uint8Array(46 + name.length), cv = new DataView(record.buffer);
    cv.setUint32(0,0x02014b50,true); cv.setUint16(4,0x314,true); cv.setUint16(6,20,true);
    cv.setUint16(8,0x800,true); cv.setUint16(14,33,true); cv.setUint32(16,crc,true);
    cv.setUint32(20,file.bytes.length,true); cv.setUint32(24,file.bytes.length,true);
    cv.setUint16(28,name.length,true); cv.setUint32(38,parseInt(file.mode || '100644',8) << 16,true);
    cv.setUint32(42,offset,true); record.set(name,46);
    local.push(header,file.bytes); central.push(record);
    offset += header.length + file.bytes.length; directorySize += record.length;
  }
  const end = new Uint8Array(22), view = new DataView(end.buffer);
  view.setUint32(0,0x06054b50,true); view.setUint16(8,files.length,true); view.setUint16(10,files.length,true);
  view.setUint32(12,directorySize,true); view.setUint32(16,offset,true);
  const archive = new Uint8Array(offset + directorySize + end.length); let cursor = 0;
  if (archive.length > PACKAGE_LIMIT + 1024 * 1024) throw new Error('oversized archive');
  for (const bytes of [...local,...central,end]) { archive.set(bytes,cursor); cursor += bytes.length; }
  return archive;
}

export function createChallengeArchive(date, files, shared) {
  if (!validDate(date)) throw new Error('invalid challenge date');
  const selected = selectChallengeEntries({truncated:false,tree:files});
  const prefix = `debug-challenge-${date}/`;
  const contents = selected.map(file => {
    if (!(file.bytes instanceof Uint8Array) || file.bytes.length !== file.size) throw new Error('incomplete package bytes');
    return {...file,path:`${prefix}challenges/${date}/${file.path}`};
  });
  for (const path of SHARED_FILES) {
    if (!(shared[path] instanceof Uint8Array)) throw new Error('missing shared document');
    contents.push({path:prefix+path,bytes:shared[path]});
  }
  contents.push({path:prefix+'README.md',bytes:ENCODER.encode(`# ${date} 赛题资料\n\n先读[赛题入口](challenges/${date}/README.md)，再按入口准备知识与环境。\n\n在解压后的本目录打开终端：\n\n\`\`\`sh\ncd challenges/${date}\n\`\`\`\n\n具体准备命令见题目运行指南。通用规则见[参赛手册](Debug%20挑战赛手册.md)。\n`)});
  return zipArchive(contents.sort((a,b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
}

export async function loadChallengeArchive(readText, readBytes, repo, date, revision) {
  if (!validDate(date) || !/^[a-f0-9]{40}$/.test(revision) || !/^[\w.-]+\/[\w.-]+$/.test(repo)) throw new Error('invalid package source');
  const treeURL = sha => `https://api.github.com/repos/${repo}/git/trees/${sha}`;
  const root = JSON.parse(await readText(treeURL(revision)));
  const subtree = (tree,path) => {
    if (tree.truncated !== false || !Array.isArray(tree.tree)) throw new Error('incomplete source tree');
    const entry = tree.tree.find(item => item.path === path);
    if (entry?.type !== 'tree' || entry.mode !== '040000' || !/^[a-f0-9]{40}$/.test(entry.sha)) throw new Error('missing source directory');
    return entry.sha;
  };
  const dates = JSON.parse(await readText(treeURL(subtree(root,'challenges'))));
  const tree = JSON.parse(await readText(treeURL(subtree(dates,date))+'?recursive=1'));
  const files = selectChallengeEntries(tree);
  const rawURL = path => `https://raw.githubusercontent.com/${repo}/${revision}/${path.split('/').map(encodeURIComponent).join('/')}`;
  // Four downloads at a time; only the selected date's allowlisted blobs are read.
  for (let start = 0; start < files.length; start += 4) {
    await Promise.all(files.slice(start,start+4).map(async file => {
      file.bytes = await readBytes(rawURL(`challenges/${date}/${file.path}`),FILE_LIMIT);
      if (file.bytes.length !== file.size) throw new Error('changed or incomplete source');
    }));
  }
  const shared = {};
  for (const path of SHARED_FILES) {
    const entry = root.tree.find(item => item.path === path);
    if (entry?.type !== 'blob' || entry.mode !== '100644' || entry.size > FILE_LIMIT) throw new Error('unsafe shared document');
    shared[path] = await readBytes(rawURL(path),FILE_LIMIT);
    if (shared[path].length !== entry.size) throw new Error('incomplete shared document');
  }
  return createChallengeArchive(date,files,shared);
}
