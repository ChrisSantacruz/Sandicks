"""Application entrypoint."""

import os

import uvicorn

from src.api.app import create_app
from src.config.settings import get_settings

app = create_app()


def run() -> None:
    """Run the application with uvicorn."""
    settings = get_settings()
    port = int(os.getenv("PORT", str(settings.app_port)))
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=port,
        reload=settings.app_env == "dev",
    )


if __name__ == "__main__":
    run()
