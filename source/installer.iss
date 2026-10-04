#define MyAppName "Oasis Attend"
#define MyAppVersion "1.1.7"
[Setup]
AppId={{903970FA-DDA6-476D-9B99-B8C3EE283B91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Oasis Digital Solutions
AppPublisherURL=https://www.oasis-it.com
DefaultDirName={localappdata}\Programs\Oasis Attend
DefaultGroupName=Oasis Attend
PrivilegesRequired=lowest
OutputDir=..\installer
OutputBaseFilename=Oasis Attend Setup
SetupIconFile=brand\app-icon.ico
UninstallDisplayIcon={app}\Oasis Attend.exe
LicenseFile=..\LICENSE.txt
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "..\portable\Oasis Attend\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Oasis Attend"; Filename: "{app}\Oasis Attend.exe"
Name: "{autodesktop}\Oasis Attend"; Filename: "{app}\Oasis Attend.exe"
