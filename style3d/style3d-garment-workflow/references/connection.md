# 本地连接

2026-10-30 验证的服务：`style3d-studio-mcp-server` 1.0.0，Python API revision `2026.09.15`。应用需已运行、登录并加载资产库。

## 调用入口

在 PowerShell 中将 `$rpc` 指向本技能的 `scripts/style3d_rpc.ps1`。先从用户或当前应用确认本地 MCP 地址，每次显式传入 `-Endpoint`。2026-10-30 案例使用 57281，不能视为其他机器的默认值。

```powershell
& $rpc -Endpoint $endpoint -Method initialize
& $rpc -Endpoint $endpoint -Method tools/list
& $rpc -Endpoint $endpoint -Method resources/read -Uri 'style3d://python/api/categories'
& $rpc -Endpoint $endpoint -Method resources/read -Uri 'style3d://python/api/entry/spy.GetGarmentWorkflow'
& $rpc -Endpoint $endpoint -Method resources/read -Uri 'style3d://python/api/entry/spy.GetCapabilities'
```

类别地址：`style3d://python/api/category/{category}`。已知完整函数名时直接读 `style3d://python/api/entry/spy.FunctionName`。常用类别是 `garment_authoring`、`avatar_arrangement`、`fabric`、`snapshot`、`mesh_diagnostics`。

将应用脚本保存为 UTF-8 `.py`，然后调用：

```powershell
& $rpc -Endpoint $endpoint -Method tools/call -ScriptPath 'C:/absolute/task/work/inspect.py'
```

服务暴露的工具是 `run_python_script`，参数 `script_content` 为完整 Python 源码。它在 Style3D 进程中执行 `import spy`，不是外部 Python 解释器。用 `print` 返回执行结果；脚本应短且分阶段，避免失败后仍操作无效 ID。

## 实际传输边界

本次服务器接受 JSON-RPC HTTP POST，要求 `Content-Type: application/json` 和 `Accept: application/json, text/event-stream`，响应为 JSON；未要求会话标识。发送初始化版本 `2024-11-05` 后，服务器返回 `2025-11-25`。这是此实现的实际行为，不代表所有 MCP 服务都使用无状态 JSON。

随附脚本只支持此已验证传输形式，不实现 SSE/持久 session。如果服务返回 session header 或 event-stream，脚本明确停止，此时应使用支持协商的正式 MCP 客户端；不要反复重发可能已经执行的修改。HTTP 超时也不代表应用脚本已取消，重新执行修改前先检查应用状态。

连接被拒绝时先确认用户给出的地址和应用运行状态，不扫描无关端口、不自动修改 Codex 全局配置。技能安装与永久注册 MCP 是不同任务。

