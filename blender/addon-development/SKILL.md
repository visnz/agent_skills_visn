---
name: blender-addon-maintenance
description: 在已有协作规则（如 CLAUDE.md/AGENTS.md）约束下的 Blender 插件代码库中开发新功能或修 bug：核对模块归属与改动边界、按功能单独开分支、按项目要求留档，并用真实连接的 Blender（MCP）做端到端 operator 验证而不污染用户当前场景。涵盖世界空间包围盒计算陷阱、bpy 图标/枚举校验、context override 等真实踩坑。适用于"给 Blender 插件加新 operator/面板""多人协作的插件仓库""改别人模块前要确认""用 MCP 测试 operator"等任务；不涉及插件打包/发行、addon 模板脚手架（走社区 blender-addon-development 专题）或操作用户当前场景内容本身（走 blender-workflow）。
---

# Blender 插件仓库开发

对象是一个**插件的 Python 代码库**本身（operator、面板、注册流程、分支与协作记录），不是用户当前场景里的模型/材质/动画内容。后者属于 [blender-workflow](../blender-workflow/SKILL.md)。本技能记录的是在 pond_bekkan（蛙灾×桶桶双人维护的 Blender 5.2 插件）仓库中真实验证过的开发流程。

## 什么时候用

- 给一个已有协作规则的 Blender 插件仓库新增 operator、面板按钮或修 bug。
- 仓库里有 CLAUDE.md / AGENTS.md 一类文件，定义了"谁的模块不能随便改""改前要不要确认"。
- 需要在真实运行的 Blender（通过 MCP 或类似连接）里验证新 operator，而不只是语法检查。
- 遇到"按旋转物体算包围盒结果偏大""图标/事件枚举名不确定""多条分支改到同一处产生冲突"这类具体问题。

不适用：纯粹的 addon 打包/发行流程、从零搭建插件模板（这些交给社区 `blender-addon-development` 专题，见 [blender-workflow 的社区分流](../blender-workflow/references/community-routing.md)）；操作用户当前场景内容本身走 `blender-workflow`。

## 核心决策

### 1. 先读协作规则，再决定能不能动手

开工前检查仓库根目录是否有 CLAUDE.md / AGENTS.md 一类文件。这类文件通常把代码按模块划归不同维护者（专属 A / 专属 B / 共同维护），并规定修改边界。

- 只新增独立文件、独立函数/类、不改动任何既有逻辑时，风险较低，可以直接做，但仍按仓库要求说明改了什么、原归属是什么。
- 要改对方专属模块或"共同维护"模块的既有逻辑时，动手前必须向用户说明：改哪个文件/函数、这个模块原来归属谁、改的理由、是否影响另一方的 UI/行为、是否需要同步更新仓库里记录模块归属的文档。获得明确同意后才改，不能因为"看起来是小改动"就跳过这一步。
- 具体协议细节和一次完整执行记录见 [references/repo-collaboration.md](references/repo-collaboration.md)。

### 2. 一个功能一条分支，从正确的基点切出

- 新功能从当前的公共开发分支（而不是别的功能分支）切出独立分支；如果开工前发现当前分支上还有未提交的、与本次需求无关的改动，先用 `git stash` 挪到正确基点上的新分支，不要把不相关的改动堆在一起。
- 多条独立分支各自给同一个文件的"尾部同一区域"（比如 operator 注册的元组、面板 `draw()` 方法、记录归属的表格）追加内容时，合并第二条分支会产生冲突——这是正常现象，不是误操作；解决时要保留两边各自新增的内容，不能选边删掉一方。
- 合并前，若某条分支此前只做过背景脚本测试没做过真实交互测试，先补测再合并；每次合并后用静态检查（如 `python -m compileall`）和重新加载插件确认所有分支的功能能同时正常注册、互不冲突。

### 3. 按项目要求留档

项目如果要求"每次开发必须留档"，按其指定的位置和格式记录：目标、改了哪些文件/函数、调试与试错过程、测试结果、未完成的 TODO。合并多条分支前，把每条分支当时欠缺的测试补上并追加记录，而不是在日志里留一个"未测试"就直接合并。

### 4. 用真实连接的 Blender 做端到端验证，同时保护用户现场

有 MCP（或类似）连接到用户正在使用的真实 Blender 时，优先用它跑一遍真实的 `选中 → 调用 operator → 检查结果`，而不是只改代码后假设正确，也不是只用 `--background` 脚本模拟（后者绕过了真实的选中/UI 上下文，可能掩盖 context 相关的问题）。

同时：

- 操作前先读取当前场景信息，确认是不是用户正在使用的真实工程（可能有几十个物体、绑定好的骨骼等），不要默认是空场景。
- 需要测试数据时建一个命名清晰的临时集合，测完按名字精确删除该集合及其数据块，不用会牵连到其他物体的批量操作。
- `bpy.ops.object.select_all` 等需要 Object Mode 和 3D 视口上下文的 operator，脚本环境下默认 `bpy.context` 可能缺这些，poll 失败不等于代码有 bug，见 [references/mcp-live-testing.md](references/mcp-live-testing.md) 的 context override 写法。
- 发现用户当前处于编辑模式等非 Object Mode 时，不要强制切换用户的模式去跑测试；记录为当前未覆盖的分支，等用户方便时再测或只验证不依赖该切换的部分。
- 连接偶发断开是常见的瞬时抖动，重新检查一次连接状态确认重连即可继续，不要当成功能失败。

### 5. 两个具体的 bpy 技术陷阱

- **图标/枚举名用前查，不凭记忆**：不同版本/图标集合未必包含某个名字；用当前连接的 Blender 实际查询枚举（如 `bpy.types.UILayout.bl_rna.functions['prop'].parameters['icon'].enum_items`，事件类型查 `Event.bl_rna.properties['type'].enum_items`）确认存在再写进代码。
- **世界空间包围盒不能用局部 bbox 整体变换**：物体局部空间包围盒（`obj.bound_box` 的 8 个角点）本身对圆柱等非箱形几何就比真实形状宽松；物体一旦被旋转，把这 8 个角点整体乘 `matrix_world` 再求 min/max，就是"盒子套盒子"，算出的世界空间范围会比真实几何更大。需要贴合物体实际旋转/缩放表现的边界时，要逐个真实几何点（mesh 顶点、曲线端点+贝塞尔手柄）变换到世界空间后再求 min/max。技术细节、验证数据和案例见 [references/world-space-bbox.md](references/world-space-bbox.md)。

## 完成标准

- **协作边界**：改了对方专属或共同维护模块的既有逻辑时，已经在动手前向用户说明五要素并获得同意；仅新增独立内容时已说明改动范围。
- **分支与合并**：功能分支职责单一、从正确基点切出；合并冲突已确认双方新增都被保留，静态检查通过，重新加载后新功能能和已有功能一起正常注册。
- **留档**：按项目要求的位置和格式记录了目标、改动、调试过程、测试结果、TODO；合并前补齐了之前欠缺的验证。
- **测试**：真实连接可用时已做端到端 operator 验证而非只检查语法；用户真实场景没有被测试数据污染，已确认清理；受限于用户当前状态而未覆盖的分支已明确说明，不假装已经测过。
- **技术实现**：图标/枚举来自当前连接的 Blender 验证；涉及世界空间几何边界计算时，已用真实几何点而非局部 bbox 验证过旋转物体的结果是否贴合视觉表现。

## 按需读取

- [references/repo-collaboration.md](references/repo-collaboration.md)：模块归属协议的具体执行方式、分支策略与合并冲突处理、留档格式。
- [references/mcp-live-testing.md](references/mcp-live-testing.md)：真实 Blender 连接测试的现场保护、context override 写法、连接抖动处理。
- [references/world-space-bbox.md](references/world-space-bbox.md)：包围盒陷阱的技术细节与实测数据。
- [references/2026-10-31-pond-bekkan-case.md](references/2026-10-31-pond-bekkan-case.md)：本技能依据的完整真实案例（pond_bekkan 插件一次会话内的 5 条分支开发与合并）。路径、分支名、具体数值仅代表当时现场，执行前须在当前仓库重新确认。
