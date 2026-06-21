[Setup]
; AppId identifie l'application de façon unique et stable.
; ⚠️ NE JAMAIS modifier cette valeur entre les versions, sinon Windows
; considérera chaque mise à jour comme une application différente.
AppId={{56AECC74-FC7D-477C-96C5-5B3B4FB1C467}
AppName=PC Optimizer Pro
AppVersion=3.4
DefaultDirName={autopf}\PCOptimizerPro
DefaultGroupName=PC Optimizer Pro
OutputBaseFilename=PCOptimizerPro_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\PCOptimizerPro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PC Optimizer Pro"; Filename: "{app}\PCOptimizerPro.exe"
Name: "{commondesktop}\PC Optimizer Pro"; Filename: "{app}\PCOptimizerPro.exe"

[Run]
Filename: "{app}\PCOptimizerPro.exe"; Description: "Lancer PC Optimizer Pro"; Flags: nowait postinstall skipifsilent
