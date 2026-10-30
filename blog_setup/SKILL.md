---
name: blog-setup
description: 维护 visn 的 Hexo 博客（hexo_visn）。核心是优化图片/媒体流量：gif 转 mp4、png 转 webp、jpg 压缩、正文与封面懒加载；封面 gif 保留动图；转换后校验引用完整性。并遵守 git 协作规范：完成任务只报告结果，未经用户明确确认不 commit、不 push。适用于"优化博客图片流量""动图转视频""图片转 webp""加懒加载""引用 404""博客 git 代理"等任务。
---

# Hexo 博客维护与媒体优化

以 visn 的 Hexo 博客（`hexo_visn`）为工作对象。核心场景是降低每次访问的图片流量，同时保留有表达意图的动图，并把 git 协作规范落到可检查的结果。

## 什么时候用

- 优化博客图片/媒体体积：gif→mp4、png→webp、jpg 压缩、懒加载。
- 排查正文动图不播放、封面不显示、引用 404、`.webp.jpg` 误伤。
- 修改 hexo `scripts/` 下的 filter 或主题模板后需要重启 server。
- 为博客 git 配置代理（Clash）或准备提交/推送。

不适用：与 hexo 博客无关的通用图片处理；未经用户确认就 commit/push。

## 核心认知（先对齐）

1. **gif → mp4，而不是 animated WebP**：本机 ImageMagick/ffmpeg 转 animated WebP 体积往往大于原 gif；mp4（H.264, crf 26）约 -85% 且帧完整，前端用 `<video>` 渲染。小 gif 转 mp4 可能反而变大，先对比体积再决定。
2. **封面（cover）gif 是有意动图，保留不转**：首页/画廊卡片用 `<img src="cover">` 渲染，`<img>` 无法显示 mp4；把封面转成静态第一帧会丢失动图意图。转换脚本必须跳过 `cover:` 引用的 gif。
3. **basename 子串替换会误伤**：`title.png` 会匹配 `title.png.jpg`，产生 `.webp.jpg` 错误引用。转换后必须跑引用完整性检查。
4. **hexo scripts filter 不热重载**：`scripts/media.js` 等 filter 变更后必须重启 `hexo server`；md 与主题模板变更会被 watch 自动重新渲染。
5. **git 规范**：完成任务只报告结果，等用户明确说"可以 commit/push"再执行；绝不擅自 commit 或 push。

## 媒体转换流程

按需选择步骤；参数与坑详见 [references/media-conversion.md](references/media-conversion.md)；脚本在 [scripts/](scripts/) 下，用项目根路径作为参数运行。

1. **gif → mp4**：跳过 `cover:` 引用的封面 gif，其余用 `ffmpeg -i x.gif -c:v libx264 -pix_fmt yuv420p -crf 26 -movflags faststart x.mp4`，成功后删 gif 并替换引用。
2. **png → webp**：`ffmpeg -i x.png -c:v libwebp -quality 80 -lossless 0 x.webp`。
3. **jpg 原地压缩**：`magick x.jpg -auto-orient -resize 2560x2560> -quality 82 -strip x.jpg`，只处理 >400KB 大图，避免小图二次劣化。
4. **替换引用 + 校验**：用 basename 映射替换 md/yml/json 引用，跑 [scripts/check-refs.js](scripts/check-refs.js) 确认 0 个 404。
5. **前端懒加载**：正文 filter 把 `<img src="*.mp4">` 转 `<video loop muted playsinline preload="none">`，其余 `<img>` 注入 `loading="lazy"`；前端 IntersectionObserver 懒播放视频；首页/画廊封面加 `loading="lazy"`。

## 关键决策点（需要问用户的）

1. 封面动图是否保留：遇到封面是 gif 时，先确认是否保留动图（默认保留）。
2. 压缩力度：有损压缩（q80/q82）是否可接受，还是要求无损。
3. git 提交/推送：先报告改动清单与验证结果，等用户明确确认再执行。

## 完成标准

- 报告转换前后体积对比（图片、媒体总体积与节省比例）。
- [scripts/check-refs.js](scripts/check-refs.js) 通过（0 个 404），`.webp.jpg` 等误伤已修复。
- 页面渲染已验证：正文动图为 `<video>`，封面为 gif/静态图且带 `loading="lazy"`。
- 未擅自 commit/push；需要提交时先报告、等确认。

## 约束与边界

- 脚本用项目根路径作参数，不硬编码某台机器的绝对路径。
- 历史案例中的路径、端口、参数仅代表当时现场，执行前重新确认。
- 不擅自清理用户数据、不覆盖同名文件、不修改全局 git 配置。
