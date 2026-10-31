# 制作与验证要点

以下是已读取的 API revision 2026.09.15 的关键语义。执行前仍需查询运行服务的 entry。

## 工程与资产

- `GetAllAvatarIds()`、`GetAllClothPieceIds()` 检查当前工程；原生 API 操作当前项目。
- `OpenAvatar(path)` 加载 `.savt`；`OpenGarment(path)` 加载 `.sgar`；`SaveProject(path)` 保存 `.sproj`，三者返回 bool。
- `GetLocalAssetFiles('avatar'/'garment'/'fabric')` 返回安装路径；发现空列表不是本机一定没有资产的证明。
- `GetAllAssetIds(spy.AssetType.Fabric)` 获得面料 ID。用 `GetFabricMaterial(fabricId, spy.SideType.Front/Back/Side)` 读取材质 ID，过滤零并去重，再传给 `ChangeMaterialProperty`。
- `spy.MaterialProperty()` 支持可选字段。示例纯色：`color=spy.CommonColor(91,159,185)`、`metalness=0.0`、`smoothness=0.15`。这些是外观参数，不是面料物理参数。物理属性采用真实预设或已安装面料，不编造刚度。

## 原生纸样（文档路径，尚未由本案例从零验证）

`CreatePatternPath` 的点为二维 WORLD 毫米；`GetPatternEdges` 返回 PATTERN-LOCAL 毫米，两者不可混用。`PatternPoint` 的 incoming/outgoing 是相对曲线手柄。闭合轮廓不重复首点。

保存创建结果中的 clothPieceId 及 edges 映射；创建命令可能改变方向。`CreateSewing` 使用有顺序的 `SewingSegment` 列表，应按真实边向构造。毫米是几何和新测量 API 的单位，旧 `SetAvatarSizes` 使用厘米，不能混用。

`ValidatePatternPiece` 空列表仅表示未检测到二维纸样自交；`GetSewingLengths` 的长度差可能包含设计吃势，不能一律判错。两者都不证明服装穿着正确。

## 模拟排查

限时调用示例：`SimulationToConverge(0.5,1.0,20.0)`。准确打印 `Coveraged`（接口原拼写）、`TimeOut`、`Error` 等返回值。

当返回超时且衣片仍分离时：

1. 检查 `GetSimulationDiagnostics()` 的 running/status/mode，以及 `GetClothPieceProperty` 中 Freeze、Deactivate、Solidify、ParticleDistance。
2. 如果结构/摆放/状态无明显异常，可以单独调用 `StartSimulation()`，返回宿主后让应用运行一段短时间，再独立调用 `StopSimulation()`。
3. 本案例开始后的下一次截图已成功缝合；这个结果不证明首次调用超时的根因，也不证明数值收敛。

初次模拟和一次有依据的补救仍失败时，停止盲目重试，保存检查点，检查截图与状态；依据具体缺陷调整摆放、纸样或面料。无法继续则报告具体阻碍。不要无限重试或重复导入。

## 截图示例

阅读 `GetProjectSnapshot3DImageConfig` / `ExportSnapshotImage3D` entry 后使用：

```python
cfg = spy.GetProjectSnapshot3DImageConfig()
cfg.viewSourceType = spy.SettingSourceType.Enum
cfg.customViewTypes = {spy.CameraOrientationType.Front,
                       spy.CameraOrientationType.Back,
                       spy.CameraOrientationType.Left}
cfg.renderType = spy.Snapshot3DRenderType.Normal
cfg.imageConfig.imageSizeUnit = spy.SnapshotImageConfig.ImageUnit.Pixel
cfg.imageConfig.width = 1000
cfg.imageConfig.height = 1400
cfg.namingConfig.filePath = output_directory
cfg.namingConfig.namingUseCustomText = True
cfg.namingConfig.namingCustomText = 'TShirt'
cfg.namingConfig.namingUseViewNum = False
cfg.optionsConfig.fileType = spy.SnapshotOptionsConfig.FileType.Png
cfg.optionsConfig.doMerge = False
print(spy.ExportSnapshotImage3D(cfg))
```

`filePath` 是目录。检查实际输出文件名，再逐张查看；不要假定中英文视图后缀。二维图用 `GetProjectSnapshot2DConfig` + `ExportSnapshotImage2D`；服务可能自动添加配色、尺码后缀。

正、背、侧面检查完成后再保存最终工程。本案例使用粗粒度 20 mm 模拟用于基础示范，未做精细网格、数值碰撞检查或生产级验证。
