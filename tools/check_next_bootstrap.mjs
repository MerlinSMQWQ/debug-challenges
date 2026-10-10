// CI only: compile the actual bootstrap with production's exact public dependencies.
import {mkdtempSync,writeFileSync,copyFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
const root=mkdtempSync(join(tmpdir(),'debug-next-bootstrap-'));
const {mkdirSync}=await import('node:fs');mkdirSync(join(root,'app'));
for(const name of ['site-client.tsx','release-loader.mjs']) copyFileSync(new URL(`../website/next/${name}`,import.meta.url),join(root,'app',name));
writeFileSync(join(root,'package.json'),JSON.stringify({private:true,type:'module',dependencies:{next:'16.3.4',react:'19.2.6','react-dom':'19.2.6'},devDependencies:{typescript:'5.9.3','@types/node':'22.19.19','@types/react':'19.2.14','@types/react-dom':'19.2.3'}}));
writeFileSync(join(root,'tsconfig.json'),JSON.stringify({compilerOptions:{target:'ES2022',lib:['dom','dom.iterable','esnext'],allowJs:true,skipLibCheck:true,strict:true,noEmit:true,esModuleInterop:true,module:'esnext',moduleResolution:'bundler',resolveJsonModule:true,isolatedModules:true,jsx:'react-jsx',plugins:[{name:'next'}]},include:['app/**/*','.next/types/**/*.ts']}));
writeFileSync(join(root,'next.config.mjs'),'export default {experimental:{cpus:1},poweredByHeader:false};');
writeFileSync(join(root,'app/layout.tsx'),'import type {ReactNode} from "react";export default function Layout({children}:{children:ReactNode}){return <html><body>{children}</body></html>;}');
writeFileSync(join(root,'app/page.tsx'),'import SiteClient from "./site-client";export default function Page(){return <SiteClient/>;}');
writeFileSync(join(root,'app/site-shell.ts'),`export const siteShell=${JSON.stringify('<main id="main">Loading</main>')};`);
execFileSync('npm',['install','--ignore-scripts','--no-audit','--no-fund'],{cwd:root,stdio:'inherit'});
execFileSync(join(root,'node_modules/.bin/next'),['build','--webpack'],{cwd:root,stdio:'inherit',env:{...process.env,NEXT_TELEMETRY_DISABLED:'1'}});
