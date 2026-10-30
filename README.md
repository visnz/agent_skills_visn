# agent_skills_visn

我的个人 Agent 技能合集。把真实协作中验证有效的操作方法、需求和经验整理成可复用 skill，让后续助手更快理解我的工作方式，并把操作完成到可检查、可继续使用的结果。

目前从 Blender 开始；后续按需加入文本处理、After Effects 等领域。

## 技能索引

按领域组织长期积累的复用技能；临时性的综合任务单独列在下方「特殊任务」。

| 领域 | 技能 | 用途 |
| --- | --- | --- |
| Blender | [blender-workflow](blender/blender-workflow/SKILL.md) | 按任务下载社区基础/专题，再执行个人场景、多实例、资产入库与缩略图工作流 |
| Blender | [blender-addon-maintenance](blender/addon-development/SKILL.md) | 多人协作插件仓库里开发 operator/面板：模块归属与改动边界、分支与合并、留档，用真实 Blender 连接做端到端验证 |
| 博客 | [blog-setup](blog_setup/SKILL.md) | Hexo 博客维护与媒体流量优化（gif→mp4、png→webp、jpg 压缩、懒加载、引用校验、git 规范） |
| 博客 | [flomo-to-moment](flomo_to_moment/SKILL.md) | 把 flomo 导出 zip 同步成「铭记」说说（格式解析、图片搬运、差异化更新） |
| 文本处理 | 待实际任务后添加 | 按真实需求积累编辑、整理与转换流程 |
| After Effects | 待实际任务后添加 | 按真实需求积累 AE 工程和操作经验 |

### 特殊任务

一次性或临时性的综合需求，跨多个步骤/领域，按需沉淀、不进入长期技能索引：

1. [wechat-corpus-export](Special_Missions/微信聊天记录提取语料/SKILL.md) —— 微信 4.x 聊天记录解密导出、清洗成 A/B 对话语料（切片、场景分类、隐私提示）。

## 目录约定

```text
agent_skills_visn/
├── README.md
├── AGENTS.md
├── docs/
│   └── skill-building.md
├── LICENSE
├── blender/
│   ├── blender-workflow/
│   │   ├── SKILL.md
│   │   ├── community-skills.json
│   │   ├── agents/
│   │   │   └── openai.yaml
│   │   ├── scripts/
│   │   │   ├── blender_rpc.py
│   │   │   └── prepare_community_skills.py
│   │   └── references/
│   │       ├── asset-library.md
│   │       ├── 2026-10-30-water-normal.md
│   │       ├── community-routing.md
│   │       └── community-sources.md
│   └── addon-development/
│       ├── SKILL.md
│       ├── agents/
│       │   └── openai.yaml
│       └── references/
│           ├── repo-collaboration.md
│           ├── mcp-live-testing.md
│           ├── world-space-bbox.md
│           └── 2026-10-31-pond-bekkan-case.md
└── blog_setup/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── scripts/
    │   ├── convert-media.js
    │   └── check-refs.js
    └── references/
        ├── media-conversion.md
        └── git-collaboration.md
└── flomo_to_moment/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── scripts/
    │   └── flomo_to_moment.py
    └── references/
        └── flomo-format.md
```

按领域组织，每个可以独立使用的技能有自己的文件夹和 `SKILL.md`。后续可使用 `text/<skill-name>/`、`ae/<skill-name>/`；有实际技能时再创建，不提前堆放空模板。

- `SKILL.md`：说明何时使用、核心决策与完成标准。
- `references/`：按需读取的流程细节和真实案例。案例中的路径、端口和参数仅代表当时现场。
- `scripts/`：反复使用且经过检查的辅助脚本，具体参数和用途在技能中说明。
- `assets/`：确实需要交付模板或其他素材时再添加。

## 使用方式

仓库是技能源文件合集，放入仓库不等于已经安装到 Agent 的技能发现目录。可以直接让助手读取指定技能：

> 请读取这个仓库的 `blender/blender-workflow/SKILL.md`，从当前选中的节点开始，把它合并进我指定的资产库文件，保留参数并制作缩略图。

### Blender 社区技能：需要时由 Agent 下载

本仓库不 fork 或收存社区技能源码，只维护个人规则、专题分流、来源版本与下载器。其他 Agent clone 后读取上面的技能入口，即可分析任务、按需下载并读取相关技能，再开始执行。

```text
读取个人入口并判断任务
  → 只读查询可先用现有工具；修改/交付前下载或离线读取 blender-core
  → 下载/读取当前阶段所需专题
  → 应用个人工作流和本次用户要求
  → 检查现场、执行、验证
```

默认社区来源为 [EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills)。基础技能和 21 个专题按固定 commit 下载到仓库外缓存，配套脚本、参考和许可证一起获取；下载器不执行远端代码，也不全局安装全部专题。固定版本和哈希位于 [community-skills.json](blender/blender-workflow/community-skills.json)。

在 clone 的仓库根目录下，例如资产整理需要场景和材质专题：

```powershell
python blender/blender-workflow/scripts/prepare_community_skills.py --list
python blender/blender-workflow/scripts/prepare_community_skills.py --skills blender-scene-setup blender-pbr-materials
```

`blender-core` 自动加入；Agent 必须实际读取输出 JSON 的 `load_order`，不能将“已下载”当成“已加载”。默认使用系统临时缓存；可加 `--cache-dir` 指向仓库外的持久可写目录。重复使用校验缓存，无需联网；无网络且无完整缓存时会明确失败，不伪装装载成功。Blender/MCP 运行能力仍由当前机器或宿主提供。

常见方向包括角色雕刻 `blender-sculpting`、角色绑定 `blender-character-rigging`、灯光 `blender-lighting-lookdev`、渲染 `blender-rendering`、材质 `blender-pbr-materials`、插件开发 `blender-addon-development` 等。完整分流与组合见 [社区技能分流表](blender/blender-workflow/references/community-routing.md)，经验归档和后续拆分条件见 [Blender 技能维护](blender/blender-workflow/references/skill-maintenance.md)。缺少完整缓存或版本不适用时可继续独立只读查询，依赖缺失资料的修改/交付步骤暂停；筛选理由、其他候选和本机 50 项测试记录见 [来源与验证](blender/blender-workflow/references/community-sources.md)。

### 在 Codex 中关联安装个人入口

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

## 技能建设约定

每次真实任务结束都可以复盘，但不要求每次新增 Skill。先判断经验是否会改善后续任务，再选择更新已有技能、补充参考资料、修正脚本、保存案例或待验证记录、新建技能，或无需修改。

- 从具体触发场景和用户目标出发，检查已有技能，优先更新能够合理容纳该经验的内容。
- 区分通用规则、条件性流程、可执行脚本、历史案例和待验证判断；一次任务的路径、参数与工具行为不自动成为通用要求。
- 每条规则说明必要的适用条件和验证依据。区分观察到的事实、推测原因，以及本次有效和后续实践中再次验证有效。
- 维护说明与实际能力的一致性，检查入口、引用和脚本；不宣称未验证或尚未实现的能力。
- 按任务规模记录，微调不必另建复盘文件；没有新增可复用信息时，可以明确无需修改。

详细判断问题、归档选择、验证及交付要求见 [技能建设规范](docs/skill-building.md)。Agent 在本仓库新增或更新技能前，应遵循 [AGENTS.md](AGENTS.md) 并读取该规范。README 负责介绍与导航，详细方法统一在规范中维护。

## 后续新增或更新

1. 从一项真实任务出发，说明触发条件和用户想得到的结果。
2. 把可复用规则写进技能入口，技术细节和复盘按需拆入参考文件。
3. 脚本用参数接收端口和路径，避免绑定某个工程。记录实际验证，不宣称未完成的功能。
4. 更新本页技能索引，区分已经可用与仍在规划的内容。
5. 更新前保留原有内容；未经明确要求，不代替用户提交 Git、推送仓库或扩大外部操作范围。

## License

仓库授权以 [LICENSE](LICENSE) 为准。

## 任务规模、沉淀提醒与特殊任务

- 开始执行前先粗估工作量、需要的上下文和验证成本；工作范围明显扩大时重新评估。预计涉及大批量文件、反复长链试错、长时间运行或大量资料装载时，先反馈范围、主要成本与可缩小方案，等待用户选择后开展高成本部分。不虚构精确 token 消耗。
- 一项较完整、较大的任务结束或接近结束，且确有值得复用的新经验时，提醒一次并询问是否按本 README 及建设规范整理技能。小修、普通问答和同一任务的中间步骤不反复提醒；用户已经要求整理时直接完成，无需再问。
- `Special_Missions` 允许保存任务专用流程、明确限定的环境参数与特殊经验，不要求都推广为通用技能。仍须区分事实和推测、如实声明验证范围，并保证脚本和说明一致。

这些约定适用于读到本仓库规则的 Agent。若希望其他项目也普遍遵守，应在相应项目或用户级规则中明确引用；仅修改本仓库 README 不会自动约束所有对话。
