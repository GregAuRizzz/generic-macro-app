@echo off
echo Installing requirements...
pip install -r requirements.txt
pip install pyinstaller

echo Building GenericMacro EXE...
pyinstaller --noconfirm --onedir --windowed --name "GenericMacro" --icon NONE main.py

echo Done! The executable is located in the "dist/GenericMacro" folder.
pause