# 不覆盖基础姿势的呼吸 NLA

用户要求可重新摆姿势、呼吸独立开关/NLA、头肩随胸口起伏时读取。连接与角色保留仍遵循总入口；已有摆姿势与旧 COMBINE 层的关系见 [手势与动作叠加案例](../../blender-character-posing/references/2026-11-08-hands-and-limb-refinement.md)。这份参数驱动方案不是旧绝对骨骼 Action 的换名。

## 目标和可执行入口

复用 [breathing_body_nla.py](../scripts/breathing_body_nla.py)（v2.0.0，保留原 GPL-3.0-or-later 声明）。可将源码放入 Blender Text，手动运行时注册 UI 并弹出骨骼匹配窗口，确认才绑定；也可作为模块导入，用 `main(show_dialog=False)` 注册，`guess_bones(rig)` / `guess_motion_bones(rig)` 得候选，再经用户本轮授权调用 `create_or_update`。`remove_layer(rig)` 仅移除工具拥有的数据。

不因脚本会匹配 Mixamo 就自动给全部角色添加，不因当前选中对象改变就悄悄切换既定目标。不修改 Rest Pose、蒙皮或其他对象。参数/骨名匹配是起点，应用前检查层级、已有约束与骨骼轴。

## 让基础姿势继续可编辑

1. 原骨骼位置、旋转、基础缩放不插帧；已有 Action、slot 和其他 NLA 不替换。
2. 角色对象自身创建 NLA `呼吸 · 缩放与体态叠加`，只动画专用自定义参数 `_visn_breath_wave`，默认基值 0，ADD 混合。不要把某次可见绝对姿势存进呼吸循环。
3. 隐藏辅助空物体保存倍率/位移设置；只由控制器参数驱动，避免 helper 读取 rig 波形、rig 再约束 helper 的外部依赖回环。波形在 rig 上直接驱动呼吸约束。
4. 胸廓体积：Copy Scale，LOCAL/LOCAL、Offset=True、Additive=False；helper 静态倍率与约束 Power 共同叠加到现有局部缩放。头肩起伏不靠强行拉长整条骨链实现。
5. 起伏：对胸部、头、左右肩使用 WORLD/WORLD Copy Location，Offset=True，仅 Z；世界毫米换算需使用 scene unit scale。头/肩的附加量是在胸部继承量之外的量，避免重复理解为总幅度。

标准 Mixamo 优先匹配 Spine2/Spine、Head/Neck、LeftShoulder/RightShoulder，兼容常见命名前缀。现场 Rigify 使用 `tweak_spine.004/.003` 作局部形变，另以 `chest`、`head`、`shoulder.L/R` 作起伏；不要假设局部 tweak 是头肩祖先。某些 Rigify 继承链会隔开局部形变，所以“胸腔缩放”不自动等于“头肩已起伏”。

用 UUID 标记 rig、controller/helper 和工具拥有的数据；重复执行复用，清理仅针对该 owner 的约束、驱动、轨道与 helper。共享集合不在空集合前删除；不得按中文前缀清空用户所有动画。

## 实际踩坑及处理

- **旧绝对变换层覆盖重新摆好的静态姿势**：只调混合模式不足以证明已修复。验证“关闭呼吸→手动改变 pose basis→开启呼吸”全过程，确认 basis 不回退；已有关键帧的基础动作仍需用户正常插帧。
- **静音后残留上一帧参数**：单靠自定义属性的默认值不保证静音时清零。当前约束 influence 另读取 track.mute、strip.mute、animation_data.use_nla，明确禁用。不要把控制器上的 stale wave 当成骨骼仍应继续起伏的依据。
- **Influence 滑块被自动关键帧覆盖**：启用 strip.use_animated_influence 会自动建立 influence FCurve/关键帧。需允许手动常量时，删除自动 key；strip.fcurves 不支持 `.remove()`，用 strip.keyframe_delete。用户以后主动打的影响关键帧应尊重。
- **UI 注册与驱动语法**：Operator 不能用 Object ID PointerProperty，使用可搜索 rig_name 字符串；属性回调直接查 bpy.data.objects，不依赖 operator 的 Python @property；自定义属性驱动路径使用 `["prop"]`。Action 使用 slots/channelbag API，NLA strip 指定 action_slot。
- **重新打开工程**：NLA、约束和原生表达式驱动继续求值，不依赖 Python 帧回调；侧栏是会话注册的，需重新运行 Text。不要声称保存了数据就等于 UI 自动注册。
- **刷新波形不是无损编辑**：脚本重建本工具波形，保留原有外部动画及静态 influence/mute；用户编辑过本波形或 influence 动画时，先保留副本，不声称该条带的所有自定义曲线都被保留。
- **预览接口异常**：一次 look 返回 Not connected 后，后续现场读取曾未找到刚创建的工具层；原因未确认，不能归咎于 look 必然重载或删数据。正确接续是重新读文件/对象/Text/NLA，核实后按授权保存，再在副本检查画面，不重启用户现场碰运气。

## 验证证据与边界（2026-11-14）

独立合成骨架测试包含旋转/非均匀缩放的对象、手动非中性 pose、原 Action/原 NLA、无关约束：

- track 静音、影响 0：全骨矩阵误差约 7.2e-7；关闭后重新摆姿势再打开，matrix_basis 保留，重新静音误差 0。
- 世界起伏：胸 8 mm、头总 9.5 mm、双肩总 10 mm；NLA 影响 0.5 时头起伏约 4.75 mm。
- 重复更新、注册 Operator、移除后保留原 Action/NLA 和用户约束均通过；独立保存重开、不注册工具代码仍能计算且静音有效。
- 实际男角色 Rigify 副本：头约 9.489 mm、肩约 9.990/9.997 mm；foot IK 控制器坐标不变；静音/影响 0 误差约 2.2e-7。基础 pose 通道未改。随后按既定目标应用现场并保存，另做上半身预览，未给另一角色批量添加。

历史证据位于当时 Blender 工作目录：`breathing_body_nla_results.json`、`breathing_real_rig_results.json`、`test_breathing_body_nla.py`、`test_breathing_v2_reopen.py`、`test_breathing_live_rig_copy.py`、`breathing_preview.gif`。本次技能整理重读结果并核对脚本，未再次操作现场呼吸或把这些少量测试外推到全部骨架。

默认 4 s、吸气 40%、胸宽 1%/厚 1.8%、腹部比例 .35、胸/头额外/肩额外 8/1.5/2 mm 是本方案起始值，均应可调。未验证所有 NLA Solo/编辑态组合、任意已约束控制器、连接骨的位移、所有导出引擎；不能声称万能叠加或直接导出即用，导出骨骼动画需按实际目标烘焙。

## 相邻的局部清理案例

用户只要求清空裙子骨骼约束时，按已确认的 `SKIRT-` 骨名集操作：该现场 62 根骨骼共移除 120 个约束及其 120 条精确路径驱动；其余 363 个骨骼约束数量不变。用户明确“不用保姿态”，因此没有补偿姿势，也未删除骨骼、权重、物理辅助对象或全骨架驱动。移除约束不等于插件的所有物理属性/处理器已停用。保留仅对本次请求有用的范围，不把“顺便清理全部物理系统”列为默认操作。
