# agent_skills_visn

我的个人 Agent 技能合集。把真实协作中验证有效的操作方法、需求和经验整理成可复用 skill，让后续助手更快理解我的工作方式，并把操作完成到可检查、可继续使用的结果。

目前包含概念设计、Blender、3D 打印、Style3D、After Effects、博客等领域；后续按实际任务继续积累。

## 技能索引

按领域组织长期积累的复用技能；临时性的综合任务单独列在下方「特殊任务」。

| 领域 | 技能 | 用途 |
| --- | --- | --- |
| 概念设计 | [concept-design-workflow](concept-design/concept-design-workflow/SKILL.md) | 概念设计协作总入口；已沉淀美术考究与图片选型偏好，预留氛围图、细节改进、概念脑洞联想模块，按后续实际任务逐步完善 |
| Blender | [blender-workflow](blender/blender-workflow/SKILL.md) | 按需社区专题与个人场景保留；参考图白盒、静态帧构图与比例校正、工程性能分析、几何节点创建与效果诊断/迁移/简化、多实例、资产入库与缩略图验证 |
| Blender | [blender-character-posing](blender/blender-character-posing/SKILL.md) | 给已有骨架角色按参考或动作意图摆静态姿势，检查手势、摄像机轮廓与道具接触 |
| Blender | [blender-addon-maintenance](blender/addon-development/SKILL.md) | 多人协作插件仓库里开发 operator/面板：模块归属与改动边界、分支与合并、留档，用真实 Blender 连接做端到端验证 |
| 3D 打印 | [3d-print-analysis](3dprinter/3d-print-analysis/SKILL.md) | 分析与优化打印：结合模型、切片、实物及过程定位问题；按需装载相关技能，打印导向建模经验留在 `3dprinter/` |
| Style3D 建模 | [style3d-garment-workflow](style3d/style3d-garment-workflow/SKILL.md) | 参考图分件、纸样与模拟验收；结合 ChatGarment 样例判断初稿价值 |
| 博客 | [blog-setup](blog_setup/SKILL.md) | Hexo 博客持续维护：媒体优化、flomo 铭记同步、内容/主题与构建检查、Git 协作 |
| 文本处理 | 待实际任务后添加 | 按真实需求积累编辑、整理与转换流程 |
| After Effects | [ae-mcp-workflow](ae/ae-mcp-workflow/SKILL.md) | 通过 AE MCP 核对连接与当前工程，按参考视频用可编辑形状和缩放制作动效，并验证渲染交付 |

### 特殊任务

一次性或临时性的综合需求，跨多个步骤/领域，按需沉淀、不进入长期技能索引：

1. [wechat-chat-export](Special_Missions/微信聊天记录提取语料/SKILL.md) —— 微信 4.x 聊天记录解密导出，两条分支：(1) 可离线浏览的 HTML 归档（文字/图片/语音/文件/自定义表情全量还原）；(2) A/B 对话语料（切片、场景分类、隐私提示）。
2. [auto-collect-triage](Special_Missions/自动剪藏素材分流/SKILL.md) —— 把「剪藏 → 手动搬运进素材库」自动化成本地脚本：读剪藏链接 → 下载视频/图片 → 入库 Eagle（打标签/记来源）→ 确认成功后再删源词条。沉淀「先确认两端接口能力再定架构、本地脚本优先于服务器常驻、入库成功后确认再删源」等方法论，以及多 Python 环境/下载器去重/MCP 中文编码等踩坑。

## 目录约定

```text
agent_skills_visn/
├── README.md / AGENTS.md
├── docs/skill-building.md
├── concept-design/concept-design-workflow/SKILL.md
├── blender/
│   ├── blender-workflow/SKILL.md
│   ├── blender-character-posing/SKILL.md
│   └── addon-development/SKILL.md
├── style3d/style3d-garment-workflow/SKILL.md
├── ae/ae-mcp-workflow/SKILL.md
├── blog_setup/SKILL.md
├── Special_Missions/微信聊天记录提取语料/SKILL.md   # 微信聊天记录导出（HTML归档 + 语料两分支）
├── Special_Missions/自动剪藏素材分流/SKILL.md       # 剪藏→素材库自动化脚本（下载/入库/删源）
└── flomo_to_moment/    旧命令兼容入口，无独立 Skill
```

按领域组织，每个可以独立使用的技能有自己的文件夹和 `SKILL.md`。后续可使用 `text/<skill-name>/`；有实际技能时再创建，不提前堆放空模板。已有角色摆静态动作可直接读 [blender-character-posing](blender/blender-character-posing/SKILL.md)，连接和社区资料的通用规则仍由 Blender 总入口维护。

- `SKILL.md`：说明何时使用、核心决策与完成标准。
- `references/`：按需读取的流程细节和真实案例。案例中的路径、端口和参数仅代表当时现场。
- `scripts/`：反复使用且经过检查的辅助脚本，具体参数和用途在技能中说明。
- `assets/`：确实需要交付模板或其他素材时再添加。

## 使用方式

仓库是技能源文件合集，放入仓库不等于已经安装到 Agent 的技能发现目录。可以直接让助手读取指定技能：

> 请读取这个仓库的 `blender/blender-workflow/SKILL.md`，从当前选中的节点开始，把它合并进我指定的资产库文件，保留参数并制作缩略图。

### 概念设计：按工作模块逐步完善

读取 [concept-design-workflow](concept-design/concept-design-workflow/SKILL.md)，先区分本轮是美术考究、氛围图、细节改进还是概念脑洞联想。当前已沉淀美术考究专题及图片驱动的协作偏好，其他模块只预留位置，随实际任务逐步完善。选型时按“用户提供图片 → 识别与分块 → 判断可用部分 → 推荐组合与必要调整”推进；沿用创作精度，重点排除明显冲突，不把其他概念设计工作一律转成考据。

该入口处理视觉决策；需要在具体软件中拼装或搭建时，再进入对应操作技能。未公开项目的经验只以通用方法和[脱敏情境](concept-design/concept-design-workflow/references/anonymized-scenarios.md)保留，不附原始素材或可还原的项目描述。

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

常见方向包括角色雕刻 `blender-sculpting`、角色绑定 `blender-character-rigging`、灯光 `blender-lighting-lookdev`、渲染 `blender-rendering`、材质 `blender-pbr-materials`、插件开发 `blender-addon-development` 等。完整分流与组合见 [社区技能分流表](blender/blender-workflow/references/community-routing.md)，经验归档和后续拆分条件见 [Blender 技能维护](blender/blender-workflow/references/skill-maintenance.md)。个人资产操作分为[节点提炼入库](blender/blender-workflow/references/asset-library.md)和[既有资产同步](blender/blender-workflow/references/asset-sync.md)，后者明确依赖检查、库内布局保留与驱动联动验证。既有场景的节点失效、效果迁移、界面简化和基础粒子改造另读[节点效果工作流](blender/blender-workflow/references/procedural-node-effects.md)；[天空、涟漪与粒子案例](blender/blender-workflow/references/2026-10-30-node-effects.md)保留本次证据及未解决的视觉/边界限制。缺少完整缓存或版本不适用时可继续独立只读查询，依赖缺失资料的修改/交付步骤暂停；筛选理由、其他候选和本机 50 项测试记录见 [来源与验证](blender/blender-workflow/references/community-sources.md)。

参考图白盒搭建与比例校正按 [白盒搭建流程](blender/blender-workflow/references/whitebox-blockout.md) 执行，静态帧优先检查主相机构成与镜头内可信度，以人物和建筑尺度为基准，允许为画面调整隐藏空间；实景或多视角还原按对应约束处理；[院落案例与二维概括探索](blender/blender-workflow/references/2026-11-09-courtyard-blockout.md) 区分已验证结果与尚未跑通的生图流程。

### 博客经验的持续积累

博客以 [blog-setup](blog_setup/SKILL.md) 为统一入口，媒体和 [flomo 同步](blog_setup/references/flomo-sync.md) 按需读取，原 [flomo 开发案例](blog_setup/references/2026-10-29-flomo-sync-case.md) 保留。后续博客功能优先补充流程和案例，不逐功能创建新 Skill。

flomo_to_moment 目录只保留旧命令/资料链接转接；旧命令现在默认预览，写入需 --apply。若外部已有独立 flomo 技能安装，应检查并改用 blog-setup；本次不修改用户级关联。

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
- 工程卡顿分析先定位具体触发动作和实际求值分支，用对照测试支持结论；默认简报“问题位置、依据、大概原因、优先操作”，硬件和底层机制按追问展开。
- 性能分析读取 [工程性能分析](blender/blender-workflow/references/project-performance.md)；创建或修改几何节点时另按 [节点效果工作流](blender/blender-workflow/references/procedural-node-effects.md) 检查高成本字段与烘焙输出边界。

这些是当前证据支持的需求；后续根据新的任务和明确反馈修订，不把一次性的参数或目录当成永久偏好。

## 技能建设约定

每次真实任务结束都可以复盘，但不要求每次新增 Skill。先判断经验是否会改善后续任务，再选择更新已有技能、补充参考资料、修正脚本、保存案例或待验证记录、新建技能，或无需修改。

- 从具体触发场景和用户目标出发，检查已有技能。同一长期项目的新功能默认归入已有入口的按需流程，开发经历另存案例；独立入口有明确收益时再新建技能。
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
