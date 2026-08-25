"""Production ASGI entrypoint configured exclusively from environment variables."""

from .runtime import create_environment_app


app = create_environment_app()
