# serialDataViewer
displays serial integers seperated by \n command with matplotlib

standard baudrate 115200 kBaud, changeable in code

standard Port COM9, changeable by starting with comandline "serialDataViewer.py COM3"

### Versions

Tested with: 
 * Python            3.8.1
 * 
 * pysinewave        0.0.6
 * pyserial          3.5
 * matplotlib        3.7.0
 * numpy             1.24.2
 * pyinstaller       4.8

# Build Windows-exe:
run "build_main_with_pyinstaller.py"

# Git Hooks

copy the two files "post-commit" and "post-checkout" from the folder git-hooks into your local folder .git\hooks\
This will change the content of the file version.py. If there are no git hooks, default version strings are used.

before V1.2 the standart process was to commit a default version of the version file and remove the file from tracking with "git update-index --assume-unchanged <file>"

# Serial Viewer to executable

to build the Tool just run the script "build_main_with_pyinstaller.py"


