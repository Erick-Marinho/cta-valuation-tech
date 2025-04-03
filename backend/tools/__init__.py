import sys
from pathlib import Path

# Adiciona o diretório raiz (backend) ao PYTHONPATH
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))
