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



if "grpc" not in sys.modules:  # pragma: no cover - stub simplificado para testes
    grpc = types.ModuleType("grpc")

    class _StatusCode:
        INVALID_ARGUMENT = object()
        FAILED_PRECONDITION = object()
        INTERNAL = object()

    class _RpcError(Exception):
        def details(self):
            return str(self)

        def code(self):
            return _StatusCode.INTERNAL

    def _insecure_channel(_target):  # pragma: no cover - canal fake
        return types.SimpleNamespace(unary_unary=lambda *_args, **_kwargs: (lambda request: request))

    def _server(_executor):  # pragma: no cover - servidor fake
        return types.SimpleNamespace(
            add_insecure_port=lambda *_args, **_kwargs: None,
            start=lambda: None,
            wait_for_termination=lambda: None,
        )

    grpc.StatusCode = _StatusCode
    grpc.RpcError = _RpcError
    grpc.insecure_channel = _insecure_channel
    grpc.server = _server

    sys.modules["grpc"] = grpc

if "dotenv" not in sys.modules:  # pragma: no cover - stub mínimo
    dotenv = types.ModuleType("dotenv")

    def _load_dotenv(*_args, **_kwargs):  # pragma: no cover - carrega nada
        return False

    dotenv.load_dotenv = _load_dotenv
    sys.modules["dotenv"] = dotenv
    sys.modules["dotenv.load_dotenv"] = _load_dotenv
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
