"""启动本地 Web 服务。"""

import uvicorn

from app.config import load_settings
from app.runtime_check import UnsupportedRuntimeError, ensure_supported_runtime


if __name__ == "__main__":
    try:
        ensure_supported_runtime()
    except UnsupportedRuntimeError as exc:
        raise SystemExit(f"[运行环境不兼容]\n{exc}") from exc
    settings = load_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
