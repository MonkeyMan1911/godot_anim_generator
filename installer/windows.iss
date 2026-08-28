#define MyAppName "Godot Anim Generator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Godot Anim Generator"
#define MyAppExeName "godot-anim-generator.exe"

[Setup]
AppId={{8E7F4E44-4D5D-4D3E-9F4A-7D6C1B9B2A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\Godot Anim Generator
DefaultGroupName={#MyAppName}

OutputDir=..\installer-output
OutputBaseFilename=Godot-Anim-Generator-Setup

Compression=lzma
SolidCompression=yes

WizardStyle=modern

SetupIconFile=..\icon.ico

UninstallDisplayIcon={app}\godot-anim-generator.exe

[Files]
Source: "..\dist\godot-anim-generator.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Godot Anim Generator"; Filename: "{app}\godot-anim-generator.exe"
Name: "{autodesktop}\Godot Anim Generator"; Filename: "{app}\godot-anim-generator.exe"

[Run]
Filename: "{app}\godot-anim-generator.exe"; Description: "Launch Godot Anim Generator"; Flags: nowait postinstall skipifsilent
