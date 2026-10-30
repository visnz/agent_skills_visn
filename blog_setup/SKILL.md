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

1. **gif → mp4**：跳过 `cover:` 引用的封面 gif，其余用 `ffmpeg -i x.gif -c:v libx264 -pix_fmt yuv420p -crf 26 -movflags faststart x.mp4`，先验证可解码且体积更小，再按完整路径替换支持的引用；保留原 gif。
2. **png → webp**：采用 q80 的候选结果前检查可解码和体积；保留原 png，已有同名输出则跳过。
3. **jpg 原地压缩**：`magick x.jpg -auto-orient -resize 2560x2560> -quality 82 -strip x.jpg`，只处理 >400KB 大图；候选有效且更小时才采用。脚本在项目根 `.media-conversion-backup/` 保存原件与输出哈希，同一结果重跑不再次压缩；原文件变化则停止处理该文件并报告。该目录不应提交或发布。
4. **替换引用 + 校验**：用 [scripts/media-refs.js](scripts/media-refs.js) 按解析后的完整路径替换 md/yml/yaml/json/html/css 中支持的媒体引用，保留查询参数和片段；跑 [scripts/check-refs.js](scripts/check-refs.js) 初筛。动态主题模板、srcset、引用式 Markdown 需另查，不再批量修改 categories.ejs。
5. **前端懒加载**：正文 filter 把 `<img src="*.mp4">` 转 `<video loop muted playsinline preload="none">`，其余 `<img>` 注入 `loading="lazy"`；前端 IntersectionObserver 懒播放视频；首页/画廊封面加 `loading="lazy"`。

## 关键决策点（需要问用户的）

1. 封面动图是否保留：遇到封面是 gif 时，先确认是否保留动图（默认保留）。
2. 压缩力度：有损压缩（q80/q82）是否可接受，还是要求无损。
3. git 提交/推送：先报告改动清单与验证结果，等用户明确确认再执行。

## 完成标准

- 报告已采用文件的转换前后体积、跳过与失败情况。原始 GIF/PNG 保留会增加磁盘占用，不能将采用文件的减少量宣称为磁盘或整站流量的实际节省。
- [scripts/check-refs.js](scripts/check-refs.js) 在支持的本地引用范围内通过；问题或运行错误返回非零状态。不将此结果称为全站 0 个 404；远程地址、生成页面和未覆盖语法另行验证。
- 页面渲染已验证：正文动图为 `<video>`，封面为 gif/静态图且带 `loading="lazy"`。
- 未擅自 commit/push；需要提交时先报告、等确认。

## 约束与边界

- 脚本用项目根路径作参数，不硬编码某台机器的绝对路径。
- 历史案例中的路径、端口、参数仅代表当时现场，执行前重新确认。
- 不擅自清理用户数据、不覆盖同名文件、不修改全局 git 配置。

脚本依赖 Node.js 18+、ffmpeg、ffprobe、ImageMagick（magick）。从技能目录运行 `node scripts/convert-media.js <项目根>`；回归样例运行 `node tests/test-media.js`，只在临时目录生成媒体，不处理真实博客。自动验证不替代视觉检查，人工确认前不清理原件。
