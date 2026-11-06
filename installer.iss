#pragma code_page=65001

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

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные параметры:"; Flags: unchecked

[Files]
Source: "dist\DjShrek Draiver\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.rtf"; Flags: dontcopy

[Icons]
Name: "{group}\DjShrek Draiver"; Filename: "{app}\DjShrek Draiver.exe"
Name: "{autodesktop}\DjShrek Draiver"; Filename: "{app}\DjShrek Draiver.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DjShrek Draiver.exe"; Description: "Запустить DjShrek Draiver"; Flags: postinstall nowait skipifsilent

[Code]
var
  LicensePage: TWizardPage;
  AcceptLicenseCheck: TNewCheckBox;
  ViewLicenseButton: TNewButton;

procedure AcceptLicenseClick(Sender: TObject);
begin
  WizardForm.NextButton.Enabled := AcceptLicenseCheck.Checked;
end;

procedure ViewLicenseClick(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ExtractTemporaryFile('LICENSE.rtf');
  if not ShellExec('open', ExpandConstant('{tmp}\LICENSE.rtf'), '', '',
       SW_SHOWNORMAL, ewNoWait, ErrorCode) then
    MsgBox('Не удалось открыть файл соглашения. Файл LICENSE.rtf включён в установщик.',
      mbError, MB_OK);
end;

procedure InitializeWizard;
var
  InfoText: TNewStaticText;
begin
  LicensePage := CreateCustomPage(wpWelcome,
    'Лицензионное соглашение',
    'Ознакомьтесь с условиями использования DjShrek-Draiver Cyber Club.');

  InfoText := TNewStaticText.Create(LicensePage);
  InfoText.Parent := LicensePage.Surface;
  InfoText.Left := 0;
  InfoText.Top := ScaleY(8);
  InfoText.Width := LicensePage.SurfaceWidth;
  InfoText.Height := ScaleY(76);
  InfoText.AutoSize := False;
  InfoText.WordWrap := True;
  InfoText.Caption :=
    'Автор и правообладатель: Секисов М. В.' + #13#10 +
    'Адрес: Тюменская область, с. Омутинское, ул. Терешковой, д. 12, кв. 16.' + #13#10#13#10 +
    'Лицензия разрешает личное использование программы. Взлом, обход защиты, ' +
    'незаконное копирование, распространение и коммерческое использование без ' +
    'письменного разрешения правообладателя запрещены. Ответственность определяется ' +
    'законодательством Российской Федерации.';

  ViewLicenseButton := TNewButton.Create(LicensePage);
  ViewLicenseButton.Parent := LicensePage.Surface;
  ViewLicenseButton.Left := 0;
  ViewLicenseButton.Top := ScaleY(96);
  ViewLicenseButton.Width := ScaleX(190);
  ViewLicenseButton.Height := ScaleY(30);
  ViewLicenseButton.Caption := 'Просмотреть полный текст';
  ViewLicenseButton.OnClick := @ViewLicenseClick;

  AcceptLicenseCheck := TNewCheckBox.Create(LicensePage);
  AcceptLicenseCheck.Parent := LicensePage.Surface;
  AcceptLicenseCheck.Left := 0;
  AcceptLicenseCheck.Top := ScaleY(148);
  AcceptLicenseCheck.Width := LicensePage.SurfaceWidth;
  AcceptLicenseCheck.Height := ScaleY(36);
  AcceptLicenseCheck.WordWrap := True;
  AcceptLicenseCheck.Checked := False;
  AcceptLicenseCheck.Caption :=
    'Я прочитал(а) и принимаю условия лицензионного соглашения.';
  AcceptLicenseCheck.OnClick := @AcceptLicenseClick;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (LicensePage <> nil) and (CurPageID = LicensePage.ID) then
    WizardForm.NextButton.Enabled := AcceptLicenseCheck.Checked;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (LicensePage <> nil) and (CurPageID = LicensePage.ID) and
     (not AcceptLicenseCheck.Checked) then
  begin
    MsgBox('Для продолжения установки необходимо принять лицензионное соглашение.',
      mbInformation, MB_OK);
    Result := False;
  end;
end;
