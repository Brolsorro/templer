pip install pyinstaller
pyinstaller -F --add-data="libs/*;." templer.py
@RD /S /Q build
