#!/usr/bin/env node
// Node 18+. Local source references only; no HTTP requests or generated-page validation.
const path = require('path');
const {check} = require('./media-refs');
try {
  const result = check(path.resolve(process.argv[2] || '.'));
  for (const p of result.problems) console.error(`${p.file} -> ${p.ref}: ${p.reason}`);
  console.log(`已检查 ${result.checked} 个本地媒体引用；问题 ${result.problems.length} 个。远程地址、动态模板、srcset、引用式 Markdown 和生成页面不在检查范围内。`);
  process.exitCode = result.problems.length ? 1 : 0;
} catch (e) { console.error(e.message); process.exitCode = 1; }
