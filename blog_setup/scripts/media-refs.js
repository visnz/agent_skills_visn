'use strict';
// Shared local-reference handling. This is a source-file check, not a browser/HTTP check.
const fs = require('fs');
const path = require('path');
const MEDIA = /\.(?:webp|png|jpe?g|gif|mp4|webm|avif|svg)$/i;
function walk(dir, extensions) {
  return fs.readdirSync(dir, {withFileTypes: true}).flatMap(e => {
    if (e.name.startsWith('.') || e.isSymbolicLink()) return [];
    const file = path.join(dir, e.name);
    return e.isDirectory() ? walk(file, extensions) :
      (!extensions || extensions.includes(path.extname(file).toLowerCase()) ? [file] : []);
  });
}
function references(text) {
  const refs = [];
  function collect(re, group, kind) {
    for (const m of text.matchAll(re)) {
      if (!m.indices[group]) continue;
      const [start, end] = m.indices[group];
      if (!refs.some(r => r.start === start && r.end === end)) refs.push({start, end, value: m[group], kind});
    }
  }
  collect(/!?\[[^\]\n]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+["'][^\n]*?["'])?\s*\)/gd, 1, 'markdown-angle');
  // The optional angle group is absent for ordinary Markdown.
  collect(/!?\[[^\]\n]*\]\(\s*([^<\s)]+)(?:\s+["'][^\n]*?["'])?\s*\)/gd, 1, 'markdown');
  collect(/<(?:img|video|source)\b[^>]*?\b(?:src|poster)\s*=\s*["']([^"']+)["']/gdi, 1, 'html');
  // Extract all relevant attributes, including poster alongside src.
  for (const tag of text.matchAll(/<(?:img|video|source)\b[^>]*>/gdi)) {
    for (const attr of tag[0].matchAll(/\b(?:src|poster)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))/gdi)) {
      const n = attr[1] !== undefined ? 1 : attr[2] !== undefined ? 2 : 3;
      const start = tag.index + attr.indices[n][0], end = tag.index + attr.indices[n][1];
      if (!refs.some(r => r.start === start && r.end === end)) refs.push({start, end, value: attr[n], kind: 'html'});
    }
  }
  collect(/url\(\s*["']?([^'"\s)]+)["']?\s*\)/gd, 1, 'css');
  for (const m of text.matchAll(/(?:^|[\n{,])\s*["']?(cover|portrait|img|thumbnail|icon|default_cover|avatar)["']?\s*:\s*(?:"([^"\n]+)"|'([^'\n]+)'|([^\s#,"'\n}]+))/gd)) {
    const n = m[2] !== undefined ? 2 : m[3] !== undefined ? 3 : 4;
    const [start, end] = m.indices[n];
    if (!refs.some(r => r.start === start && r.end === end)) refs.push({start, end, value: m[n], kind: m[1]});
  }
  return refs.sort((a,b) => a.start - b.start);
}
function resolveRef(value, owner, source) {
  if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(value) || value.includes('<%') || value.includes('{{')) return null;
  const clean = value.replace(/[?#].*$/, '');
  let decoded;
  try { decoded = decodeURIComponent(clean).replace(/\\/g, '/'); } catch { return {error: 'invalid URL encoding'}; }
  if (!MEDIA.test(decoded)) return null;
  const target = decoded.startsWith('/') ? path.resolve(source, '.' + path.posix.normalize(decoded)) : path.resolve(path.dirname(owner), decoded);
  const rel = path.relative(source, target);
  if (rel.startsWith('..' + path.sep) || rel === '..' || path.isAbsolute(rel)) return {error: 'outside source; requires site-specific resolution'};
  return {target, suffix: value.slice(clean.length)};
}
function check(root) {
  const source = path.join(root, 'source');
  const problems = [];
  let checked = 0;
  for (const owner of walk(source, ['.md','.yml','.yaml','.json','.html','.css'])) {
    for (const ref of references(fs.readFileSync(owner, 'utf8'))) {
      const resolved = resolveRef(ref.value, owner, source);
      if (!resolved) continue;
      checked++;
      if (resolved.error || !fs.existsSync(resolved.target) || !fs.statSync(resolved.target).isFile())
        problems.push({file: path.relative(root, owner), ref: ref.value, reason: resolved.error || 'file missing'});
    }
  }
  return {checked, problems};
}
module.exports = {walk, references, resolveRef, check};
