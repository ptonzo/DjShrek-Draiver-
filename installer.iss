[Setup]
AppId={{B5C90D4B-12F1-4D89-A3B4-9B6E5C0A2D17}
AppName=DjShrek-Draiver Cyber Club
AppVersion=0.1.0
AppPublisher=Секисов М. В.
DefaultDirName={autopf}\DjShrek Draiver
DefaultGroupName=DjShrek-Draiver Cyber Club
UninstallDisplayName=DjShrek-Draiver Cyber Club
OutputDir=dist\installer
OutputBaseFilename=DjShrek-Draiver-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
Uninstallable=yes
CloseApplications=yes
RestartApplications=no
SetupIconFile=assets\\DjShrek-Draiver.ico
UninstallDisplayIcon={app}\\DjShrek Draiver.exe
LicenseFile=LICENSE.rtf

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные параметры:"; Flags: unchecked

[Files]
Source: "dist\DjShrek Draiver\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DjShrek Draiver"; Filename: "{app}\DjShrek Draiver.exe"
Name: "{autodesktop}\DjShrek Draiver"; Filename: "{app}\DjShrek Draiver.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DjShrek Draiver.exe"; Description: "Запустить DjShrek Draiver"; Flags: postinstall nowait skipifsilent
