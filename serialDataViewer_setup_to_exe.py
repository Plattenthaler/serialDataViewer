from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {'packages': [], 'excludes': []}

base = 'Console'

executables = [
    Executable('serialDataViewer.py', base=base)
]

setup(name='serialDataViewer',
      version = '1.0',
      description = 'Grafische Visualisierung einkommender Zahlen über eine Serielle Schnitstelle',
      options = {'build_exe': build_options},
      executables = executables)
