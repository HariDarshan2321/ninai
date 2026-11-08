param(
    [ValidateSet("Auto", "ClaudeCode", "Codex", "Gemini", "None")]
    [string]$Client = "Auto",
    [string]$InstallDir = "$env:LOCALAPPDATA\Ninai"
)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "This installer runs on Windows only."
}
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw "LOCALAPPDATA is unavailable. Ninai cannot choose a safe installation folder."
}
$allowedRoot = [IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\') + '\'
$resolvedInstall = [IO.Path]::GetFullPath($InstallDir)
if (-not $resolvedInstall.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "InstallDir must be inside LOCALAPPDATA."
}

function Find-Python {
    foreach ($command in @("py", "python")) {
        if (Get-Command $command -ErrorAction SilentlyContinue) {
            try {
                if ($command -eq "py") { & py -3.11 -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { return @("py", "-3.11") } }
                else { & python -c "import sys; raise SystemExit(sys.version_info < (3,11))" 2>$null; if ($LASTEXITCODE -eq 0) { return @("python") } }
            } catch { }
        }
    }
    throw "Ninai requires Python 3.11 or newer. Install Python from python.org, select 'Add Python to PATH', then run this installer again."
}

function Invoke-Python([string[]]$Python, [string[]]$Arguments) {
    $prefix = if ($Python.Length -gt 1) { $Python[1..($Python.Length - 1)] } else { @() }
    & $Python[0] @prefix @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python setup failed with exit code $LASTEXITCODE." }
}

function Connect-ClaudeCode([string]$McpCommand, [string]$NinaiCommand) {
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { return $false }
    & $NinaiCommand permission grant claude-code project | Out-Null
    & claude mcp remove ninai-local --scope user 2>$null | Out-Null
    & claude mcp add --transport stdio --scope user ninai-local -- $McpCommand
    return ($LASTEXITCODE -eq 0)
}

function Connect-Codex([string]$McpCommand, [string]$NinaiCommand) {
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { return $false }
    & $NinaiCommand permission grant codex project | Out-Null
    & codex mcp remove ninai-local 2>$null | Out-Null
    & codex mcp add ninai-local --env NINAI_CLIENT_ID=codex -- $McpCommand
    return ($LASTEXITCODE -eq 0)
}

function Connect-Gemini([string]$McpCommand, [string]$NinaiCommand) {
    if (-not (Get-Command gemini -ErrorAction SilentlyContinue)) { return $false }
    & $NinaiCommand permission grant gemini project | Out-Null
    $settings = Join-Path $env:USERPROFILE ".gemini\settings.json"
    New-Item -ItemType Directory -Force -Path (Split-Path $settings) | Out-Null
    $data = if (Test-Path $settings) { Get-Content $settings -Raw | ConvertFrom-Json } else { [pscustomobject]@{} }
    if (-not $data.mcpServers) { $data | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{}) }
    $entry = [pscustomobject]@{ command = $McpCommand; env = [pscustomobject]@{ NINAI_CLIENT_ID = "gemini" }; trust = $false; description = "Private Ninai memory" }
    $existing = $data.mcpServers.PSObject.Properties["ninai-local"]
    if ($existing) { $data.mcpServers."ninai-local" = $entry }
    else { $data.mcpServers | Add-Member -NotePropertyName "ninai-local" -NotePropertyValue $entry }
    $temporary = "$settings.ninai-install.tmp"
    $data | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $temporary
    Move-Item -Force $temporary $settings
    return $true
}

$python = Find-Python
$venv = Join-Path $resolvedInstall "venv"
$backup = "$resolvedInstall.previous"
if (Test-Path $backup) { Remove-Item -Recurse -Force $backup }
if (Test-Path $resolvedInstall) { Move-Item $resolvedInstall $backup }

try {
    New-Item -ItemType Directory -Force -Path $resolvedInstall | Out-Null
    Invoke-Python $python @("-m", "venv", $venv)
    $venvPython = Join-Path $venv "Scripts\python.exe"
    $source = "ninai-memory[windows-build] @ https://github.com/HariDarshan2321/ninai/archive/refs/heads/main.zip#subdirectory=engine"
    & $venvPython -m pip --disable-pip-version-check install --upgrade pip | Out-Null
    & $venvPython -m pip --disable-pip-version-check install $source
    if ($LASTEXITCODE -ne 0) { throw "Ninai package installation failed." }

    $ninai = Join-Path $venv "Scripts\ninai.exe"
    $mcp = Join-Path $venv "Scripts\ninai-mcp.exe"
    $app = Join-Path $venv "Scripts\ninai-app.exe"
    & $ninai doctor | Out-Null

    $connected = @()
    if ($Client -in @("Auto", "ClaudeCode")) { if (Connect-ClaudeCode $mcp $ninai) { $connected += "Claude Code" } }
    if ($Client -in @("Auto", "Codex")) { if (Connect-Codex $mcp $ninai) { $connected += "Codex" } }
    if ($Client -in @("Auto", "Gemini")) { if (Connect-Gemini $mcp $ninai) { $connected += "Gemini CLI" } }

    $shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ninai.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $app
    $shortcut.WorkingDirectory = $resolvedInstall
    $shortcut.Save()

    if (Test-Path $backup) { Remove-Item -Recurse -Force $backup }
    Start-Process $app
    Write-Host "Ninai is installed. Connected assistants: $($connected -join ', ')."
} catch {
    if (Test-Path $resolvedInstall) { Remove-Item -Recurse -Force $resolvedInstall }
    if (Test-Path $backup) { Move-Item $backup $resolvedInstall }
    throw
}
