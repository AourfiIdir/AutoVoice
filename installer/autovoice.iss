; AutoVoice Inno Setup Script
; Installs AutoVoice and places the Lua script into DaVinci Resolve's Scripts folder.

#define MyAppName "AutoVoice"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "AutoVoice"
#define MyAppURL "https://github.com/AUTOVOICE_USER/AutoVoice"

[Setup]
AppId={{AUTOVOICE-0001-0001-0001-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\installer_output
OutputBaseFilename=AutoVoice_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\launch.bat

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Rust backend binary
Source: "..\backend\target\release\autovoice-server.exe"; DestDir: "{app}\backend"; Flags: ignoreversion
; Python frontend (single exe via PyInstaller)
Source: "..\app\dist\AutoVoice.exe"; DestDir: "{app}"; Flags: ignoreversion
; Lua modules (ljsocket, dkjson, server)
Source: "..\Resolve-integration\modules\autovoice_server.lua"; DestDir: "{app}\modules"; Flags: ignoreversion
Source: "..\Resolve-integration\modules\ljsocket.lua"; DestDir: "{app}\modules"; Flags: ignoreversion
Source: "..\Resolve-integration\modules\dkjson.lua"; DestDir: "{app}\modules"; Flags: ignoreversion
; Launcher and launch script (install directory)
Source: "..\AutoVoice.lua"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch.bat"; DestDir: "{app}"; Flags: ignoreversion

; Resolve scripts (per-user, in Fusion\Scripts\Utility so it appears in Script menu)
Source: "..\AutoVoice.lua"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"; Flags: ignoreversion

[Code]
const
  ResolvePath = '{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility';

procedure RewriteLuaPathsInFile(FilePath: String; InstallDir: String);
var
  Lines: TStringList;
  I: Integer;
  Line: String;
  OldDir: String;
  NewDir: String;
  OldMod: String;
  NewMod: String;
begin
  if not FileExists(FilePath) then
    Exit;

  Lines := TStringList.Create;
  try
    Lines.LoadFromFile(FilePath);

    OldDir := 'C:\Users\omen1\Desktop\autoVoice';
    NewDir := InstallDir;
    OldMod := 'C:\Users\omen1\Desktop\autoVoice\Resolve-integration\modules';
    NewMod := InstallDir + '\modules';

    for I := 0 to Lines.Count - 1 do
    begin
      Line := Lines[I];
      StringChange(Line, OldDir, NewDir);
      StringChange(Line, OldMod, NewMod);
      Lines[I] := Line;
    end;

    Lines.SaveToFile(FilePath);
  finally
    Lines.Free;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  InstallDir: String;
  ResolveDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    InstallDir := ExpandConstant('{app}');
    ResolveDir := ExpandConstant(ResolvePath);

    RewriteLuaPathsInFile(ResolveDir + '\AutoVoice.lua', InstallDir);
  end;
end;

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\launch.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\launch.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\launch.bat"; Description: "Launch AutoVoice now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backend\audio_output"
Type: filesandordirs; Name: "{app}\autovoice_kill.txt"
Type: filesandordirs; Name: "{app}\autovoice_port.txt"
Type: filesandordirs; Name: "{app}\autovoice_jobs.json"
Type: filesandordirs; Name: "{app}\autovoice_results.json"
