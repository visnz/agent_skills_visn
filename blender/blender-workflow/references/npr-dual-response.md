# 项目常规三渲二：双响应材质与法线

## 读取时机与边界

用户说“常规风格化 setup”“三渲二双响应着色器”“按以前那套做类似材质”，或排查高度、法线编码、灯光响应时读取。此文件记录用户选定的创作基线，不是要求所有 NPR 材质采用同一实现。先读取现场，保留用户新参数；不因发现可简化或不符合物理的接法而自动修正。

沟通先给简短结论与实际影响，细节按追问展开；用户明确要求逐参数教学时才展开接口和公式。解释某个节点不等于获准改线、渲染或重做系统。

## 用户指定的基线：2026-11-15 只读检查

Blender 5.3.0 / EEVEE。材质 **`一个常规的三渲二双响应着色器`**，当时挂在 `Platform_Base_Instance_3`；对象名称只作历史定位。用户明确将其作为后续项目常规风格化基础。根树 44 节点、38 链接；连同 4 个引用组共 165 节点、201 链接。本轮检查结构及参数，未修改材质、未保存工程、未做新镜头渲染验收。

完整只读结构见 [节点快照](2026-11-15-dual-response-nodes.json)。包含输入实例值、节点运算、混合模式、色带、图像/对象引用、端口序号和子树；它是可供重建核对的清单，不是可直接执行的完整导入格式，也不携带贴图像素。

后续复用时按以下信号职责理解，不能把“双响应”误认成两盏灯或 5.3 Light Accumulation：当前根树使用传统 Shader to RGB 和自定义半兰伯特。

### 1. 纹理与 Albedo

- `三层噪波`：三档尺度为 `Basic Scale`、`Basic Scale × Index`、`Basic Scale × Index²`，用 Soft Light 叠加；同组另有三层 Voronoi 输出。当前两处实例实际使用 `noise` 输出，不要因组内有 Voronoi 就写成当前材质正使用 Voronoi。
- Texture Coordinate 未提供自定义坐标时，组内退回 Object 坐标；该选择依赖内部比较/混合接线，迁移时检查自定义输入。坐标比例不是世界米制保证。
- 主 noise → `色阶`。其“色阶（视觉）”带 Gamma 2.2 分支，用于 Color Ramp 配色；“色阶（线性）”用于 Bump Height。两路应保留不同语义，不随意互换。
- 基础 RGB 与纹理色带经 Soft Light 合成，再与边缘链 Screen，得到共用 Albedo。当前常量色不是原始 Albedo 图像；根树图像节点承担的是固有法线。

### 2. 边缘属性依赖

Attribute 读取 `SA`，与独立 noise 的明暗变化经 Darken、Brightness/Contrast 处理后 Screen 到 Albedo。

`SA` 不是屏幕描边，也不是 Shader 内计算出的曲率。现场 `UA/SA.001` 几何修改器将 Edge Angle 的 Unsigned Angle / Signed Angle 分别写入 `UA` / `SA`，均为 FLOAT、POINT；包含边域到点域的适配。原始网格属性列表可不含它们，不能仅据原始属性列表判定缺失，应检查修改器与求值几何。当前物体还存在 Bevel、WeightedNormal、OH_OUTLINE，后者不等于本材质的 SA 边缘链。

迁移到别的模型时，核对属性生产链、名称、类型、域与修改器顺序；缺少 SA 时不能把边缘效果已复现当作事实。

### 3. 合并法线

固有 Normal 图（Non-Color）→ Normal Map（Tangent）→ 法线 A；主纹理的线性色阶 → Bump Height → 法线 B。

`法线叠加 · 表面偏移相加` 的实际运算：

```text
Nout = normalize(N0 + a × (normalize(A) − N0)
                    + b × (normalize(B) − N0))
N0 = Geometry Normal
```

这是共同着色空间内的表面偏移相加，既非直接相加 RGB，也非自动 RNM 切线空间合并。两路输入都应是已经解码/计算好的 Normal 向量。强度可以超过 1，但属于艺术控制；迁移需看轮廓受光与高光是否翻转，不能保证任意大幅扰动准确。未连接的零向量不应假称“中性法线”，需要显式提供 N0 或相应回退。

合并结果同时进入传统受光计算、真实 Diffuse 和 Glossy。自定义 `Shading Models.001` 的 Normal 当前未连，组内回退 Geometry Normal；这一区别应按基线保留，不能说所有分支都用了笔触法线。

### 4. 双响应的实际接法

- 真实受光链：共用合并法线 → Diffuse BSDF → Shader to RGB → Greater Than → 明暗 Color Ramp。
- 辅助增强链：Texture Coordinate 的 Object 引用 `Sun` → `Shading Models.001.Light`。该组 normalize 输入并取反，以点积构造 Half Lambert；当前实际消费 Half Lambert，Phong/Blinn Phong 等输出未被根树使用。
- 这一路读取的是相对 Sun 对象的 Object 坐标，不是 5.3 Light Evaluation 的 Direction，也不是完整的实际灯光遮挡。跨坐标空间、Sun 平移/旋转、实例缩放后的视觉尚未另行验证，不应承诺其与物理 Sun 方向完全等价。
- 传统色阶与辅助 Half Lambert 经 Screen 合成，再与 Albedo Soft Light 得到风格化颜色。
- Mix Shader：一路为以 Albedo 着色的真实 Diffuse BSDF，另一路直接接上述颜色，借颜色到 Shader 的隐式转换显示。后者上游仍响应灯光，不应称“完全不响应光照”。需要显式化时可等效表达为 Emission 分支，但未经授权不改原树。

### 5. 最后的独立光泽

Albedo 和合并法线进入 Glossy BSDF。基础双响应结果先 Add Glossy，再与未加 Glossy 的基础结果 Mix。按当前接线可写为：

```text
Base = Mix(Diffuse(Albedo, Nout), 风格化颜色转Shader, w)
Final = Base + (1 − g) × Glossy(Albedo, Nout)
```

最后 Mix 的系数越大，光泽贡献越小；不要把这个端口反向解释成“光泽强度”。

### 当时实例值，不作为跨项目默认

主 noise：Detail 15.49、Basic Scale 1.12、Index 3；色阶数 6、边界模糊 0.001；纹理 Soft Light 0.725；真实明暗 Greater Than 1.1；双响应 Mix 0.5。固有 Normal Map 强度 0.3，Bump 强度 5、Distance 1、Filter Width 0.001；合并 A/B 强度 0.5/10；Glossy Roughness 0.3，最后 Mix 0.833333（按接线约保留 1/6 光泽）。

Greater Than 目前先产生二值，再进色带；不能因色带有三个色标就把这一分支描述成三档连续受光。高 Bump/法线强度及阈值来自用户当前创作，不自动钳回“物理合理”范围。

## 最近实践：不要重复的混淆

### Bump to Normal 只读诊断

此前的 `Bump to Normal` 实际为 `World to Tangent → 向量 × 0.5 + 0.5`，用于把已有世界法线编码为切线 RGB，不含高度导数。此前输入是色阶灰度、后接 Normal Map 的 Object Space，存在高度/方向与编码空间两种不匹配；只读诊断没有自动替用户改线。当前基线已使用 Bump 和世界法线叠加，应以当前结构为准，不能把旧接法当成现存错误。

只要受光法线时直接用 `Height → Bump → BSDF/Light Evaluation Normal`；需要 RGB 法线图再编码，真实图片还需烘焙。重建切线基时须关注 UV、镜像 UV 的切线手性与解码空间；本轮未验证旧自制 World to Tangent 在这些情形的正确性。

### 5.3 四个灯光节点：有依据的知识边界

- Light Evaluation 内置 Lambert / GGX，不是 Half Lambert / Blinn Phong。完整半兰伯特要从原始 N·L 构建，不能从已截负的漫反射 Factor 恢复。
- Mask 是灯锥/范围等限制，Shadow Raycast 是遮挡；不要混为一谈。
- 本地 5.3 点光测试中距离 1→2、Factor 约 1→0.25，Power 不变。不要在内置 Factor 后无条件再乘一次 1/r²。该数值不是所有灯型的通用公式。
- 新灯光数据需要处于 Light Accumulation 输入链中。完整的直接漫反射教学链可以包含 Factor、Mask、Shadow、Power、灯色和底色；这不是完整 Principled/GI 的替代承诺。
- sun_threshold=0 是明确关闭世界太阳提取的方式；此前把它提高至 1e6 只是间接压住提取。关闭提取不等于删除世界全部照明，也不会关闭场景 Sun。

### 旧公交亭 NPR 原型的取舍

2026-11-14 的 `公交亭 · 5.2兼容着色` / `5.3光照着色` 是独立试验，不是当前用户指定双响应基线。旧组“色阶扰动”改变调色输入，“投影偏移”改变阴影采样位置；“光强归一”(π/10)和“直射校准”(2.3)只是场景固定倍率，可合并为受光增益，不是自动归一或通用校正常数。多灯暗部底色重复曾通过“底色只加一次、逐灯加增量”调整；不能据数值误差改善宣布参考风格已还原。

用户认为此前最小原型过于复杂。后续优先保留有可见收益的信号链，讲清主控，辅助补偿可内部合并；不得因此擅自删除当前用户手工保留的层。

## 证据、验证与来源

- 当时工作目录 `C:/Users/<user>/Documents/ChatGPT/Blender/`：`npr_explanation_20261115/user_dual_response_shader_audit.json`（已将精简结构清单收在本参考旁）、`node_probe.json`、`probe_light_nodes_53.py`；`busstop_npr_20261114/npr_bus.py`、`改动与验证.txt`、`look_verification.json`、`probe.log`。这些是历史定位，不要求新机器具备该目录。
- 当前基线是现场只读复盘，用户指定作为常规起点；未声称跨项目验证、各镜头渲染认可或在 Cycles 可用。
- [开发者模型与使用说明](https://forum.blender.org/t/material-lighting-nodes-feedback/45695)、[官方 Light Evaluation](https://docs.blender.org/manual/en/5.3/render/shader_nodes/input/light_evaluation.html)、[World Sun](https://docs.blender.org/manual/en/5.3/render/eevee/world_settings.html)。后续版本应重新核对接口，不能照抄开发阶段旧截图。
- FotoSketcher Shader 面板集成不在本轮验证范围；最新开发状态另读 [插件维护入口](../../addon-development/SKILL.md)。不能依据这份旧需求回顾断言它当前已完成或未完成。
