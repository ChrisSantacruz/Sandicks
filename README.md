# Sandicks Telegram Bot

Bot de Telegram para generacion de memes con Python.

## Requisitos

- Python 3.11+
- Token de bot de Telegram
- Variables de entorno en `.env`

## Instalacion local

1. Crear y activar entorno virtual.
2. Instalar dependencias:
   `pip install -r requirements.txt`
3. Configurar `.env`.
4. Ejecutar el bot:
   `python src/main.py`

## Deploy en Render

Este repo ya incluye `render.yaml`, asi que puedes hacer deploy con Blueprint.

Configuracion usada:

- Root Directory: `.`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m src.main`
- Health Check Path: `/health`

Variables obligatorias en Render (Environment):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_CHAT_ID`
- `HUGGINGFACE_TOKEN`
- `GROQ_API_KEY`

Variables de app recomendadas:

- `APP_ENV=prod`
- `APP_HOST=0.0.0.0`

Nota: Render inyecta `PORT` automaticamente y la app ya lo toma para iniciar correctamente.
Los prompts viven en `src/prompts` para que queden versionados en el repo y disponibles en deploy.
