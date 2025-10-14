import sys
import types
from pathlib import Path


if "psycopg2" not in sys.modules:  # pragma: no cover - disponibiliza stub para ambiente de teste
    psycopg2 = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")
    pool = types.ModuleType("psycopg2.pool")

    class _UnavailablePool:
        def __init__(self, *args, **kwargs):  # noqa: D401 - comportamento simplificado para testes
            raise RuntimeError("psycopg2 is not installed in the test environment")

        def closeall(self) -> None:  # pragma: no cover - nunca chamado em testes atuais
            return None

    extras.DictCursor = object

    class _Json:
        def __init__(self, value):
            self.adapted = value

        def dumps(self, value):  # pragma: no cover - compatibilidade simples
            return value

    extras.Json = _Json
    pool.SimpleConnectionPool = _UnavailablePool

    psycopg2.extras = extras
    psycopg2.pool = pool

    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras
    sys.modules["psycopg2.pool"] = pool


if "pydantic" not in sys.modules:  # pragma: no cover - stub mínimo para tipagens
    pydantic = types.ModuleType("pydantic")

    class _BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self):  # pragma: no cover - compatibilidade básica
            return self.__dict__.copy()

    def _field(default=None, **_kwargs):  # pragma: no cover - ignora validações
        return default

    class _ConfigDict(dict):
        pass

    pydantic.BaseModel = _BaseModel
    pydantic.ConfigDict = _ConfigDict
    pydantic.Field = _field

    sys.modules["pydantic"] = pydantic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
