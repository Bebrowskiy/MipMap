# api/v1.py
from fastapi import APIRouter, Response, UploadFile, Form
from fastapi.responses import FileResponse
from core.models import WorldData
from core.player_manager import player_manager
from core.chunk_storage import update_blocks, get_blocks_in_region, invalidate_cache_for_blocks
from core.tile_worker import render_tile_in_process  # ← НОВЫЙ импорт
from pathlib import Path
from PIL import Image
import asyncio
from concurrent.futures import ProcessPoolExecutor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Пул процессов для рендеринга (глобальный)
PROCESS_POOL = ProcessPoolExecutor(max_workers=4)

# Папки
TEXTURE_DIR = Path("assets/textures/blocks")
TILE_CACHE_DIR = Path("data/tile_cache")
TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/worlds")
async def update_world(data: WorldData):
    block_tuples = [
        (b.coordinates[0], b.coordinates[1], b.coordinates[2], b.name)
        for b in data.blocks
    ]
    await update_blocks("overworld", block_tuples)
    invalidate_cache_for_blocks(blocks=block_tuples)
    return {"status": "ok", "updated": len(block_tuples)}

@router.get("/tiles/{dimension}/{z}/{x}/{y}.webp")
async def get_tile(dimension: str, z: int, x: int, y: int):
    # Ограничение zoom (опционально, но рекомендуется)
    if z < 1 or z > 5:
        return Response(status_code=404)

    cache_path = TILE_CACHE_DIR / str(dimension) / str(z) / str(x)
    cache_file = cache_path / f"{y}.webp"

    if cache_file.exists():
        return FileResponse(cache_file, media_type="image/webp")

    try:
        scale = 2 ** z
        tile_size_px = 256
        px_min = x * tile_size_px
        pz_min = y * tile_size_px
        px_max = px_min + tile_size_px
        pz_max = pz_min + tile_size_px

        x_min = int(px_min // scale) - 1
        x_max = int(px_max // scale) + 1
        z_min = int(pz_min // scale) - 1
        z_max = int(pz_max // scale) + 1

        raw_blocks = await get_blocks_in_region("overworld", x_min, x_max, z_min, z_max)

        if not raw_blocks:
            # Прозрачный тайл
            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            cache_path.mkdir(parents=True, exist_ok=True)
            img.save(cache_file, format="WEBP", lossless=True)
            return FileResponse(cache_file, media_type="image/webp")

        # === РЕНДЕРИНГ В ОТДЕЛЬНОМ ПРОЦЕССЕ ===
        loop = asyncio.get_event_loop()
        image_bytes = await loop.run_in_executor(
            PROCESS_POOL,
            render_tile_in_process,
            raw_blocks,  # список кортежей (x, y, z, name)
            x,
            y,
            z
        )

        # Сохраняем в кэш
        cache_path.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "wb") as f:
            f.write(image_bytes)

        return FileResponse(cache_file, media_type="image/webp")

    except Exception:
        logger.exception("Tile render error")
        return Response(status_code=500, content="Render failed")

@router.post("/players")
async def update_player(
    nickname: str = Form(...),
    x: int = Form(...),
    y: int = Form(...),
    z: int = Form(...),
    face: UploadFile = Form(...)
):
    face_bytes = await face.read()
    await player_manager.update_player(nickname, x, y, z, face_bytes)
    return {"status": "ok"}

@router.get("/players")
async def get_players_in_view(
    x_min: int, x_max: int,
    z_min: int, z_max: int
):
    players = await player_manager.get_players_in_region(x_min, x_max, z_min, z_max)
    return {"players": players}

@router.get("/players/{nickname}/face.webp")
async def get_player_face(nickname: str):
    face_path = await player_manager.get_player_face_path(nickname)
    if not face_path:
        return Response(status_code=404)
    return FileResponse(face_path, media_type="image/webp")
