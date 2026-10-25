@echo off
REM ---------------------------------------------------------------------------
REM Guilliman - Build de ejecutable nativo de 32 bits (PyInstaller)
REM
REM Genera dist\Guilliman\Guilliman.exe para Windows de 32 bits (publico objetivo).
REM Requiere Python 3.12 de 32 bits instalado. El launcher "py" selecciona el
REM 3.12 de 32 bits con "py -3.12-32".
REM
REM Nota: greenlet no publica wheel de 32 bits (ni 3.11 ni 3.12), asi que
REM SQLAlchemy se instala con --no-deps (la app es 100%% sincrona).
REM
REM Uso:
REM   build.bat                  -> usa "py -3.12-32"
REM   build.bat ruta\python.exe  -> usa el interprete indicado
REM ---------------------------------------------------------------------------
setlocal EnableDelayedExpansion

set OVERRIDE=%1
if "%OVERRIDE%"=="" (
  set RUN=py -3.12-32
) else (
  set RUN="%~1"
)

echo [Guilliman] Usando Python: %RUN%
%RUN% -m pip install --no-deps sqlalchemy==2.0.52
%RUN% -m pip install typing_extensions
%RUN% -m pip install PyQt5==5.15.11 pyqt-fluent-widgets==1.11.3 "PyQt5-Frameless-Window>=0.8.0" pydantic==2.13.4 "reportlab>=4.0,<5.0"
%RUN% -m pip install pyinstaller

%RUN% -m PyInstaller -w --name Guilliman --noconfirm --clean ^
  --icon=assets\icon.ico ^
  --add-data "assets\icon.ico;assets" ^
  --hidden-import qfluentwidgets ^
  --hidden-import qframelesswindow ^
  --hidden-import reportlab ^
  --hidden-import PyQt5.QtPrintSupport ^
  --collect-all qfluentwidgets ^
  --collect-all qframelesswindow ^
  main.py

echo [Guilliman] Listo. El ejecutable esta en dist\Guilliman\Guilliman.exe
endlocal
