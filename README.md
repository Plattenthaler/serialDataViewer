# serialDataViewer
displays serial integers seperated by \n command with matplotlib

standard baudrate 115200 kBaud, changeable in code

standard Port COM9, changeable by starting with comandline "serialDataViewer.py COM3"

Tested with: 
Python            3.8.1

scipy             1.4.1
pysinewave        0.0.6
pyserial          3.5
matplotlib        3.4.2
numpy             1.20.3
cx-Freeze         6.6

Build Windows-exe:
install cx_Freeze with "pip install --upgrade cx_Freeze"
run "cxfreeze serialDataViewer_setup_to_exe.py" (file generated with cxfreeze-quickstart)
