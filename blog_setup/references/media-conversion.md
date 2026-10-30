# 媒体转换复盘

2026-10-30 在 `hexo_visn` 上完成的图片流量优化。以下参数和路径是当时现场，复用时重新确认。

## 结果

| 格式 | 处理前 | 处理后 | 说明 |
| --- | --- | --- | --- |
| gif | 316.5 MB (28 个) | mp4 48 MB | -85%，H.264 crf 26 |
| png | 39.1 MB (66 个) | webp ~5 MB | -87%，q80 |
| jpg | 226.8 MB (235 个) | 66 MB | -71%，长边 2560 q82 |
| 图片合计 | 582 MB | 79 MB | -86.7% |

媒体总体积（含原有 320MB mp4）：912.88 MB → 447.34 MB。

## 为什么 gif 转 mp4 而不是 animated WebP

- ImageMagick `convert` 生成 animated WebP：6.6 MB（原 3.15MB gif 反而变大）。
- ffmpeg 生成 animated WebP：12.8 MB（更大）。
- ffmpeg 转 mp4（H.264 crf 26）：0.4 MB，120 帧完整。

结论：本机 animated WebP 效果差，mp4 是正确选择。但**小 gif 转 mp4 也可能变大**（77KB gif → 35KB 是变小，但另有 82KB 场景曾变大），先对比体积再决定。

## 封面 gif 必须保留

- 封面（front-matter `cover:`）在首页/画廊卡片用 `<img src="cover">` 渲染，`<img>` 无法显示 mp4。
- 封面 gif 是"有意动图"，转成静态第一帧会丢失表达意图。
- 当前脚本按完整本地路径识别 `cover:` 引用并跳过对应 GIF，避免同名文件互相影响；未覆盖的模板语法仍需人工核对。
- 案例：`blender_RimClamp.md` 的封面+正文共用同一个 gif，用户要求保留 gif 动图。

## basename 子串替换的坑

- `title.png` 会误伤 `title.png.jpg`（basename 子串匹配），产生 `.webp.jpg` 错误引用。
- 案例：转换后出现 6 处 `.webp.jpg`（title 3 处 + Reel2024 3 处），全部手工修复。
- 当时通过检查后手工修复。当前转换脚本已改为按完整路径替换识别出的引用，不再做 basename 子串替换；`check-refs.js` 是有限语法下的本地文件初筛，不覆盖所有 404。

## 历史遗留 404（转换前就存在）

- `CRE.md` 的 `24.png.jpg`（文件缺失，删引用）。
- `sketch220625.md` 的 `22062.jpg`（笔误，改 `220625.jpg`）。
- `天气晚来秋.md` 的 `Allpic.png.jpg`（改 `Allpic.jpg`）。

## 懒加载实现

1. `scripts/media.js`（after_post_render filter）：`<img src="*.mp4">` → `<video class="lazy-video" loop muted playsinline preload="none">`，其余 `<img>` 注入 `loading="lazy"`。
2. 主题 `source/js/media.js`：IntersectionObserver 进入视口才 `play()`/`load()`。
3. `head.ejs` 引入 media.js；`home.ejs`、`gallery.ejs` 封面加 `loading="lazy"`。
4. `article_cente.less` 加 `video` 样式。

## 路径坑

- 正文相对路径 `../../assets/...` 渲染后变成 `/../../assets/...`（hexo 既有行为），浏览器会折叠成 `/assets/...`，可正常加载；与 jpg 行为一致，无需修复。

## 命令速查

```bash
# gif -> mp4
ffmpeg -y -i in.gif -c:v libx264 -pix_fmt yuv420p -crf 26 -movflags faststart out.mp4
# png -> webp
ffmpeg -y -i in.png -c:v libwebp -quality 80 -lossless 0 out.webp
# jpg 压缩
magick in.jpg -auto-orient -resize 2560x2560> -quality 82 -strip out.jpg
# 引用检查
node check-refs.js <hexo项目根路径>
```

## 当前脚本行为与验证（2026-10-31）

上述体积与人工修复属于历史案例。当前脚本保留 GIF/PNG 原件，只采用可解码且更小的结果，拒绝已有输出，不自动修改主题动态路径。JPG 在覆盖前保存原件及输出哈希至项目根 `.media-conversion-backup/`；同一输出不二次压缩，状态不符时报告失败。备份及状态不要提交或发布，保留状态才能识别已处理 JPG；删除备份前应明确承担后续重跑再次压缩的影响。

转换开始前先检查支持的本地引用，存在问题则不转换。单个媒体失败保留原件并继续其他文件，整次以非零状态报告；引用写入失败时原件仍可用，已生成结果不会自动清理，检查现场后再决定下一步。不保证跨文件事务、断电回滚或自动处理手工修改过的状态。

引用检查支持内联 Markdown（含尖括号路径）、带/不带引号的已列媒体字段、img/video/source 的 src/poster 与 CSS url；相对地址按来源文件位置解析，根路径按 source 解析，保留 URL 编码、查询参数与片段。不请求远程地址，不证明 HTTP 状态，不覆盖动态模板、srcset、引用式 Markdown 或 Hexo 自定义资源解析。发现缺失文件、越出 source 或运行失败时返回非零状态。

运行：

```text
node scripts/check-refs.js <hexo项目根路径>
node scripts/convert-media.js <hexo项目根路径>
node tests/test-media.js
```

隔离回归使用虚构路径与实际生成的媒体，验证完整路径、同名与扩展名边界、视频/未加引号字段、错误状态、保留原件、已有输出、JPG 重跑和损坏输入。没有对真实博客批量转换，也未验证所有主题、动图特性或视觉质量；透明度、动画时长/循环及有损画质仍需检查。
