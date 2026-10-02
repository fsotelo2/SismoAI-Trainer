
#define MyAppName "SismoAI Trainer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SismoAI Trainer"
#define MyAppExeName "SismoAI-Trainer.exe"

[Setup]
AppId={{A7D36C91-5E42-4F8B-9C21-6D0A4B73E815}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SismoAI Trainer
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\installer-output
OutputBaseFilename=SismoAI-Trainer-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\dist\SismoAI-Trainer\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SismoAI Trainer"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SismoAI Trainer"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Iniciar SismoAI Trainer"; \
    Flags: postinstall nowait skipifsilent
