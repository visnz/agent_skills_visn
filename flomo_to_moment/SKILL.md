---
name: flomo-to-moment
description: 把 flomo 导出的 zip 同步成 visn Hexo 博客的「铭记」说说。解析 flomo 导出格式（文件名时间戳、正文首行【标题】、#标签 行、原文链接、images 图片），生成 source/_posts/moment 下的帖子，搬运图片，差异化更新（只新增与覆盖、不删除），并写运行日志。适用于"同步 flomo""flomo 转说说""更新铭记说说"等任务。
---

# flomo 同步到「铭记」说说

把 flomo 导出的 zip 转成 visn 博客（`hexo_visn`）的「铭记」（moment）说说。核心场景是用户从 flomo 导出一批 memo，不想手写 markdown，而是用脚本直接同步成博客说说。

## 什么时候用

- 用户提供 flomo 导出 zip（放在 `moments_update/flomo_fetch/`），要同步成说说。
- 更新说说内容（flomo 里改了字、调了顺序、加了【标题】等改版）。
- 排查说说内容、图片引用、日期、标题问题。

不适用：与 flomo 说说无关的博客媒体优化（用 blog-setup）；未经用户确认删除说说。

## 核心认知（先对齐）

1. **flomo 导出有固定结构**：文件名 `YYYYMMDDHHMM_序号.md` 即创建时间；正文首行可能是 `【标题】`；正文里混有 `#标签` 行（`#` 后无空格）和末行原文链接 `[日期](https://flomoapp.com/mine/?memo_id=...)`；图片在 `images/` 下相对引用。细节与案例见 [references/flomo-format.md](references/flomo-format.md)。

2. **说说 front-matter**：`type: moment` + `date` + `title`（可选）+ `photos`（数组）。说说由项目 `scripts/content-types.js` 识别 `type: moment`，渲染到「铭记」页；图片放 `source/assets/moment/`。

3. **差异化更新，只增改、不删除**：以文件名时间戳为唯一标识；新增和覆盖更新自动写入，**绝不执行删除**（zip 里消失的旧说说由用户手动删除）。这是用户的明确要求。

4. **脚本参数化项目路径**：脚本放在技能库，运行时传入项目根路径，不绑定某台机器。

## 执行流程

1. 确认 zip 在 `<项目>/moments_update/flomo_fetch/`。
2. 运行 `python scripts/flomo_to_moment.py <项目根路径>`。
3. 脚本自动：解压 → 解析每条 memo → 生成/更新 `source/_posts/moment/YYYYMMDDHHMM.md` → 搬运图片 → 输出「新增/更新/未变」报告。
4. 运行日志写在 `<项目>/moments_update/flomo_to_moment.log`（含时间戳与异常 traceback），出错时把该文件交给用户排查。
5. 用户预览确认后，按 git 协作规范（不擅自 commit/push）处理提交。

## 关键决策点

- 说说标题：flomo 首行 `【标题】` 自动提取为 `title` 并移除该行；没有则不写 `title`。
- 删除：脚本不做删除。发现 zip 里消失的旧说说，提醒用户手动删除。
- 图片重名：同名图片直接覆盖（文件名带时间戳，冲突概率低）。

## 完成标准

- 脚本运行后报告「新增/更新/未变」数量与时间戳清单。
- 生成的说说 front-matter 正确（date/type/title/photos），图片已复制到 `source/assets/moment/`。
- 运行日志存在且 UTF-8 可读。
- 未擅自 commit/push；需要提交时先报告、等确认。

## 约束与边界

- 脚本仅用 Python 标准库，无第三方依赖。
- 路径、端口等现场信息执行前重新确认，历史案例不代表当前现场。
- 不覆盖用户的非脚本改动；同时间戳多条 memo 时警告并保留后者。
