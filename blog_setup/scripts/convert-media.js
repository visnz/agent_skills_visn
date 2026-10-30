#!/usr/bin/env node
/**
 * 媒体转换脚本（幂等，可重复运行）：
 *   - gif -> mp4   (H.264, crf 26, 用于画廊/正文动图，体积约 -85%)
 *   - png -> webp  (q80 有损)
 *   - jpg -> 原地压缩 (长边 2560, q82, auto-orient + 去 EXIF, 仅 >400KB)
 *   - 跳过 front-matter cover 引用的 gif（封面动图保留不转）
 *  并替换 source 下 .md/.yml/.json 与 categories.ejs 中的引用。
 *
 * 依赖：ffmpeg、ImageMagick(magick)，均在 PATH 中。
 * 用法：node convert-media.js <hexo项目根路径>
 *   <hexo项目根路径> 缺省时为当前目录。
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(process.argv[2] || '.');
const SRC = path.join(ROOT, 'source');
const THEME_LAYOUT = path.join(ROOT, 'themes', 'hexo-theme-quiet', 'layout'); // 按实际主题名调整

const JPG_MIN = 400 * 1024; // 只压缩大于 400KB 的 jpg，避免小图二次劣化

function walk(dir, exts, out = []) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (e) {
    return out;
  }
  for (const ent of entries) {
    if (ent.name.startsWith('.')) continue;
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      walk(full, exts, out);
    } else if (exts.includes(path.extname(ent.name).toLowerCase())) {
      out.push(full);
    }
  }
  return out;
}

function run(cmd, args) {
  try {
    execFileSync(cmd, args, { stdio: 'pipe', windowsHide: true });
  } catch (e) {
    const detail = (e.stderr || e.message || '').toString().trim();
    throw new Error(cmd + ' ' + args.slice(0, 3).join(' ') + ' ... ' + detail.slice(0, 400));
  }
}

function fmt(bytes) {
  return (bytes / 1024 / 1024).toFixed(2) + ' MB';
}

const mapping = []; // { oldBase, newBase }

function main() {
  const before = totalMediaSize();
  console.log('转换前媒体总体积: ' + fmt(before) + '\n');

  // 0. 用作封面的 gif 保留不动（封面以 <img> 渲染，gif 动图是有意为之）
  const coverGifs = findCoverGifs();

  // 1. gif -> mp4
  for (const gif of walk(SRC, ['.gif'])) {
    if (coverGifs.has(path.basename(gif))) {
      console.log('[gif保留] ' + path.relative(ROOT, gif) + '  (封面动图，跳过转换)');
      continue;
    }
    const mp4 = gif.replace(/\.gif$/i, '.mp4');
    const tmp = mp4 + '.tmp.mp4';
    console.log('[gif->mp4] ' + path.relative(ROOT, gif));
    try {
      run('ffmpeg', ['-y', '-loglevel', 'error', '-i', gif,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '26', '-movflags', 'faststart', tmp]);
      fs.renameSync(tmp, mp4);
      fs.unlinkSync(gif);
      mapping.push({ oldBase: path.basename(gif), newBase: path.basename(mp4) });
    } catch (e) {
      console.error('  !! 失败，跳过: ' + e.message);
      if (fs.existsSync(tmp)) fs.unlinkSync(tmp);
    }
  }

  // 2. png -> webp
  for (const png of walk(SRC, ['.png'])) {
    const webp = png.replace(/\.png$/i, '.webp');
    const tmp = webp + '.tmp.webp';
    console.log('[png->webp] ' + path.relative(ROOT, png));
    try {
      run('ffmpeg', ['-y', '-loglevel', 'error', '-i', png,
        '-c:v', 'libwebp', '-quality', '80', '-lossless', '0', tmp]);
      fs.renameSync(tmp, webp);
      fs.unlinkSync(png);
      mapping.push({ oldBase: path.basename(png), newBase: path.basename(webp) });
    } catch (e) {
      console.error('  !! 失败，跳过: ' + e.message);
      if (fs.existsSync(tmp)) fs.unlinkSync(tmp);
    }
  }

  // 3. jpg 原地压缩
  for (const jpg of walk(SRC, ['.jpg', '.jpeg'])) {
    const size = fs.statSync(jpg).size;
    if (size < JPG_MIN) continue;
    const tmp = jpg + '.tmp.jpg';
    console.log('[jpg压缩] ' + path.relative(ROOT, jpg) + '  (' + fmt(size) + ')');
    try {
      run('magick', [jpg, '-auto-orient', '-resize', '2560x2560>', '-quality', '82', '-strip', tmp]);
      fs.renameSync(tmp, jpg);
    } catch (e) {
      console.error('  !! 失败，跳过: ' + e.message);
      if (fs.existsSync(tmp)) fs.unlinkSync(tmp);
    }
  }

  // 4. 替换引用
  replaceRefs();

  const after = totalMediaSize();
  console.log('\n==== 转换完成 ====');
  console.log('媒体总体积: ' + fmt(before) + ' -> ' + fmt(after) + '   (节省 ' + fmt(Math.max(0, before - after)) + ')');
}

/**
 * 找出 front-matter cover 字段中引用的 gif 文件名（basename）。
 * 这些 gif 用作封面动图（以 <img> 渲染），保留原样不转 mp4。
 */
function findCoverGifs() {
  const coverGifs = new Set();
  const coverRe = /^cover:\s*['"]?([^'"\n]+\.gif)['"]?\s*$/gm;
  for (const f of walk(SRC, ['.md'])) {
    let content;
    try {
      content = fs.readFileSync(f, 'utf8');
    } catch (e) {
      continue;
    }
    let m;
    while ((m = coverRe.exec(content)) !== null) {
      coverGifs.add(path.basename(m[1]));
    }
  }
  return coverGifs;
}

function replaceRefs() {
  const bmap = {};
  for (const m of mapping) bmap[m.oldBase] = m.newBase;

  if (Object.keys(bmap).length === 0) {
    console.log('无 gif/png 转换，跳过引用替换');
    return;
  }

  let changedFiles = 0;

  // 普通 basename 替换（gif->mp4, png->webp）
  for (const f of walk(SRC, ['.md', '.yml', '.json'])) {
    let content = fs.readFileSync(f, 'utf8');
    let changed = false;
    for (const [oldBase, newBase] of Object.entries(bmap)) {
      if (content.includes(oldBase)) {
        content = content.split(oldBase).join(newBase);
        changed = true;
      }
    }
    if (changed) {
      fs.writeFileSync(f, content, 'utf8');
      console.log('[引用替换] ' + path.relative(ROOT, f));
      changedFiles++;
    }
  }

  // categories.ejs 中硬编码的 .png 扩展名（分类图标动态拼接）
  const catEjs = path.join(THEME_LAYOUT, 'categories.ejs');
  if (fs.existsSync(catEjs)) {
    let c = fs.readFileSync(catEjs, 'utf8');
    if (c.includes('%>.png')) {
      c = c.split('%>.png').join('%>.webp');
      fs.writeFileSync(catEjs, c, 'utf8');
      console.log('[引用替换] themes/.../layout/categories.ejs  (%>.png -> %>.webp)');
    }
  }

  console.log('共替换 ' + changedFiles + ' 个 Markdown/数据文件');
}

function totalMediaSize() {
  let total = 0;
  for (const f of walk(SRC, ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp4'])) {
    total += fs.statSync(f).size;
  }
  return total;
}

main();
