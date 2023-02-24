# serialDataViewer
displays serial integers seperated by \n command with matplotlib

standard baudrate 115200 kBaud, changeable in code

standard Port COM9, changeable by starting with comandline "serialDataViewer.py COM3"

Tested with: 
Python            3.8.1

scipy             1.10.1
pysinewave        0.0.6
pyserial          3.5
matplotlib        3.7.0
numpy             1.24.2
cx-Freeze         6.6 (6.14.4 installation error on Windows)

Build Windows-exe:
install cx_Freeze with "pip install --upgrade cx_Freeze"
run "cxfreeze serialDataViewer_setup_to_exe.py" (file generated with cxfreeze-quickstart)

# Git Hooks

copy the two files "post-commit" and "post-checkout" from the folder git-hooks into your local folder .git\hooks\
This will change the content of the file version.py. If there are no git hooks, default version strings are used.

before V1.2 the standart process was to commit a default version of the version file and remove the file from tracking with "git update-index --assume-unchanged <file>"