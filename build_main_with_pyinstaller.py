import os
import shutil
import PyInstaller.__main__

shutil.rmtree("__pycache__", ignore_errors=True) #remove cached directories
shutil.rmtree("build", ignore_errors=True) #remove build directories
shutil.rmtree("dist", ignore_errors=True) #remove build directories

if os.name == "nt":
	print("Using Windwos commands")
	PyInstaller.__main__.run([
		'windows_main.spec'
	])
# if os.name == "posix":
	# print("Using Windwos coomands")
	# PyInstaller.__main__.run([
		# 'linux_main.spec'
	# ])