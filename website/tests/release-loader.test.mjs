import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadRelease,releaseScript} from '../next/release-loader.mjs';

test('ordinary boots bypass cached metadata and select immutable directories, including rollback', async () => {
  const old = 'a'.repeat(40), current = 'b'.repeat(40);
  const cache = new Map([['/app.js','old executable'],['/snapshot.json',{commit:old}]]);
  let published=current, n=0;
  const requests=[],scripts=[];
  const fetchSnapshot=async (url,options) => {
    requests.push({url,options});
    return {ok:true,json:async () => cache.get(url) || {commit:published}};
  };
  const add=async src=>scripts.push(src);
  assert.equal(await loadRelease(fetchSnapshot,add,()=>String(++n)),`/releases/${current}/app.js`);
  published=old;
  assert.equal(await loadRelease(fetchSnapshot,add,()=>String(++n)),`/releases/${old}/app.js`);
  assert.deepEqual(requests.map(r=>r.url),['/snapshot.json?boot=1','/snapshot.json?boot=2']);
  assert.ok(requests.every(r=>r.options.cache==='no-store' && r.options.credentials==='omit'));
  assert.deepEqual(scripts,[...['/vendor/marked.min.js','/vendor/purify.min.js',`/releases/${current}/app.js`],...['/vendor/marked.min.js','/vendor/purify.min.js',`/releases/${old}/app.js`]]);
  assert.equal(cache.get('/app.js'),'old executable');
});

test('invalid or unavailable release metadata never boots unversioned or external code', async () => {
  for(const commit of ['main','../private','https://example.com/a.js','a'.repeat(41),'A'.repeat(40),null]) assert.throws(()=>releaseScript({commit}));
  let ran=false;
  await assert.rejects(loadRelease(async()=>({ok:false}),async()=>{ran=true},()=> 'nonce'));
  await assert.rejects(loadRelease(async()=>({ok:true,json:async()=>({commit:'main'})}),async()=>{ran=true},()=> 'nonce'));
  assert.equal(ran,false);
});
