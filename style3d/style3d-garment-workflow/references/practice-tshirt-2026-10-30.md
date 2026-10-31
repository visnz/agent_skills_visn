# 实践：女模 + 浅蓝圆领 T 恤

日期：2026-10-30（Asia/Shanghai）。用户要求连接本地 Style3D，添加模特并简单制作 T 恤。

## 前提与资产发现

通过 `http://127.0.0.1:57281/mcp` 初始化，服务名 `style3d-studio-mcp-server`、版本 1.0.0，Python API revision 2026.09.15。开始时 `GetAllAvatarIds()` 和 `GetAllClothPieceIds()` 均为空，可以在当前空工程中操作。

`GetLocalAssetFiles('avatar')` 返回 `[]`，但 `GetLocalAssetFiles('garment')` 返回已安装的男女 T 恤模板。随后只在已知 `C:/Users/Public/Documents/Style3D` 目录按 `*.savt` 查找，发现 `Asset_2.5/Avatar_V4` 下的真实模特文件。空列表的原因未查明。

实际使用：

- 模特：`C:/Users/Public/Documents/Style3D/Asset_2.5/Avatar_V4/Female/Female.savt`
- 服装：`C:/Users/Public/Documents/Style3D/Asset_2.5/Garment/Female_T-Shirt.sgar`

以上路径仅为本机案例，不作为其他机器的固定安装路径。

## 执行与观察

1. `OpenAvatar` 和 `OpenGarment` 都返回 True；另存 `.sproj` 返回 True。模型包含 7 个纸样实体及 16 个缝合关系（含模板对称关系），无需重新建立缝合。
2. 导入时出现纹理宽高为零的 warning；其未阻止导入及截图。未判断根因，不将警告泛化为可永远忽略。
3. 所有纸样 `ValidatePatternPiece` 均返回空列表。缝合长度包含差异，其中一对约 474.70 / 567.77 mm；未据此自动修改模板。实际多视图用于判断穿着。
4. 初始截图衣身、袖子、领条在人体周围分离，尚未缝合成衣。
5. 将工程面料关联的材质去重后设为 RGB(91,159,185)，metalness=0，smoothness=0.15。没有替换模板物理面料，不能宣称使用了棉针织物理预设。
6. `SimulationToConverge(0.5,1.0,20.0)` 返回 `SimulationResult.TimeOut`。后续截图仍是分离衣片，不报告成功。
7. 检查纸样 Freeze/Deactivate/Solidify 均为 False、ParticleDistance 为 20 mm。模拟诊断显示停止。
8. 单独调用 `StartSimulation()` 返回 True，诊断显示 running=True、mode=1（XGpu）。在应用外等待约 12 秒，再另一次调用 `StopSimulation()`。截图中衣身、袖子和领口已合拢并形成正常短袖 T 恤。首次失败根因未证实，不声称一定由线程阻塞或 GPU 模式造成。
9. 查看正、背、左侧图片，未见明显分离、扭曲或穿插；再次保存 `.sproj`。交互式模拟成功产生穿着效果，但没有取得数值收敛证明或生产验证。

## 实际产物

原始任务输出目录：`C:/Users/yue.zhao04/Documents/Codex/2026-10-30/ch/outputs/`

- `Basic_TShirt.sproj`：约 31.6 MB，可编辑的模特、纸样、缝合及材质工程。
- `TShirt_Front.png`、`TShirt_Back.png`、`TShirt_Left.png`：1000 × 1400 三视图。
- `TShirt_Patterns_齐色 0_M.png`：二维纸样图；实际导出文件名含配色、尺码后缀。

本次成果是基于内置模板的制作与试穿，不是从零绘制纸样。技能不内嵌商业资产及上述工程；路径用作追溯记录，未来任务使用自身输出位置。
