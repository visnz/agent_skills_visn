# agent_skills_visn

我的个人 Agent 技能合集。把真实协作中验证有效的操作方法、需求和经验整理成可复用 skill，让后续助手更快理解我的工作方式，并把操作完成到可检查、可继续使用的结果。

目前从 Blender 开始；后续按需加入文本处理、After Effects 等领域。

## 技能索引

| 领域 | 技能 | 用途 | 状态 |
| --- | --- | --- | --- |
| Blender | [blender-workflow](blender/blender-workflow/SKILL.md) | 场景读取、多实例连接、跨工程复制、节点组资产入库和缩略图验证 | 已建立，来自一次实际入库操作 |
| 文本处理 | 待实际任务后添加 | 按真实需求积累编辑、整理与转换流程 | 规划中 |
| After Effects | 待实际任务后添加 | 按真实需求积累 AE 工程和操作经验 | 规划中 |

## 目录约定

```text
agent_skills_visn/
├── README.md
├── LICENSE
└── blender/
    └── blender-workflow/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        ├── scripts/
        │   └── blender_rpc.py
        └── references/
            ├── asset-library.md
            └── 2026-10-30-water-normal.md
```

按领域组织，每个可以独立使用的技能有自己的文件夹和 `SKILL.md`。后续可使用 `text/<skill-name>/`、`ae/<skill-name>/`；有实际技能时再创建，不提前堆放空模板。

- `SKILL.md`：说明何时使用、核心决策与完成标准。
- `references/`：按需读取的流程细节和真实案例。案例中的路径、端口和参数仅代表当时现场。
- `scripts/`：反复使用且经过检查的辅助脚本，具体参数和用途在技能中说明。
- `assets/`：确实需要交付模板或其他素材时再添加。

## 使用方式

仓库是技能源文件合集，放入仓库不等于已经安装到 Agent 的技能发现目录。可以直接让助手读取指定技能：

> 请读取这个仓库的 `blender/blender-workflow/SKILL.md`，从当前选中的节点开始，把它合并进我指定的资产库文件，保留参数并制作缩略图。

Codex 当前的用户级技能目录是 `~/.agents/skills/`，支持链接到仓库中的技能文件夹，并能在任务匹配技能描述时自动选用。[官方技能文档](https://learn.chatgpt.com/docs/build-skills)

本机采用 Windows 目录联接（junction），保持仓库为唯一维护来源：

```text
C:\Users\zyvis\.agents\skills\blender-workflow
  → C:\Users\zyvis\Documents\git\agent_skills_visn\blender\blender-workflow
```

新机器上可以在 PowerShell 中创建相同关联，按实际位置调整仓库路径：

```powershell
$skillSource = 'C:\Users\zyvis\Documents\git\agent_skills_visn\blender\blender-workflow'
$skillsDirectory = Join-Path $env:USERPROFILE '.agents\skills'
New-Item -ItemType Directory -Path $skillsDirectory -Force
New-Item -ItemType Junction -Path (Join-Path $skillsDirectory 'blender-workflow') -Target $skillSource
```

目标位置已有同名技能时先检查，不覆盖。`agents/openai.yaml` 显式设置 `allow_implicit_invocation: true`：相关 Blender 任务可自动选用，也可通过 `$blender-workflow` 明确指定。它并不强制所有包含 Blender 字样的请求都调用技能。

以后直接编辑仓库内容，或在仓库中 `git pull --ff-only`，已安装的关联会读取同一份文件。保留仓库目录位置；若移动或删除仓库，需要更新联接。技能安装后从下一轮开始可用；若客户端列表仍未刷新，重启 Codex。此前提到的 `~/.codex/skills` 是旧路径示例，本仓库现在采用上述官方用户级位置。

Blender 技能中的端口辅助脚本只依赖 Python 标准库：

```powershell
python blender/blender-workflow/scripts/blender_rpc.py inspect --port 9875
python blender/blender-workflow/scripts/blender_rpc.py run --port 9875 --expect-file 'D:\我的资产库\资产库.blend' --code-file 'C:\工作目录\本次操作.py'
```

第二条命令会在目标 Blender 中执行脚本，应先检查脚本内容；路径校验用于防止操作到另一个同名工程，不能替代文件写入权限或用户授权。

## 这份合集怎样记录我的习惯

从已发生的操作中提炼可执行规则，标清适用范围。本次 Blender 任务记录的需求是：

- 对“我选中的这个”先读取当前选择和界面，减少重复问路径与名称。
- 跨工程操作先核对实际文件路径，区分连接限制和产品能力。
- “入库”和“合并进主文件”要完成到对应结果，临时导出不能冒充完成。
- 保存用户当前调好的参数，让资产再次使用时有合理默认值。
- 需要缩略图时，查看实际效果并验证图片已嵌入、已保存。

这些是当前证据支持的需求；后续根据新的任务和明确反馈修订，不把一次性的参数或目录当成永久偏好。

## 后续新增或更新

1. 从一项真实任务出发，说明触发条件和用户想得到的结果。
2. 把可复用规则写进技能入口，技术细节和复盘按需拆入参考文件。
3. 脚本用参数接收端口和路径，避免绑定某个工程。记录实际验证，不宣称未完成的功能。
4. 更新本页技能索引，区分已经可用与仍在规划的内容。
5. 更新前保留原有内容；未经明确要求，不代替用户提交 Git、推送仓库或扩大外部操作范围。

## License

仓库授权以 [LICENSE](LICENSE) 为准。
