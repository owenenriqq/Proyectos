[Setup]
AppName=EzSetup
AppVerName=EzSetup
AppVersion=1.0.6
AppPublisher=EzSetup
DefaultDirName={pf}\EzSetup
DefaultGroupName=EzSetup
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=EzSetupInstaller
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
SetupIconFile="E:\Owen\Programs\CMD\EasySetup\EzSetup.ico"
UninstallDisplayIcon={app}\EzSetup.ico
VersionInfoVersion=1.0.6
VersionInfoProductVersion=1.0.6
VersionInfoTextVersion=1.0.6

[Files]
Source: "E:\Owen\Programs\CMD\EzSetup\EzSetup.bat"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\RegasmDotnetCheck.bat"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\PermisosSolSistemas.ps1"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\KMS.bat"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\DescargarSistemaContable.ps1"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\DescargarFortiClient.ps1"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\DescargarAWSVPNClient.ps1"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\Credenciales de Fox.bat"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\CopiarEidicoPrueba.ps1"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\EzSetup.exe"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\EzSetup.ico"; DestDir: "{app}"
Source: "E:\Owen\Programs\CMD\EzSetup\EzSetup.vbs"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Run]
Filename: "{app}\EasySetup.exe"; Description: "Ejecutar EasySetup"; Flags: nowait postinstall skipifsilent

[Icons]
Name: "{commondesktop}\EasySetup"; Filename: "{app}\EasySetup.vbs"; IconFilename: "{app}\EzSetup.ico"; IconIndex: 0
Name: "{group}\EasySetup"; Filename: "{app}\EasySetup.vbs"; IconFilename: "{app}\EzSetup.ico"; IconIndex: 0