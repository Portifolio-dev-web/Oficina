import sys
from pathlib import Path

# Permite "import rate_limit" (e outros módulos de backend/) nos testes,
# já que pytest por padrão só coloca backend/tests/ no sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
