// Use the same allowlist and ZIP writer as the browser; never walk organizer or runtime.
import {readFile, readdir, lstat, mkdir, writeFile} from 'node:fs/promises';
import {resolve, relative, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {parseIndex, publicChallengeFile, createChallengeArchive} from '../website/public/content-source.mjs';

const ROOT = resolve(fileURLToPath(new URL('..',import.meta.url)));
const blocked = /(?:^|[-_.])(organizer|reference|fixed|fix|answer|solution|credential|secret|token|password|account|submission|score|private|user|participant|member|login|auth|session|key|api[_-]?key|ground[_-]?truth)s?(?:$|[-_.])/i;

export async function buildPackages(root, output) {
  root = resolve(root); output = resolve(output);
  if (relative(root,output).split(/[\\/]/).some(part => ['challenges','organizer'].includes(part))) throw new Error('unsafe output directory');
  await mkdir(output,{recursive:true});
  if ((await readdir(output)).length) throw new Error('output directory must be empty');
  const episodes = parseIndex(await readFile(join(root,'README.md'),'utf8'));
  const shared = {};
  for (const path of ['Debug 挑战赛手册.md']) {
    if (!(await lstat(join(root,path))).isFile()) throw new Error('unsafe shared document');
    shared[path] = new Uint8Array(await readFile(join(root,path)));
  }
  const report = [];
  for (const episode of episodes) {
    const base = join(root,'challenges',episode.date), files = [];
    if (!(await lstat(base)).isDirectory()) throw new Error('unsafe challenge directory');
    async function walk(directory, prefix='') {
      for (const entry of await readdir(directory,{withFileTypes:true})) {
        const path = prefix + entry.name;
        if (entry.isDirectory()) {
          if (path.split('/').some(part => part.startsWith('.') || blocked.test(part) || ['runtime','var','notes'].includes(part))) continue;
          await walk(join(directory,entry.name),path+'/');
        } else if (publicChallengeFile(path)) {
          if (!entry.isFile()) throw new Error('unsafe package file: '+path);
          const bytes = new Uint8Array(await readFile(join(directory,entry.name)));
          const sha = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
          const mode = (await lstat(join(directory,entry.name))).mode & 0o111 ? '100755' : '100644';
          files.push({path,type:'blob',mode,sha,size:bytes.length,bytes});
        }
      }
    }
    await walk(base);
    const archive = createChallengeArchive(episode.date,files,shared);
    const name = `debug-challenge-${episode.date}.zip`;
    await writeFile(join(output,name),archive);
    report.push({date:episode.date,file:name,challengeFiles:files.length,bytes:archive.length,
      sha256:createHash('sha256').update(archive).digest('hex')});
  }
  return report;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const index = process.argv.indexOf('--output');
  if (index === -1 || !process.argv[index+1]) throw new Error('Use --output with an empty staging directory');
  console.log(JSON.stringify(await buildPackages(ROOT,process.argv[index+1]),null,2));
}
