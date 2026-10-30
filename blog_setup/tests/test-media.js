'use strict';
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const {execFileSync, spawnSync} = require('child_process');
const scripts = fs.existsSync(path.join(__dirname,'media-refs.js')) ? __dirname : path.join(__dirname,'..','scripts');
const {check, references} = require(path.join(scripts,'media-refs.js'));
const base = fs.mkdtempSync(path.join(os.tmpdir(),'visn-media-test-'));
function write(name,text) { const p=path.join(base,'source',name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,text);return p; }
function run(command,args) { return execFileSync(command,args,{stdio:'pipe',windowsHide:true}); }
try {
  const a=write('a/title.png','image'), b=write('b/title.png','image');
  write('a/title.png.jpg','image');
  write('post.md','![a](/a/title.png)\n![b](/b/title.png)\n![suffix](/a/title.png.jpg)\ncover: /a/title.png\n<video src="/a/title.png" poster="/b/title.png"><source src="/bad/video.mp4"></video>\n![remote](https://example.com/test.png)');
  assert.equal(check(base).problems.length,1);
  assert.match(check(base).problems[0].ref,/video.mp4/);
  write('bad/video.mp4','video');
  assert.equal(check(base).problems.length,0);
  write('bad.md','![wrong directory](/wrong/title.png)\ncover: /wrong/missing.gif');
  const checked=spawnSync(process.execPath,[path.join(scripts,'check-refs.js'),base],{encoding:'utf8'});
  assert.equal(checked.status,1);
  assert.equal(check(base).problems.length,2);
  assert.equal(references('![space](</a/a%20b.png> "title")')[0].value,'/a/a%20b.png');
  // Start a real-media fixture, without touching the user's blog.
  const fixture=fs.mkdtempSync(path.join(base,'conversion-'));
  const source=path.join(fixture,'source');fs.mkdirSync(path.join(source,'a'),{recursive:true});fs.mkdirSync(path.join(source,'b'));
  function media(name,args) { const out=path.join(source,name);run('ffmpeg',['-y','-v','error',...args,out]);return out; }
  const png=media('a/title.png',['-f','lavfi','-i','testsrc=size=512x512:rate=1','-frames:v','1']);
  fs.copyFileSync(png,path.join(source,'b','title.png'));
  const cover=media('a/cover.gif',['-f','lavfi','-i','testsrc=size=128x128:rate=10','-t','1']);
  const animation=media('a/anim.gif',['-f','lavfi','-i','testsrc=size=128x128:rate=10','-t','2']);
  const tiny=media('a/tiny.gif',['-f','lavfi','-i','color=black:size=2x2:rate=1','-frames:v','1']);
  fs.copyFileSync(png,path.join(source,'a','title.png.jpg'));
  const existing=path.join(source,'b','title.webp');fs.writeFileSync(existing,'existing output');
  const jpg=path.join(source,'a','large.jpg');run('magick',['-size','1600x1600','plasma:fractal','-quality','100',jpg]);
  assert.ok(fs.statSync(jpg).size>400*1024);
  const originalJpg=fs.readFileSync(jpg);
  const doc='![a](/a/title.png?x=1#demo)\n![b](/b/title.png)\n![suffix](/a/title.png.jpg)\ncover: /a/cover.gif\n![anim](/a/anim.gif)\n';
  fs.writeFileSync(path.join(source,'post.md'),doc);
  run(process.execPath,[path.join(scripts,'convert-media.js'),fixture]);
  const rewritten=fs.readFileSync(path.join(source,'post.md'),'utf8');
  assert.match(rewritten,/\/a\/title\.webp\?x=1#demo/);
  assert.match(rewritten,/\/b\/title\.png/);
  assert.match(rewritten,/\/a\/title\.png\.jpg/);
  assert.match(rewritten,/cover: \/a\/cover\.gif/);
  assert.match(rewritten,/\/a\/anim\.mp4/);
  for(const p of [png,cover,animation]) assert.ok(fs.existsSync(p));
  assert.ok(fs.existsSync(tiny));
  assert.ok(!fs.existsSync(path.join(source,'a','tiny.mp4')));
  assert.equal(fs.readFileSync(existing,'utf8'),'existing output');
  assert.deepEqual(fs.readFileSync(path.join(fixture,'.media-conversion-backup','originals','a','large.jpg')),originalJpg);
  const compressed=fs.readFileSync(jpg);
  run(process.execPath,[path.join(scripts,'convert-media.js'),fixture]);
  assert.deepEqual(fs.readFileSync(jpg),compressed);
  assert.equal(check(fixture).problems.length,0);
  fs.appendFileSync(jpg,'modified');
  const changedJpg=fs.readFileSync(jpg);
  const changed=spawnSync(process.execPath,[path.join(scripts,'convert-media.js'),fixture],{encoding:'utf8'});
  assert.equal(changed.status,1);
  assert.deepEqual(fs.readFileSync(jpg),changedJpg);
  // Invalid conversion input must not be removed, and failure must be observable.
  fs.writeFileSync(path.join(source,'broken.png'),'not an image');
  const failed=spawnSync(process.execPath,[path.join(scripts,'convert-media.js'),fixture],{encoding:'utf8'});
  assert.equal(failed.status,1);
  assert.equal(fs.readFileSync(path.join(source,'broken.png'),'utf8'),'not an image');
  assert.ok(!fs.existsSync(path.join(source,'broken.webp')));
  console.log('PASS: local path checks, video/unquoted fields, nonzero exit, exact replacement, existing targets, original retention, real conversion, JPG rerun, invalid input.');
} finally {
  assert.equal(path.dirname(path.resolve(base)),path.resolve(os.tmpdir()));
  assert.ok(path.basename(base).startsWith('visn-media-test-'));
  fs.rmSync(base,{recursive:true,force:true});
}
