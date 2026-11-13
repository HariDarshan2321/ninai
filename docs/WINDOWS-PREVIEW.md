# Ninai for Windows preview

The local engine and desktop interface are portable, but Windows packaging is
still a preview. Do not advertise general Windows availability until the build
has passed the acceptance checks below on clean Windows 11 machines.

## Preview install

Run PowerShell as the current user, not as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

The preview installer confines its files to `%LOCALAPPDATA%\Ninai`, creates a
desktop shortcut, detects installed Claude Code, Codex, and Gemini CLI clients,
and connects the clients it finds. It does not configure lifecycle session
hooks on Windows yet.

## Release gate

- Replace the Python bootstrap with a signed installer that bundles its runtime.
- Code-sign the executable and installer.
- Test standard-user installation without Python, Git, or developer tools.
- Verify install, upgrade, rollback, uninstall, and retained-vault behavior.
- Verify Claude Code, Codex, and Gemini CLI independently.
- Verify immediate permission revocation and disclosure logging.
- Test Windows 11 at 100%, 125%, and 150% display scaling.
- Pass Microsoft Defender and independent malware scans.
- Record a clean-machine installation video.

## Bundled installer build and native regression

A separate packaged-preview route now exists; the bootstrap above is unchanged.
On a Windows x64 build machine with Python 3.11+, Inno Setup 6, and build network
access, run:

```powershell
./scripts/build-windows-app.ps1
```

The output is `dist/windows/Ninai-Windows-<version>-unsigned.exe` plus SHA-256.
PyInstaller bundles Python, the desktop UI, CLI and MCP server; customers do not
need Python or Git for this package. The system WebView2 runtime is still a
prerequisite and its clean-machine availability/offline setup must be accepted.
The per-user Inno installer uses a stable AppId and `%LOCALAPPDATA%\Programs\Ninai`.
It leaves the vault and assistant configuration outside its install tree, never
auto-connects assistants, and never auto-launches the app. Installed commands are
`ninai-cli\ninai-cli.exe` and `ninai-mcp\ninai-mcp.exe` under the install folder.
Assistant connection is a separate explicit step. The installer does not snapshot
the vault or provide a transactional database rollback.

The manual/PR `Desktop installer regression` workflow builds immutable prior
0.1.0 source and current source on `windows-2022`, installs both on the native
runner using synthetic data, tests repeated upgrade, retained provenance/grants,
revocation, uninstall and retained-vault reinstall. Run locally on a **disposable
CI runner only**:

```powershell
./scripts/test-windows-installer.ps1 -PreviousInstaller <old-unsigned.exe> -CurrentInstaller <new-unsigned.exe>
```

This workflow must actually pass before claiming native Windows regression
coverage. It has not been executed merely because the YAML exists. It does not
prove Windows 11 visual acceptance, Defender/SmartScreen reputation, interrupted
installation recovery, or publisher trust. It never publishes a release.

For an owner with a code-signing identity already provisioned in the Windows
certificate store (including its required hardware/provider), and the Windows SDK
SignTool on PATH:

```powershell
./scripts/build-windows-app.ps1 -CertificateThumbprint <40-hex-thumbprint> -TimestampUrl https://YOUR-CA-TIMESTAMP-SERVICE
```

The script SHA-256 signs and timestamps bundled executable code, the installer,
and its uninstaller, then verifies Authenticode using `signtool verify /pa /all`.
It writes a release filename only when signing succeeds. No PFX/password/key is
accepted or stored by the script. A signing certificate alone does not establish
SmartScreen reputation or replace clean-machine acceptance. Current unsigned
artifacts must not be advertised as signed customer installers.

References: [Microsoft SignTool](https://learn.microsoft.com/windows/win32/seccrypto/signtool),
[Inno per-user privilege mode](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).

## Owner verification boundary

The new in-app governance approval path currently uses macOS owner verification.
Windows verification is not implemented; approvals fail closed on unsupported
platforms. Native Windows install/upgrade regressions exercise data preservation,
not Windows Hello or a completed first-run approval. Windows remains a preview
until its verification, clean-machine UI and trusted distribution gates pass.
