// Bundled into Next's hashed page chunk; mutable metadata never caches this loader.
export function releaseScript(snapshot) {
  if (!snapshot || typeof snapshot.commit !== 'string' || !/^[a-f0-9]{40}$/.test(snapshot.commit)) throw new Error('发布版本无效，请稍后重试。');
  return `/releases/${snapshot.commit}/app.js`;
}

export async function loadRelease(fetchSnapshot, addScript, nonce = () => crypto.randomUUID()) {
  const response = await fetchSnapshot(`/snapshot.json?boot=${encodeURIComponent(nonce())}`, {
    cache: 'no-store', credentials: 'omit',
  });
  if (!response.ok) throw new Error('当前发布版本暂时无法读取，请稍后重试。');
  const source = releaseScript(await response.json());
  // These dependencies already have immutable, unchanged contents in production.
  for (const path of ['/vendor/marked.min.js', '/vendor/purify.min.js', source]) await addScript(path);
  return source;
}
