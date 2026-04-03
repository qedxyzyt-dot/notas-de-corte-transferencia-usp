@echo off
echo Gerando executavel...
pip install pyinstaller
pyinstaller --onefile --name notas_de_corte --add-data "dados.json;." notas_de_corte.py
echo.
echo Executavel gerado em: dist\notas_de_corte.exe
echo Copie o arquivo dados.json para a mesma pasta do .exe
pause
