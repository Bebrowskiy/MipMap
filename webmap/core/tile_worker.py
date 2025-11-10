from pathlib import Path

from core.texture_manager import TextureManager
from core.tile_renderer import TileRenderer
from core.models import Block

TEXTURE_DIR = Path("assets/textures/blocks")
texture_manager = TextureManager(TEXTURE_DIR)
tile_renderer = TileRenderer(texture_manager)

def render_tile_in_process(blocks_data, tile_x: int, tile_y: int, zoom: int) -> bytes:
    """
    Рендер тайла в отдельном процессе
    Возвращает байты WebP-image
    """
    blocks = [Block(coordinates=(x, y, z), name=name) for (x, y, z, name) in blocks_data]

    img = tile_renderer.render_tile(blocks, tile_x=tile_x, tile_y=tile_y, zoom=zoom)

    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="WEBP", lossless=True)
    return buf.getvalue()
