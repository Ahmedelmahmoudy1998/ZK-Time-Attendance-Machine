$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
python -m unittest discover -p 'test_*.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name 'Oasis Attend' --distpath ../portable --workpath build-portable --specpath build-portable --additional-hooks-dir hooks --hidden-import pyzatt.pyzatt --icon "$PSScriptRoot\brand\app-icon.ico" --add-data "$PSScriptRoot\assets;assets" --add-data "$PSScriptRoot\brand;brand" --exclude-module zk --exclude-module matplotlib --exclude-module pandas --exclude-module numpy app.py
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed' }
python make_notices.py
if ($LASTEXITCODE -ne 0) { throw 'Notice generation failed' }
$innoCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($innoCompiler) { & $innoCompiler.Source installer.iss }
elseif (Test-Path -LiteralPath 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe') { & 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' installer.iss }
else { throw 'Portable is ready. Install Inno Setup 6 to compile installer.iss.' }
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
