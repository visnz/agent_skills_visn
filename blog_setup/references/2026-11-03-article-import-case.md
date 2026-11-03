# 2026-11-03：Blender 技术文章导入案例

本案例记录 `hexo_visn` 一次本地 TXT 原稿及配图导入。可复用方法见 [文章导入流程](article-import.md)；以下目录、排序值和结果只代表当时站点。

## 输入与处理

- 输入为 `markdown-to-import/` 下的 Blender 5.2 原稿及两张 PNG；原稿保留。按当前 Blender 文章格式写入 `source/_posts/blog/CG/Blender/`，把配图复制到 `source/assets/blog/CG/Blender/`，更新 `cover` 和正文图片路径。
- 原稿写到 `Math: Add（Clamp）`，截图里却显示 `Shader to RGB` 直接连接 `Greater Than`。导入时保留作者原文并指出差异；这次没有独立复现实验或确认差异原因。
- 首次生成的文章详情可访问，但首页未显示在第一页。检查当前 `hexo-generator-index-pin-top` 的比较逻辑及 60 篇既有普通文章，发现它们都有 `top: 300`，新文章没有。加上相同的 `top` 后，按日期排到首页首位。

## 实际验证与边界

`npm run build` 成功；运行 `hexo server` 后，文章页和两张图片均返回 HTTP 200，首页第一张卡片为新文章。作者在浏览器检查后确认可用。随后文章、图片和开发日志已提交到 `hexo_visn` 的 `main` 并推送到 `origin/main`，提交为 `b990c48`。这些检查没有验证原稿技术结论的跨版本稳定性，也不能推出其他 Hexo 站点应使用 `top: 300`。
