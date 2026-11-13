param(
    [string]$EngineDir = "$PSScriptRoot\..\engine",
    [string]$BuildDir = "$PSScriptRoot\..\build\windows",
    [string]$DistDir = "$PSScriptRoot\..\dist\windows",
    [string]$CertificateThumbprint = "",
    [string]$TimestampUrl = ""
)
$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT") { throw "Build on Windows." }
function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed ($LASTEXITCODE)." }
}
$repo = (Resolve-Path "$PSScriptRoot\..").Path
New-Item -ItemType Directory -Force $BuildDir, $DistDir | Out-Null
$BuildDir = (Resolve-Path $BuildDir).Path
$DistDir = (Resolve-Path $DistDir).Path
$python = Join-Path $BuildDir "venv\Scripts\python.exe"
if (!(Test-Path $python)) { Invoke-Checked "python" @("-m", "venv", "$BuildDir\venv") }
Invoke-Checked $python @("-m", "pip", "install", "${EngineDir}[windows-build]")
$version = (& $python -c "from importlib.metadata import version; print(version('ninai-memory'))").Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid package version." }
$bundle = Join-Path $DistDir "bundle"
if (Test-Path $bundle) { Remove-Item -Recurse -Force $bundle }
New-Item -ItemType Directory -Force $bundle | Out-Null
foreach ($entry in @(@("Ninai", "desktop", "--windowed"), @("ninai-cli", "cli", "--console"), @("ninai-mcp", "mcp", "--console"))) {
    Invoke-Checked $python @("-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", $entry[2], "--name", $entry[0], "--collect-all", "webview", "--collect-data", "ninai", "--distpath", "$BuildDir\frozen", "--workpath", "$BuildDir\work", "--specpath", $BuildDir, "$repo\packaging\windows\$($entry[1])-entry.py")
    # Separate support directories prevent one executable overwriting another's DLLs.
    Copy-Item "$BuildDir\frozen\$($entry[0])" "$bundle\$($entry[0])" -Recurse -Force
}
# Stable top-level launchers are not needed: shortcuts target the desktop subfolder.
$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (!$iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (!(Test-Path $iscc)) { throw "Install Inno Setup 6 from jrsoftware.org first." }
$isccArguments = @("/DAppVersion=$version", "/DBundleDir=$bundle", "/DOutputDir=$DistDir")
if ($CertificateThumbprint) {
    if ($CertificateThumbprint -notmatch '^[A-Fa-f0-9]{40}$') { throw "Expected SHA-1 certificate thumbprint." }
    if ($TimestampUrl -notmatch '^https://[A-Za-z0-9./_-]+$') { throw "An HTTPS timestamp service is required." }
    $signTool = (Get-Command signtool.exe -ErrorAction Stop).Source
    foreach ($file in @(Get-ChildItem $bundle -Recurse -File | Where-Object { $_.Extension -in @('.exe', '.dll', '.pyd') })) {
        Invoke-Checked $signTool @("sign", "/sha1", $CertificateThumbprint, "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256", $file.FullName)
        Invoke-Checked $signTool @("verify", "/pa", "/all", $file.FullName)
    }
    $isccArguments += "/DReleaseSigning"
    $isccArguments += "/Srelease=`"$signTool`" sign /sha1 $CertificateThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 `$f"
}
Invoke-Checked $iscc ($isccArguments + @("$repo\packaging\windows\ninai.iss"))
$name = if ($CertificateThumbprint) { "Ninai-Windows-$version.exe" } else { "Ninai-Windows-$version-unsigned.exe" }
$installer = Join-Path $DistDir $name
if ($CertificateThumbprint) { Invoke-Checked $signTool @("verify", "/pa", "/all", $installer) }
$hash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLower()
"$hash  $name" | Set-Content -Encoding ascii "$installer.sha256"
Write-Host "Built $installer. Native install/upgrade/UI acceptance is required before release."
