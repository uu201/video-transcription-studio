"""启动本地 Web 服务。"""

import uvicorn

from app.config import load_settings


if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
