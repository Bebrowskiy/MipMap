# core/player_manager.py
import asyncio
import time
from pathlib import Path
from typing import Dict, Optional, List
from PIL import Image
import io

PLAYER_TTL = 60  # секунд - через сколько удалить игрока, если он не обновлялся
FACES_DIR = Path("data/player_faces")
FACES_DIR.mkdir(parents=True, exist_ok=True)

class PlayerManager:
    def __init__(self):
        self._players: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def update_player(self, nickname: str, x: int, y: int, z: int, face_bytes: bytes):
        async with self._lock:
            # Сохраняем аватарку как WebP 16x16
            face_path = FACES_DIR / f"{nickname}.webp"
            try:
                img = Image.open(io.BytesIO(face_bytes)).convert("RGBA")
                if img.size != (128, 128):
                    img = img.resize((128, 128), Image.NEAREST)
                img.save(face_path, "WEBP", lossless=True)
            except Exception:
                # Заглушка: бирюзовый квадрат
                img = Image.new("RGBA", (128, 128), (0, 255, 255, 255))
                img.save(face_path, "WEBP", lossless=True)

            self._players[nickname] = {
                "x": x,
                "y": y,
                "z": z,
                "last_update": time.time()
            }

    async def get_players_in_region(self, x_min: int, x_max: int, z_min: int, z_max: int) -> List[dict]:
        now = time.time()
        result = []
        async with self._lock:
            to_remove = []
            for nick, data in self._players.items():
                if now - data["last_update"] > PLAYER_TTL:
                    to_remove.append(nick)
                    continue
                if x_min <= data["x"] <= x_max and z_min <= data["z"] <= z_max:
                    result.append({
                        "nickname": nick,
                        "x": data["x"],
                        "y": data["y"],
                        "z": data["z"]
                    })
            for nick in to_remove:
                self._players.pop(nick, None)
        return result

    async def get_player_face_path(self, nickname: str) -> Optional[Path]:
        path = FACES_DIR / f"{nickname}.webp"
        return path if path.exists() else None

# Глобальный экземпляр
player_manager = PlayerManager()
