; Inno Setup script for "Vedi Pocket PC".
;
; The output of `build_exe.bat` is staged at:
;   release/Vedi Pocket PC/   <- PyInstaller onedir bundle (VediPocketPC.exe + _internal/)
;   release/setup.iss        <- a copy of THIS file (so Inno Setup can find it relative to the bundle).
;
; Compile with:
;   "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" release\setup.iss
;
; The resulting `Vedi Pocket PC Setup-1.0.0.exe` is a single self-contained
; installer that copies the bundle into Program Files, creates Start Menu +
; Desktop shortcuts, and registers an uninstaller in Settings -> Apps.

#define MyAppName       "Vedi Pocket PC"
#define MyAppVersion    "1.0.0"
#define MyAppPublisher   "Vedi"
#define MyAppURL         "https://github.com/ajaysaagar-dev/Vedi-Pocket-PC"
#define MyAppExeName     "VediPocketPC.exe"
#define MyAppCopyright   "Copyright (c) Vedi. Released under the MIT License."

[Setup]
AppId={{B7F2CDE6-1A0E-4B71-8A60-3B6EE2E1F0A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
LicenseFile=..\LICENSE
OutputDir=..
OutputBaseFilename={#MyAppName} Setup-{#MyAppVersion}
SetupIconFile=..\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedalone
Name: "firewall";    Description: "Allow inbound TCP on ports 8000, 8080, 8090 (recommended)"; GroupDescription: "{cm:Firewall}"\n; Flags: checkedalone

[Files]
; Copy the entire PyInstaller onedir bundle straight into Program Files.
Source: "Vedi Pocket PC\*";           DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; The application icon used in Start Menu + uninstaller.
Source: "Vedi Pocket PC\logo.ico";   DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";         Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon and not desktopicon
Name: "{userdesktop}\{#MyAppName}";   Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"; Tasks: firewall

[Code]
const
  FirewallPortBackend = 8000;
  FirewallPortStream  = 8080;
  FirewallPortUi      = 8090;

function AddFirewallRule(Port: Integer; DisplayName: string): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if not IsAdminLoggedOn then begin
    Log('Not an admin; skipping firewall rule for port ' + IntToStr(Port));
    exit;
  end;
  Result := Exec(
    'netsh.exe',
    Format('advfirewall firewall add rule name="%s" dir=in action=allow protocol=TCP localport=%d', [DisplayName, Port]),
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode
  ) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    if IsTaskSelected('firewall') then begin
      AddFirewallRule(FirewallPortBackend, 'Vedi Pocket PC Backend (TCP 8000)');
      AddFirewallRule(FirewallPortStream,  'Vedi Pocket PC Stream  (TCP 8080)');
      AddFirewallRule(FirewallPortUi,      'Vedi Pocket PC UI      (TCP 8090)');
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then begin
    // Best-effort delete the persisted user data folder on uninstall.
    // Preserve the data folder when the user did not tick the firewall
    // task because we use that as an explicit "wipe everything" hint.
    if IsTaskSelected('firewall') then begin
      Exec(
        'cmd.exe',
        Format('/c rmdir /S /Q "%s\%s"', [ExpandConstant('{localappdata}'), '{#MyAppName}']),
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode
      );
    end;
  end;
end;
