# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
import asyncio

# Импортируем пул из api/v1
from api.v1 import PROCESS_POOL

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Minecraft Map Viewer")

web_dir = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=web_dir / "static"), name="static")
templates = Jinja2Templates(directory=web_dir / "templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from api.v1 import router as api_router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("shutdown")
async def shutdown_event():
    """Корректно завершаем пул процессов."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, PROCESS_POOL.shutdown, True)
    logging.info("Process pool shut down.")
