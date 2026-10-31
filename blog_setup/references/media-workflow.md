# 博客媒体优化流程

仅在媒体体积、动图、懒加载和媒体引用任务中读取。以下保留原博客入口的媒体经验；历史节省比例只代表案例，当前参数应按目标效果选择。

## 已有经验


1. **gif → mp4，而不是 animated WebP**：本机 ImageMagick/ffmpeg 转 animated WebP 体积往往大于原 gif；mp4（H.264, crf 26）约 -85% 且帧完整，前端用 `<video>` 渲染。小 gif 转 mp4 可能反而变大，先对比体积再决定。
2. **封面（cover）gif 是有意动图，保留不转**：首页/画廊卡片用 `<img src="cover">` 渲染，`<img>` 无法显示 mp4；把封面转成静态第一帧会丢失动图意图。转换脚本必须跳过 `cover:` 引用的 gif。
3. **basename 子串替换会误伤**：`title.png` 会匹配 `title.png.jpg`，产生 `.webp.jpg` 错误引用。转换后必须跑引用完整性检查。
4. **hexo scripts filter 不热重载**：`scripts/media.js` 等 filter 变更后必须重启 `hexo server`；md 与主题模板变更会被 watch 自动重新渲染。
5. **Git**：按用户本次授权执行，未授权不提交或推送；详见 [Git 协作参考](git-collaboration.md)。

## 媒体转换流程

按需选择步骤；参数与坑详见 [媒体转换案例与参数](media-conversion.md)；脚本在 [scripts/](../scripts/) 下，用项目根路径作为参数运行。

1. **gif → mp4**：跳过 `cover:` 引用的封面 gif，其余用 `ffmpeg -i x.gif -c:v libx264 -pix_fmt yuv420p -crf 26 -movflags faststart x.mp4`，先验证可解码且体积更小，再按完整路径替换支持的引用；保留原 gif。
2. **png → webp**：采用 q80 的候选结果前检查可解码和体积；保留原 png，已有同名输出则跳过。
3. **jpg 原地压缩**：`magick x.jpg -auto-orient -resize 2560x2560> -quality 82 -strip candidate.jpg`，只处理 >400KB 大图；候选有效且更小时才采用。脚本在项目根 `.media-conversion-backup/` 保存原件与输出哈希，同一结果重跑不再次压缩；原文件变化则停止处理该文件并报告。该目录不应提交或发布。
4. **替换引用 + 校验**：用 [scripts/media-refs.js](../scripts/media-refs.js) 按解析后的完整路径替换 md/yml/yaml/json/html/css 中支持的媒体引用，保留查询参数和片段；跑 [scripts/check-refs.js](../scripts/check-refs.js) 初筛。动态主题模板、srcset、引用式 Markdown 需另查，不再批量修改 categories.ejs。
5. **前端懒加载**：正文 filter 把 `<img src="*.mp4">` 转 `<video loop muted playsinline preload="none">`，其余 `<img>` 注入 `loading="lazy"`；前端 IntersectionObserver 懒播放视频；首页/画廊封面加 `loading="lazy"`。

## 按现有授权作出选择

1. 封面动图默认保留；本次意图与现有模板确实无法确定时再确认，不重复询问已有选择。
2. 压缩力度：有损压缩（q80/q82）是否可接受，还是要求无损。
3. Git 提交/推送按本次明确授权执行；未授权时只报告结果，不重复索取同一授权。

## 完成标准

- 报告已采用文件的转换前后体积、跳过与失败情况。原始 GIF/PNG 保留会增加磁盘占用，不能将采用文件的减少量宣称为磁盘或整站流量的实际节省。
- [scripts/check-refs.js](../scripts/check-refs.js) 在支持的本地引用范围内通过；问题或运行错误返回非零状态。不将此结果称为全站 0 个 404；远程地址、生成页面和未覆盖语法另行验证。
- 页面渲染已验证：正文动图为 `<video>`，封面为 gif/静态图且带 `loading="lazy"`。
- 未超出本次 Git 授权；如已授权提交或推送，分别核对实际结果。


依赖 Node.js 18+、ffmpeg、ffprobe、ImageMagick。在技能根目录运行 `node tests/test-media.js` 做隔离回归；预览和人工视觉核对不可由引用检查替代。
