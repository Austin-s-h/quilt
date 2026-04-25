import asyncio
import base64
import functools
import inspect
import os
import re
import subprocess
import tempfile
import time
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import fastapi
import requests

from . import preview, s3select, tabular_preview, thumbnail

LAMBDAS = {
    "thumbnail": thumbnail,
    "preview": preview,
    "s3select": s3select,
    "tabular-preview": tabular_preview,
}

lambdas = fastapi.FastAPI()

REPO_ROOT = Path(__file__).resolve().parents[4]
LAMBDA_RUNNER = REPO_ROOT / "lambdas" / "local_runner.py"
DEFAULT_LAMBDA_PYTHON = "3.13"


@dataclass(frozen=True)
class RealLambdaConfig:
    name: str
    cwd: Path
    module: str
    handler_attr: str
    port: int


REAL_LAMBDAS = {
    "preview": RealLambdaConfig(
        name="preview",
        cwd=REPO_ROOT / "lambdas" / "preview",
        module="t4_lambda_preview",
        handler_attr="lambda_handler",
        port=int(os.getenv("QUILT_LOCAL_LAMBDA_PREVIEW_PORT", "18082")),
    ),
    "tabular-preview": RealLambdaConfig(
        name="tabular-preview",
        cwd=REPO_ROOT / "lambdas" / "tabular_preview",
        module="t4_lambda_tabular_preview",
        handler_attr="lambda_handler",
        port=int(os.getenv("QUILT_LOCAL_LAMBDA_TABULAR_PREVIEW_PORT", "18083")),
    ),
    "thumbnail": RealLambdaConfig(
        name="thumbnail",
        cwd=REPO_ROOT / "lambdas" / "thumbnail",
        module="t4_lambda_thumbnail",
        handler_attr="lambda_handler",
        port=int(os.getenv("QUILT_LOCAL_LAMBDA_THUMBNAIL_PORT", "18081")),
    ),
    "transcode": RealLambdaConfig(
        name="transcode",
        cwd=REPO_ROOT / "lambdas" / "transcode",
        module="t4_lambda_transcode",
        handler_attr="lambda_handler",
        port=int(os.getenv("QUILT_LOCAL_LAMBDA_TRANSCODE_PORT", "18084")),
    ),
}

_runner_processes: dict[str, subprocess.Popen] = {}


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def _lambda_env_prefix(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", name.upper())


def _extract_python_version(spec: str | None) -> str | None:
    if not spec:
        return None
    match = re.search(r"(\d+)\.(\d+)", spec)
    if match is None:
        return None
    return f"{match.group(1)}.{match.group(2)}"


@lru_cache(maxsize=None)
def _project_python_version(cwd: Path) -> str | None:
    pyproject_path = cwd / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    requires_python = pyproject.get("project", {}).get("requires-python")
    return _extract_python_version(requires_python)


def _configured_lambda_python(config: RealLambdaConfig) -> str:
    specific_override = os.getenv(f"QUILT_LOCAL_LAMBDA_{_lambda_env_prefix(config.name)}_PYTHON")
    global_override = os.getenv("QUILT_LOCAL_LAMBDA_PYTHON")
    return specific_override or global_override or _project_python_version(config.cwd) or DEFAULT_LAMBDA_PYTHON


def _strict_lambda_runtime() -> bool:
    return _truthy_env("QUILT_LOCAL_LAMBDA_STRICT")


def _normalized_response_headers(headers: dict[str, str], body: bytes) -> dict[str, str]:
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
    }
    normalized = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}
    normalized["content-length"] = str(len(body))
    return normalized


def _runner_log_path(name: str) -> Path:
    return Path(tempfile.gettempdir()) / f"quilt-local-lambda-{name}.log"


def _runner_start_error(config: RealLambdaConfig, proc: subprocess.Popen) -> RuntimeError:
    log_path = _runner_log_path(config.name)
    detail = ""
    if log_path.exists():
        detail = log_path.read_text(errors="ignore")[-4000:].strip()
    message = f"LOCAL lambda runner for {config.name} exited with code {proc.returncode}"
    if detail:
        message = f"{message}: {detail}"
    return RuntimeError(message)


def _real_lambda_url(config: RealLambdaConfig, path: str) -> str:
    suffix = f"/{path}" if path else ""
    return f"http://127.0.0.1:{config.port}/lambda{suffix}"


def _runner_healthcheck(config: RealLambdaConfig) -> bool:
    try:
        response = requests.get(f"http://127.0.0.1:{config.port}/healthz", timeout=0.5)
    except requests.RequestException:
        return False
    return response.status_code == 200


def _start_runner(config: RealLambdaConfig) -> None:
    proc = _runner_processes.get(config.name)
    if proc is not None and proc.poll() is None:
        return

    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "QUILT_LOCAL_ORIGIN": os.getenv("QUILT_LOCAL_ORIGIN", "http://localhost:3000"),
        "PYTHONPATH": ":".join(
            filter(
                None,
                [
                    str(config.cwd / "src"),
                    str(REPO_ROOT / "lambdas" / "shared" / "src"),
                    os.environ.get("PYTHONPATH"),
                ],
            )
        ),
    }
    log_path = _runner_log_path(config.name)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w")
    python_version = _configured_lambda_python(config)
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "--managed-python",
            "--python",
            python_version,
            "--no-dev",
            "python",
            str(LAMBDA_RUNNER),
            config.module,
            config.handler_attr,
            "--port",
            str(config.port),
        ],
        cwd=config.cwd,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    _runner_processes[config.name] = proc

    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            raise _runner_start_error(config, proc)
        if _runner_healthcheck(config):
            return
        time.sleep(0.2)

    raise RuntimeError(f"Timed out waiting for LOCAL lambda runner: {config.name}")


def shutdown_runners() -> None:
    for proc in _runner_processes.values():
        if proc.poll() is None:
            proc.terminate()
    for proc in _runner_processes.values():
        if proc.poll() is None:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    _runner_processes.clear()


async def _invoke_local_lambda(request: fastapi.Request, name: str, path: str):
    req_body = await request.body()
    args = {
        "httpMethod": request.method,
        "path": request.url.path,
        "pathParameters": {"proxy": path},
        "queryStringParameters": dict(request.query_params) or None,
        "headers": request.headers or None,
        "body": base64.b64encode(req_body),
        "isBase64Encoded": True,
    }

    result = await asyncio.get_running_loop().run_in_executor(
        None,
        functools.partial(LAMBDAS[name].lambda_handler, args, None),
    )

    body = result["body"]
    if result.get("isBase64Encoded", False):
        content = base64.b64decode(body)
    elif isinstance(body, memoryview):
        content = body.tobytes()
    else:
        content = body.encode()

    response_headers = _normalized_response_headers(dict(result["headers"]), content)
    return fastapi.Response(content=content, status_code=result["statusCode"], headers=response_headers)


async def _proxy_real_lambda(request: fastapi.Request, config: RealLambdaConfig, path: str):
    response = None
    try:
        await asyncio.get_running_loop().run_in_executor(None, functools.partial(_start_runner, config))
        req_body = await request.body()
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            functools.partial(
                requests.request,
                request.method,
                _real_lambda_url(config, path),
                **{
                    **(
                        {"stream": True}
                        if (
                            "stream" in inspect.signature(requests.request).parameters
                            or any(
                                param.kind == inspect.Parameter.VAR_KEYWORD
                                for param in inspect.signature(requests.request).parameters.values()
                            )
                        )
                        else {}
                    ),
                    "params": list(request.query_params.multi_items()),
                    "headers": {
                        k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}
                    },
                    "data": req_body,
                    "timeout": 120,
                },
            ),
        )
    except requests.RequestException as exc:
        if config.name in LAMBDAS and not _strict_lambda_runtime():
            try:
                return await _invoke_local_lambda(request, config.name, path)
            except Exception:
                pass
        return fastapi.responses.JSONResponse(status_code=502, content={"error": str(exc), "lambda": config.name})
    except Exception as exc:
        if config.name in LAMBDAS and not _strict_lambda_runtime():
            try:
                return await _invoke_local_lambda(request, config.name, path)
            except Exception:
                pass
        return fastapi.responses.JSONResponse(status_code=500, content={"error": str(exc), "lambda": config.name})

    assert response is not None
    if response.status_code >= 500 and config.name in LAMBDAS and not _strict_lambda_runtime():
        close = getattr(response, "close", None)
        if callable(close):
            close()
        try:
            return await _invoke_local_lambda(request, config.name, path)
        except Exception:
            pass

    raw = getattr(response, "raw", None)
    if raw is not None and hasattr(raw, "read"):
        try:
            raw_body = raw.read(decode_content=False)
        except TypeError:
            raw_body = raw.read()
    else:
        raw_body = response.content
    response_headers = _normalized_response_headers(dict(response.headers), raw_body)
    close = getattr(response, "close", None)
    if callable(close):
        close()
    return fastapi.Response(content=raw_body, status_code=response.status_code, headers=response_headers)


@lambdas.api_route("/{name}", methods=["GET", "POST", "OPTIONS"])
@lambdas.api_route("/{name}/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def lambda_request(request: fastapi.Request, name: str, path: str = ""):
    if name in REAL_LAMBDAS:
        return await _proxy_real_lambda(request, REAL_LAMBDAS[name], path)

    if name not in LAMBDAS:
        raise fastapi.HTTPException(404, "No such lambda")
    return await _invoke_local_lambda(request, name, path)
