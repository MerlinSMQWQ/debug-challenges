import {test} from 'node:test';
import assert from 'node:assert/strict';
import {publicChallengeFile,selectChallengeEntries,createChallengeArchive,loadChallengeArchive,materialLabel} from '../public/content-source.mjs';

const sha = 'a'.repeat(40), date = '2026-10-10', encoder = new TextEncoder();
const file = (path,text='sample') => ({path,type:'blob',mode:'100644',sha,size:encoder.encode(text).length,bytes:encoder.encode(text)});
const files = [file('README.md'),file('Dockerfile'),file('compose.yaml'),file('shipping.py')];
const shared = {'Debug 挑战赛手册.md':encoder.encode('manual')};

test('private material, unrelated paths and runtime data cannot enter a challenge ZIP', () => {
  for (const path of ['../organizer/GROUND_TRUTH.md','organizer/answer.py','reference/shipping.py','shipping_fixed.py',
    '.env','.git/config','data/accounts.json','config/credentials.json','submissions/a.py','scores/a.py','runtime/run.py',
    'AGENTS.md','docs/agents.md','docs/AGENTS.override.md','docs/CLAUDE.md','docs/SKILL.md','docs/review.instructions.md',
    'var/runs/a.json','notes/fix.py','challenges/2026-10-09/README.md','data/../secret.json','tests/reference.sha256','data%2fsecret.json']) {
    assert.equal(publicChallengeFile(path),false,path);
  }
  for (const path of ['shipping.py','.dockerignore','.gitignore','data/morning.json','docs/pre_read.md',
    'settlement_export/job.py','scripts/run_export.py','tests/fixtures.sha256.json','evidence/initial/export.log']) assert.equal(publicChallengeFile(path),true,path);
});
test('incomplete trees, symlinks, submodules and duplicate files fail closed', () => {
  assert.throws(() => selectChallengeEntries({tree:files,truncated:true}));
  for (const bad of [{...files[0],mode:'120000'}, {...files[0],type:'commit',mode:'160000'}, {...files[0],size:3e6}]) {
    assert.throws(() => selectChallengeEntries({tree:[...files.slice(1),bad],truncated:false}));
  }
  assert.throws(() => selectChallengeEntries({tree:[...files,files[0]],truncated:false}));
  assert.throws(() => selectChallengeEntries({tree:files.slice(1),truncated:false}));
});
test('archive creation rejects incomplete bytes and invalid identities', () => {
  assert.throws(() => createChallengeArchive('2026-02-30',files,shared));
  assert.throws(() => createChallengeArchive(date,[...files.slice(1),{...files[0],bytes:new Uint8Array(0)}],shared));
  assert.throws(() => createChallengeArchive(date,files,{}));
  assert.deepEqual(createChallengeArchive(date,files,shared),createChallengeArchive(date,[...files].reverse(),shared));
});
test('download pins all files to one revision and never reads excluded blobs or another date', async () => {
  const calls=[], bytes=[];
  const entry = (path,treeSha) => ({path,type:'tree',mode:'040000',sha:treeSha});
  const text = async url => {
    calls.push(url);
    if (url.endsWith('/'+sha)) return JSON.stringify({truncated:false,tree:[entry('challenges','b'.repeat(40)),
      ...Object.keys(shared).map(path=>({...file(path),size:shared[path].length})),file('AGENTS.md','PRIVATE_SENTINEL'),entry('organizer','e'.repeat(40))]});
    if (url.endsWith('/'+'b'.repeat(40))) return JSON.stringify({truncated:false,tree:[entry(date,'c'.repeat(40)),entry('2026-10-09','d'.repeat(40))]});
    assert.ok(url.endsWith('/'+'c'.repeat(40)+'?recursive=1'));
    return JSON.stringify({truncated:false,tree:[...files,file('organizer/answer.py','PRIVATE_SENTINEL'),file('.env','PRIVATE_SENTINEL'),file('docs/agents.md','PRIVATE_SENTINEL')]});
  };
  const data = async url => {
    bytes.push(url);
    assert.ok(url.includes('/'+sha+'/')); assert.ok(!/organizer|\.env|2026-10-09|agents\.md/i.test(url));
    const path=decodeURIComponent(url.split('/').slice(6).join('/'));
    return shared[path] || files.find(file=>`challenges/${date}/${file.path}`===path).bytes;
  };
  const result=await loadChallengeArchive(text,data,'example/repo',date,sha);
  assert.equal(calls.length,3); assert.equal(bytes.length,5);
  assert.ok(!new TextDecoder().decode(result).includes('PRIVATE_SENTINEL'));
  await assert.rejects(loadChallengeArchive(text,data,'example/repo',date,'main'));
});
test('material navigation keeps short labels while retaining document routes', () => {
  assert.equal(materialLabel('docs/pre_read.md','赛前知识：让自定义对象参与 Python 操作'),'赛前知识');
  assert.equal(materialLabel('docs/rules.md','比赛规则与业务验收'),'比赛规则');
  assert.equal(materialLabel('docs/validation.md','准备验证范围'),'验证记录');
});
