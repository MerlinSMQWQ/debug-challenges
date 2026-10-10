'use client';
import { useEffect } from 'react';
import { siteShell } from './site-shell';
import { loadRelease } from './release-loader.mjs';

// An ordinary document refresh discovers the current immutable public release.
export default function SiteClient() {
  useEffect(() => {
    const state = window as typeof window & { debugSiteBoot?: Promise<unknown> };
    state.debugSiteBoot ??= loadRelease(fetch, (src: string) => new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.dataset.siteSrc = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('页面组件暂时无法加载，请刷新重试。'));
      document.body.appendChild(script);
    }));
    state.debugSiteBoot.catch((error: Error) => {
      const main = document.getElementById('main');
      if (main) main.textContent = error.message;
    });
  }, []);
  return <div dangerouslySetInnerHTML={{ __html: siteShell }} />;
}
