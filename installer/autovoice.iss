; AutoVoice Inno Setup Script
; Installs AutoVoice and places the Lua script into DaVinci Resolve's Scripts folder.

#define MyAppName "AutoVoice"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "AutoVoice"

[Setup]
AppId={{AUTOVOICE-0001-0001-0001-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\installer_output
OutputBaseFilename=AutoVoice_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Python app (with Windows venv)
Source: "..\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
; Rust backend binary
Source: "..\backend\target\release\autovoice-server.exe"; DestDir: "{app}\backend"; Flags: ignoreversion
; Lua script (for reference)
Source: "..\AutoVoice.lua"; DestDir: "{app}"; Flags: ignoreversion
; Config file with install path
Source: "autovoice.ini"; DestDir: "{app}"; Flags: ignoreversion

[Files]
; Install Lua script into DaVinci Resolve's Fusion Scripts folder (per-user)
Source: "..\AutoVoice.lua"; DestDir: "{localappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"; Flags: ignoreversion

[Code]
const
  ResolutionPath = '{localappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts';

procedure CurStepChanged(CurStep: TSetupStep);
var
  IniFile: String;
  InstallDir: String;
  IniContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    InstallDir := ExpandConstant('{app}');
    IniContent := InstallDir + #13#10;

    IniFile := InstallDir + '\autovoice.ini';
    SaveStringToFile(IniFile, IniContent, False);

    SaveStringToFile(
      ExpandConstant(ResolutionPath) + '\autovoice.ini',
      IniContent,
      False
    );
  end;
end;

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\launch.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\launch.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\launch.bat"; Description: "Launch AutoVoice now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backend\audio_output"
