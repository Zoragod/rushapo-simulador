import os, sys

# Ajusta la ruta al directorio del proyecto en PythonAnywhere
PROJECT_PATH = os.path.expanduser('~/rushapo-simulador')
if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

# Importa la instancia Flask como 'application' para que PythonAnywhere la detecte
from app import app as application  # noqa
