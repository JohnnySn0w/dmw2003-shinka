; Build with ISCC /DStage=<absolute frozen launcher folder> /DRelease=<output>.
#ifndef Stage
  #error Stage is required
#endif
#ifndef Release
  #error Release is required
#endif
#ifndef Version
  #define Version "0.1.0"
#endif

[Setup]
AppId={{72DD6132-096E-409C-8AEC-FCBEC96B347C}
AppName=Shinka
AppVersion={#Version}
AppPublisher=Shinka contributors
AppPublisherURL=https://johnnysn0w.github.io/dmw2003-shinka/
DefaultDirName={localappdata}\Programs\Shinka
DefaultGroupName=Shinka
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#Release}
OutputBaseFilename=Shinka-Setup-{#Version}-windows-x64
SetupIconFile=..\assets\shinka.ico
UninstallDisplayIcon={app}\Shinka.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Shinka"; Filename: "{app}\Shinka.exe"; WorkingDir: "{app}"
Name: "{group}\Shinka Setup"; Filename: "{app}\Shinka.exe"; Parameters: "--settings"; WorkingDir: "{app}"
Name: "{autodesktop}\Shinka"; Filename: "{app}\Shinka.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Shinka.exe"; Description: "Set up Shinka"; Flags: nowait postinstall skipifsilent

; User data lives separately under LocalAppData\Shinka. Deliberately no
; UninstallDelete or wildcard cleanup: uninstall must retain cards and setup.
