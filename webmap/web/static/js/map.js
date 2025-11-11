document.addEventListener("DOMContentLoaded", () => {
  // === 1. Инициализация карты ===
  const map = L.map("map", {
    crs: L.CRS.Simple,
    minZoom: 1,
    maxZoom: 5,
    zoomControl: false,
  });

  L.control.zoom({ position: "bottomright" }).addTo(map);
  map.setView([0, 0], 2);

  // === 2. Тайловый слой ===
  L.tileLayer("/api/v1/tiles/{z}/{x}/{y}.webp", {
    minZoom: 1,
    maxZoom: 5,
    tileSize: 256,
    noWrap: true,
    continuousWorld: true,
    attribution: null,
  }).addTo(map);

  // === 3. Отображение игроков ===
  let playerMarkers = {};

  async function updatePlayers() {
    try {
      const bounds = map.getBounds();
      const sw = bounds.getSouthWest();
      const ne = bounds.getNorthEast();

      const x_min = Math.floor(sw.lng);
      const x_max = Math.ceil(ne.lng);
      const z_min = Math.floor(sw.lat);
      const z_max = Math.ceil(ne.lat);

      const resp = await fetch(
        `/api/v1/players?x_min=${x_min}&x_max=${x_max}&z_min=${z_min}&z_max=${z_max}`,
      );
      const data = await resp.json();

      // Удаляем ушедших
      for (const nick of Object.keys(playerMarkers)) {
        if (!data.players.some((p) => p.nickname === nick)) {
          playerMarkers[nick].remove();
          delete playerMarkers[nick];
        }
      }

      // Добавляем/обновляем
      for (const player of data.players) {
        const icon = L.icon({
          iconUrl: `/api/v1/players/${player.nickname}/face.webp`,
          iconSize: [32, 32],
          iconAnchor: [16, 16], // ← центр иконки = координата
          className: "player-icon", // для стилей (опционально)
        });

        if (playerMarkers[player.nickname]) {
          playerMarkers[player.nickname].setLatLng([player.z, player.x]);
        } else {
          const marker = L.marker([player.z, player.x], { icon });
          // Popup при клике (с ником и координатами)
          marker.bindPopup(`
            <div class="player-popup">
              <div class="player-header">
                <img src="/api/v1/players/${player.nickname}/face.webp"
                     class="popup-avatar"
                     width="32" height="32"
                     onerror="this.parentNode.innerHTML='<div style=\'color:#0ff\'>?\'">
                <h3>${player.nickname}</h3>
              </div>
              <div class="player-coords">
                <span>x: ${player.x}</span>
                <span>y: ${player.y}</span>
                <span>z: ${player.z}</span>
              </div>
            </div>
          `);
          marker.addTo(map);
          playerMarkers[player.nickname] = marker;
        }
      }
    } catch (e) {
      console.error("Ошибка обновления игроков:", e);
    }
  }

  updatePlayers();
  setInterval(updatePlayers, 5000);

  // === 4. Координаты по клику ===
  map.on("click", (e) => {
    const x = Math.round(e.latlng.lng);
    const z = Math.round(e.latlng.lat);
    document.getElementById("coords").textContent = `x: ${x}, z: ${z}`;
  });

  // === 5. Копирование координат ===
  const coordsEl = document.getElementById("coords");
  if (coordsEl) {
    coordsEl.addEventListener("click", async (e) => {
      e.stopPropagation();
      e.preventDefault();
      const text = coordsEl.textContent;
      try {
        await navigator.clipboard.writeText(text);
        coordsEl.classList.add("copied");
        setTimeout(() => coordsEl.classList.remove("copied"), 400);
      } catch (err) {
        alert("Не удалось скопировать координаты.");
      }
    });
  }
});
