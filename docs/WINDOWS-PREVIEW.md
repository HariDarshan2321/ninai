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
