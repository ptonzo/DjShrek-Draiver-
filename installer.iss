[Setup]
AppId={{B5C90D4B-12F1-4D89-A3B4-9B6E5C0A2D17}
AppName=DjShrek-Draiver Cyber Club
AppVersion=0.2.0
AppPublisher=Секисов М. В.
DefaultDirName={autopf}\DjShrek-Draiver Cyber Club
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
SetupIconFile=assets\DjShrek-Draiver.ico
UninstallDisplayIcon={app}\DjShrek-Draiver Cyber Club.exe
LicenseFile=LICENSE.rtf

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные параметры:"; Flags: unchecked

[Files]
Source: "dist\DjShrek-Draiver Cyber Club\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DjShrek-Draiver Cyber Club"; Filename: "{app}\DjShrek-Draiver Cyber Club.exe"; IconFilename: "{app}\DjShrek-Draiver Cyber Club.exe"
Name: "{autodesktop}\DjShrek-Draiver Cyber Club"; Filename: "{app}\DjShrek-Draiver Cyber Club.exe"; IconFilename: "{app}\DjShrek-Draiver Cyber Club.exe"; Tasks: desktopicon

[InstallDelete]
Type: files; Name: "{autodesktop}\DjShrek Draiver.lnk"
Type: files; Name: "{group}\DjShrek Draiver.lnk"

[Run]
Filename: "{app}\DjShrek-Draiver Cyber Club.exe"; Description: "Запустить DjShrek-Draiver Cyber Club"; Flags: postinstall nowait skipifsilent
