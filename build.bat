@echo off
echo Gerando executavel...
pip install pyinstaller
pyinstaller --onefile --name notas_de_corte --add-data "dados.json;." notas_de_corte.py
copy dados.json dist\dados.json
echo.
echo Pronto! Executavel e dados.json estao em: dist\
pause
