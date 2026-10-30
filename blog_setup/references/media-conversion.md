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
- 脚本用 `findCoverGifs()` 扫描 `cover:` 引用，跳过这些 gif 的转换。
- 案例：`blender_RimClamp.md` 的封面+正文共用同一个 gif，用户要求保留 gif 动图。

## basename 子串替换的坑

- `title.png` 会误伤 `title.png.jpg`（basename 子串匹配），产生 `.webp.jpg` 错误引用。
- 案例：转换后出现 6 处 `.webp.jpg`（title 3 处 + Reel2024 3 处），全部手工修复。
- 修复：转换后跑 `check-refs.js`，它会报告所有疑似 404。

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
