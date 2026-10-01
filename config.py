# Configuración compartida del proyecto.
#
# Carga el archivo eam_rag/.env (y, si existe, también PROYECTO/.env).
# Las variables ya definidas en el sistema tienen prioridad sobre las del
# archivo, y eam_rag/.env tiene prioridad sobre PROYECTO/.env.
#
# Uso desde cualquier módulo:
#   from config import OPENAI_API_KEY, OPENAI_MODEL

import os

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)

for path in (os.path.join(HERE, '.env'), os.path.join(PROJECT_ROOT, '.env')):
    if os.path.exists(path):
        load_dotenv(path, override=False)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.5')


def require_openai_key() -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            'Falta OPENAI_API_KEY. Defínela en el archivo '
            f'{os.path.join(HERE, ".env")} o como variable de entorno.')
    return OPENAI_API_KEY
