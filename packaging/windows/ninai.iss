#ifndef AppVersion
  #error AppVersion required
#endif
#ifndef BundleDir
  #error BundleDir required
#endif
#ifndef OutputDir
  #error OutputDir required
#endif
[Setup]
AppId={{93DCE595-806B-46BF-B948-BA66265F31CE}
AppName=Ninai
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Ninai
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultGroupName=Ninai
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=Ninai-Windows-{#AppVersion}-unsigned
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\Ninai\Ninai.exe
#ifdef ReleaseSigning
SignTool=release $f
SignedUninstaller=yes
OutputBaseFilename=Ninai-Windows-{#AppVersion}
#endif
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Ninai"; Filename: "{app}\Ninai\Ninai.exe"
Name: "{autodesktop}\Ninai"; Filename: "{app}\Ninai\Ninai.exe"
; The vault and assistant configuration are outside {app}; never delete them.
; Do not auto-launch or silently reconnect assistants during installation.
