# 社区来源选择与验证记录

核对日期：2026-10-31。这是来源与能力边界记录，不是第三方技能正文，也没有把这些项目 fork 或复制进个人仓库。

## 评估过的来源

| 项目 | 已核对的特点 | 本次处理 |
| --- | --- | --- |
| [EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills) | MIT；基础 + 21 个专题；Blender 5.2+；含脚本、参考、扩展模板和测试 | 作为默认按需来源，固定 commit 和文件哈希 |
| [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) | MIT；README 描述 30 份串联技能；有参考图重建、外观校准和双 MCP 路由；明确公布部分测试限制 | 备选；未收录自动下载索引，不混用它的调度器与当前个人调度 |
| [MartinRapcan/blender-claude-skill](https://github.com/MartinRapcan/blender-claude-skill) | MIT；已读取入口，侧重 headless bpy、几何、材质、灯光和渲染验证 | 适合偏后台脚本的参考；未作为实时工程操作的默认入口 |
| [capybala18/capybala-bpy-skill](https://github.com/capybala18/capybala-bpy-skill) | 仓库声明 MIT，侧重后台建模、曝光与几何 QA | 仅核对仓库介绍，未完成脚本实测，不纳入自动加载名单 |

不能把仓库星数、作者自述或“有测试”直接当作生产质量保证。默认来源目前历史仍较短；选择它是因为专题覆盖、模块结构和本次实际兼容性，而不是承诺它最成熟或最优。

## 默认来源固定记录

- 上游：`https://github.com/EL4CTEO/blender-skills`
- commit：`71d031dab8bc6729504d11a78cbe91945401045f`
- 技能声明版本：`1.1.0`
- 许可：MIT，下载时附上游原始 `LICENSE`，不把本仓库许可证套给外部缓存。
- 索引：22 个真实技能名和各自文件 SHA-256，记录在 `community-skills.json`；无第三方技能正文、脚本或模板保存在个人仓库。

## 本机验证

本机 Blender：5.2.3 LTS；Windows；独立后台进程，factory startup，不修改用户已打开工程。

1. 上游 `tools/validate_skills.py --strict`：22 个技能通过，名称、frontmatter、相对链接、脚本语法和共享辅助文件一致性均通过其检查。
2. 上游测试首轮受沙箱临时目录写入限制，不能把这一轮归因于代码兼容性；按环境权限要求取得批准后重跑。
3. 开启 `BAS_SKIP_GPU=1`：47 passed、0 failed、3 skipped。
4. 补测开启图形上下文，`BAS_SKIP_GPU=0`：**50 passed、0 failed、0 skipped**，包括灯光转台、Cycles/EEVEE/Workbench 渲染、骨架绑定、扩展模板、导出、节点与模拟。
5. 单独测试基础 runner 载入一个临时 `.blend` 并读取文件路径和节点组数量，确认它能读取传入文件。
6. 本仓库下载器实际取回 core、scene-setup、pbr-materials 和许可证，共 14 个文件，全部通过固定哈希校验；在禁止联网的验证中完整复用这 14 个缓存文件。另验证未知技能、仓库内缓存路径、已改动缓存均会被拒绝，读取顺序为基础在先、个人入口在后。

示例复现命令（在上游独立 checkout 下运行，`BLENDER_EXE` 按机器调整）：

```powershell
$env:BLENDER_EXE = 'D:\SteamLibrary\steamapps\common\Blender\blender.exe'
$env:BAS_SKIP_GPU = '0'
python -X utf8 tools/validate_skills.py --strict
python -X utf8 tools/run_tests.py
```

测试通过说明这些测试覆盖的 API 和行为在本机有效。未验证其他 Blender/Agent 版本、任意复杂角色的美术质量、所有第三方扩展或生产场景兼容性。常规加载无需 clone 整个上游或运行测试；按需下载器只取本次所需文件。
