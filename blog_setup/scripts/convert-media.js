#!/usr/bin/env node
/** Node 18+, ffmpeg/ffprobe and ImageMagick in PATH.
 * node convert-media.js <hexo-root>
 * Keeps originals, refuses existing output files, adopts only smaller decodable results.
 * JPG originals and hash state live in <root>/.media-conversion-backup (exclude from Git).
 * Theme templates and dynamic references require separate review; this script never rewrites them.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {execFileSync} = require('child_process');
const {walk, references, resolveRef, check} = require('./media-refs');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function run(cmd, args) { return execFileSync(cmd, args, {encoding:'utf8', windowsHide:true, stdio:['ignore','pipe','pipe']}); }
function probe(file) {
  const data = JSON.parse(run('ffprobe', ['-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',file]));
  const s = data.streams && data.streams[0];
  if (!s || !(s.width > 0 && s.height > 0)) throw new Error('No valid image/video stream: ' + file);
  run('ffmpeg', ['-v','error','-xerror','-i',file,'-f','null','-']);
  return s;
}
function writeAtomic(file, value) {
  const tmp = file + '.' + crypto.randomUUID() + '.tmp';
  try { fs.writeFileSync(tmp, value, {flag:'wx'}); fs.renameSync(tmp, file); }
  finally { if(fs.existsSync(tmp)) fs.unlinkSync(tmp); }
}
function main(root) {
  const source = path.join(root,'source');
  if (!fs.statSync(source).isDirectory()) throw new Error('Missing source directory');
  const initial = check(root);
  if (initial.problems.length) throw new Error('Fix source-reference problems first: ' + JSON.stringify(initial.problems));
  const owners = walk(source, ['.md','.yml','.yaml','.json','.html','.css']);
  const docs = owners.map(file => ({file, text:fs.readFileSync(file,'utf8')}));
  const cover = new Set();
  for(const doc of docs) for(const ref of references(doc.text)) {
    const resolved = resolveRef(ref.value, doc.file, source);
    if(ref.kind === 'cover' && resolved && resolved.target) cover.add(resolved.target);
  }
  const backup = path.join(root,'.media-conversion-backup');
  const statePath = path.join(backup,'state.json');
  const state = fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath,'utf8')) : {};
  const mapping = new Map();
  let failures = 0, saved = 0;
  const mediaFiles = walk(source, ['.gif','.png','.jpg','.jpeg']);
  for(const file of mediaFiles) {
    const ext = path.extname(file).toLowerCase();
    const jpg = ext === '.jpg' || ext === '.jpeg';
    if(ext === '.gif' && cover.has(file)) { console.log('[保留封面] ' + path.relative(root,file)); continue; }
    const output = jpg ? file : file.slice(0,-ext.length) + (ext === '.gif' ? '.mp4' : '.webp');
    const key = path.relative(source,file).replace(/\\/g,'/');
    const bytes = fs.statSync(file).size;
    const digest = hash(file);
    if(jpg && state[key]) {
      if(state[key].outputHash === digest) { console.log('[已处理] ' + key); continue; }
      console.error('[需检查] JPG 与已保存状态不同，未再次压缩: ' + key); failures++; continue;
    }
    if(jpg && bytes <= 400*1024) continue;
    if(!jpg && fs.existsSync(output)) { console.log('[目标已存在，跳过] ' + key); continue; }
    const tmp = path.join(path.dirname(file), '.' + crypto.randomUUID() + '.tmp' + path.extname(output));
    try {
      if(jpg) run('magick',[file,'-auto-orient','-resize','2560x2560>','-quality','82','-strip',tmp]);
      else if(ext === '.gif') run('ffmpeg',['-n','-v','error','-i',file,'-c:v','libx264','-pix_fmt','yuv420p','-crf','26','-movflags','faststart',tmp]);
      else run('ffmpeg',['-n','-v','error','-i',file,'-c:v','libwebp','-quality','80','-lossless','0',tmp]);
      const resultBytes = fs.statSync(tmp).size;
      if(!resultBytes || resultBytes >= bytes) { console.log('[未变小，保留] ' + key); continue; }
      probe(tmp);
      if(jpg) {
        const original = path.join(backup,'originals',key);
        fs.mkdirSync(path.dirname(original),{recursive:true});
        fs.copyFileSync(file, original, fs.constants.COPYFILE_EXCL);
        // Persist intended result before replacing; an interrupted run fails closed on hash mismatch.
        state[key] = {originalHash:digest, outputHash:hash(tmp), original:path.relative(root,original)};
        writeAtomic(statePath,JSON.stringify(state,null,2)+'\n');
        if(hash(file) !== digest) throw new Error('Source changed during conversion');
        fs.renameSync(tmp,file);
      } else {
        if(hash(file) !== digest) throw new Error('Source changed during conversion');
        fs.copyFileSync(tmp,output,fs.constants.COPYFILE_EXCL);
        mapping.set(file,output);
      }
      saved += bytes-resultBytes;
      console.log('[采用] ' + key + ': ' + bytes + ' -> ' + resultBytes);
    } catch(e) { failures++; console.error('[失败] ' + key + ': ' + e.message); }
    finally { if(fs.existsSync(tmp)) fs.unlinkSync(tmp); }
  }
  // Read originals remain available even if reference editing fails or the process is interrupted.
  for(const doc of docs) {
    let text = doc.text;
    for(const ref of references(doc.text).reverse()) {
      const resolved = resolveRef(ref.value,doc.file,source);
      const next = resolved && mapping.get(resolved.target);
      if(!next) continue;
      const clean = ref.value.replace(/[?#].*$/,'');
      const extension = path.extname(next);
      const value = clean.replace(/\.[^.\/\\]+$/,extension) + resolved.suffix;
      text = text.slice(0,ref.start)+value+text.slice(ref.end);
    }
    if(text !== doc.text) {
      if(fs.readFileSync(doc.file,'utf8') !== doc.text) throw new Error('Document changed during conversion: '+doc.file);
      writeAtomic(doc.file,text);
    }
  }
  const final = check(root);
  for(const p of final.problems) console.error(JSON.stringify(p));
  console.log(`已采用结果合计减少 ${(saved/1024/1024).toFixed(2)} MB；原始 GIF/PNG 仍保留，因此磁盘总占用可能增加。`);
  console.log('需另行检查视觉效果、主题动态路径和生成页面；确认全部引用后再人工决定是否删除原件。JPG 备份与状态: '+backup);
  return failures || final.problems.length ? 1 : 0;
}
if(require.main === module) {
  try { process.exitCode = main(path.resolve(process.argv[2] || '.')); }
  catch(e) { console.error(e.message); process.exitCode=1; }
}
module.exports = {main};
