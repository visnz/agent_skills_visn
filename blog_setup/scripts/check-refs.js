#!/usr/bin/env node
/**
 * 引用完整性检查：扫描 source 下所有 .md/.yml/.json，
 * 提取图片/媒体引用（![]()、cover/img/portrait、<img src>、url()），
 * 校验对应文件在 source 中真实存在，报告疑似 404。
 *
 * 用法：node check-refs.js <hexo项目根路径>
 *   <hexo项目根路径> 缺省时为当前目录。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const SRC = path.join(ROOT, 'source');

// 1. 收集 source 下所有文件 basename
const files = new Set();
(function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name.startsWith('.')) continue;
    const f = path.join(d, e.name);
    if (e.isDirectory()) walk(f);
    else files.add(e.name);
  }
})(SRC);

const MEDIA = /\.(?:webp|png|jpg|jpeg|gif|mp4)$/i;
const missing = new Set();

function check(ref, srcFile) {
  const base = path.basename(ref.replace(/[?#].*$/, '').replace(/\\/g, '/'));
  if (!MEDIA.test(base)) return; // 非媒体引用（如 css/字体）跳过
  if (files.has(base)) return;
  missing.add(path.relative(ROOT, srcFile) + '  ->  ' + base);
}

(function scan(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name.startsWith('.')) continue;
    const f = path.join(d, e.name);
    if (e.isDirectory()) scan(f);
    else if (/\.(md|yml|json)$/i.test(e.name)) {
      const t = fs.readFileSync(f, 'utf8');
      let m, re;
      re = /!\[[^\]]*\]\(([^)\s]+)\)/g;
      while ((m = re.exec(t))) check(m[1], f);
      re = /(?:cover|portrait|img|thumbnail|icon|default_cover|avatar)\s*:\s*['"]([^'"]+)['"]/g;
      while ((m = re.exec(t))) check(m[1], f);
      re = /<img\b[^>]*src=["']([^"']+)["']/g;
      while ((m = re.exec(t))) check(m[1], f);
      re = /url\(['"]?([^'")]+)['"]?\)/g;
      while ((m = re.exec(t))) check(m[1], f);
    }
  }
})(SRC);

if (missing.size) {
  console.log('=== 疑似 404 的媒体引用 ===');
  [...missing].sort().forEach((x) => console.log(x));
} else {
  console.log('所有媒体引用均有效，无 404。');
}
