"""
Configuración de pytest para la carpeta tests/.

Los casos de prueba importan los paquetes de la aplicacion (``db`` y
``ui``) y el ``main.py`` de la raiz del proyecto. Al ejecutar pytest desde
cualquier ubicacion, este conftest agrega la raiz del repositorio al
``sys.path`` para que esos imports resuelvan sin importar el directorio
desde el que se invoque la suite.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
