param([Parameter(Mandatory)][string]$PreviousInstaller, [Parameter(Mandatory)][string]$CurrentInstaller)
$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT" -or $env:CI -ne "true") { throw "Disposable Windows CI runner only." }
$fixture = Join-Path $env:RUNNER_TEMP ("ninai-upgrade-" + [Guid]::NewGuid())
New-Item -ItemType Directory $fixture | Out-Null
$install = Join-Path $fixture "Application with spaces"
$env:NINAI_DATA_DIR = Join-Path $fixture "Private vault"
$cli = Join-Path $install "ninai-cli\ninai-cli.exe"
function Invoke-Cli([string[]]$Arguments) {
    $output = & $cli @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Bundled CLI failed: $Arguments" }
    return ($output | Out-String)
}
function Install([string]$Installer) {
    $process = Start-Process -FilePath (Resolve-Path $Installer) -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "`"/DIR=$install`"") -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Installer failed: $($process.ExitCode)" }
}
Install $PreviousInstaller
Invoke-Cli @('remember', 'Installer upgrade retains this synthetic memory', '--source', 'fixture://windows/prior') | Out-Null
Invoke-Cli @('permission', 'grant', 'codex', 'project') | Out-Null
Invoke-Cli @('capture', 'disable') | Out-Null
$project = (Invoke-Cli @('project', 'create', 'Synthetic prior project', '--path', $fixture) | ConvertFrom-Json).id
Invoke-Cli @('project', 'grant', 'codex', $project) | Out-Null
Invoke-Cli @('remember', 'Project upgrade fixture', '--source', 'fixture://windows/project', '--project', $project) | Out-Null
Invoke-Cli @('recall', 'Installer upgrade', '--client', 'codex') | Out-Null
$beforeLogs = Invoke-Cli @('logs')
$before = Invoke-Cli @('memories')
if ($before -notmatch 'fixture://windows/prior') { throw 'Prior install did not persist fixture.' }
Install $CurrentInstaller
Install $CurrentInstaller # Repeat must preserve data and installation identity.
$after = Invoke-Cli @('memories')
if ($after -notmatch 'fixture://windows/prior' -or $after -notmatch 'Installer upgrade retains') { throw 'Upgrade lost memory/provenance.' }
if ((Invoke-Cli @('capture', 'status') | ConvertFrom-Json).session_capture -ne $false) { throw 'Capture preference changed.' }
if ((Invoke-Cli @('logs')) -ne $beforeLogs) { throw 'Prior disclosure history changed.' }
if ((Invoke-Cli @('recall', 'Project upgrade', '--client', 'codex', '--project', $project)) -notmatch 'fixture://windows/project') { throw 'Named project grant/data lost.' }
$recall = Invoke-Cli @('recall', 'Installer upgrade', '--client', 'codex')
if ($recall -notmatch 'fixture://windows/prior') { throw 'Upgrade lost existing grant.' }
Invoke-Cli @('permission', 'revoke', 'codex', 'project') | Out-Null
$revoked = Invoke-Cli @('recall', 'Installer upgrade', '--client', 'codex')
if ($revoked -match 'fixture://windows/prior') { throw 'Revocation failed after upgrade.' }
$uninstall = Start-Process "$install\unins000.exe" -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw 'Uninstall failed.' }
if (!(Test-Path "$env:NINAI_DATA_DIR\ninai.sqlite3")) { throw 'Uninstall removed vault.' }
Install $CurrentInstaller
if ((Invoke-Cli @('memories')) -notmatch 'fixture://windows/prior') { throw 'Reinstall lost retained vault.' }
Write-Host 'PASS: packaged 0.1.0 -> current install, repeated upgrade, provenance, grants, revoke, uninstall and retained-vault reinstall.'
