# git 协作规范与代理配置

## 不擅自 commit/push

以下等待确认适用于尚未授权的情况；用户已经明确要求提交或推送时，按该范围执行，不因本参考再次索取同一授权。

- 完成任务后**只报告结果**（改动清单、验证结果、体积对比等）。
- 等用户明确说"可以 commit""帮我 push"后，才执行 `git commit` / `git push`。
- 2026-10-30 曾因擅自 commit 被用户纠正，之后改为先报告、等确认。

## 合并多个 commit 为一个

```bash
git reset --soft <基线commit>
git commit -m "合并后的提交信息"
```

`--soft` 把 HEAD 移到基线，改动回到暂存区、工作区不变，再 commit 即合并为一个。

注意：`git checkout <历史commit> -- <路径>` 恢复被删除的文件时，文件在更早的 commit（如 HEAD~2）而非 HEAD~1，先用 `git ls-tree -r <commit> -- <目录>` 确认确切路径。

## 代理配置（Windows + Clash）

- 系统代理：Clash 混合端口 `127.0.0.1:7897`（按实际端口调整，可用 `Test-NetConnection 127.0.0.1 -Port 7897` 验证监听）。
- git 直连 GitHub 会被重置（`Recv failure: Connection was reset`），需要为仓库配置代理：

```bash
git config http.proxy http://127.0.0.1:7897
git config https.proxy http://127.0.0.1:7897
```

- 查看/取消：

```bash
git config --get http.proxy
git config --unset http.proxy
```

- 备选：Linux/WSL 里用 `proxychains4 git push`（本机 WSL 未安装 proxychains，需先安装）。

## 多分支部署与 rebase（main + moments_update）

hexo_visn 站点 workflow 监听 `main` 与 `moments_update` 两个分支的 push，都触发部署：

- `moments_update` 承载高频小更新（如说说），`main` 保持"少而重要"。
- `moments_update` push 时，CI 先 `git merge origin/main` 拉入 main 再构建，避免其生成的聚合页（首页/归档/分类/标签）覆盖掉 main 上新文章的入口。
- main 有重要更新后，`moments_update` 需 rebase 到新 main：`git checkout moments_update && git rebase main && git push origin moments_update`（fast-forward 时普通 push 即可，无需 force）。
- 合并时机由开发者掌控：push 到 main 前先询问是否合并 `moments_update`。
