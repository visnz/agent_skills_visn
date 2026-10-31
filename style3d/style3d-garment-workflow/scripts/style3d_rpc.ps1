param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('initialize','tools/list','resources/read','tools/call')]
    [string]$Method,
    [Parameter(Mandatory=$true)]
    [string]$Endpoint,
    [string]$Uri,
    [string]$ScriptPath,
    [ValidateRange(1,600)][int]$TimeoutSec = 120
)
$ErrorActionPreference = 'Stop'
$target = [System.Uri]$Endpoint
if (-not $target.IsLoopback -or $target.Scheme -notin @('http','https')) {
    throw 'This helper supports local loopback HTTP(S) endpoints only.'
}
$rpcParams = @{}
switch ($Method) {
    'initialize' {
        $rpcParams = @{ protocolVersion='2024-11-05'; capabilities=@{}; clientInfo=@{name='Codex-Style3D-Skill';version='1.0'} }
    }
    'resources/read' {
        if (-not $Uri) { throw 'resources/read requires -Uri.' }
        $rpcParams = @{uri=$Uri}
    }
    'tools/call' {
        if (-not $ScriptPath) { throw 'tools/call requires a UTF-8 -ScriptPath.' }
        $scriptText = Get-Content -LiteralPath $ScriptPath -Raw -Encoding utf8
        $rpcParams = @{name='run_python_script';arguments=@{script_content=$scriptText}}
    }
}
$body = @{jsonrpc='2.0';id=1;method=$Method;params=$rpcParams} | ConvertTo-Json -Depth 30 -Compress
$response = Invoke-WebRequest -Uri $Endpoint -Method Post -ContentType 'application/json; charset=utf-8' -Headers @{Accept='application/json, text/event-stream'} -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing -TimeoutSec $TimeoutSec
if ($response.Headers['Mcp-Session-Id'] -or "$($response.Headers['Content-Type'])" -match 'text/event-stream') {
    throw 'Server requires session/SSE support. Use a full MCP client; do not blindly repeat a mutation.'
}
$rpcResponse = $response.Content | ConvertFrom-Json
if ($rpcResponse.error) { throw ($rpcResponse.error | ConvertTo-Json -Depth 20 -Compress) }
if ($null -eq $rpcResponse.result) { throw 'Missing JSON-RPC result.' }
if ($rpcResponse.result.isError) { throw ($rpcResponse.result | ConvertTo-Json -Depth 20 -Compress) }
if ($rpcResponse.result.contents) {
    $rpcResponse.result.contents | ForEach-Object { $_.text }
} elseif ($rpcResponse.result.content) {
    $rpcResponse.result.content | ForEach-Object {
        if ($_.type -eq 'text') { $_.text }
        else { $_ | ConvertTo-Json -Depth 30 -Compress }
    }
} else {
    $rpcResponse.result | ConvertTo-Json -Depth 30
}

