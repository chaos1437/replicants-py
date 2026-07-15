"""Симуляция с веб-рендером (aiohttp + WebSocket + Canvas)

Запуск:
    python example_web.py

Открыть браузер: http://localhost:8080

Авто-режим: сервер сам выполняет тики и пушит состояние на страницу.
Ручной режим: нажать на canvas — один тик.
Пробел — пауза/продолжение авто-режима.
"""
import asyncio
import logging
from pathlib import Path

from aiohttp import web
from aiohttp.client_exceptions import ClientConnectionResetError

from config.settings import load_config
from core.world import World
from core.world_map import WorldMap
from services.simulation_service import SimulationService
from services.state_provider import StateProvider

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# HTML + JS — встроенная статика
# ═══════════════════════════════════════════════════════════════

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Replicants Simulation</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #111; color: #ccc; font: 14px monospace; display: flex;
         flex-direction: column; align-items: center; padding: 10px; }
  canvas { border: 1px solid #333; cursor: pointer; image-rendering: pixelated; }
  #stats, #controls { padding: 8px 0; text-align: center; }
  #controls button { background: #333; color: #ccc; border: 1px solid #555;
                     padding: 4px 16px; cursor: pointer; font: 12px monospace; }
  #controls button:hover { background: #555; }
  .badge { display: inline-block; margin: 0 8px; }
</style>
</head>
<body>
<div id="controls">
  <span class="badge" id="conn">⬤</span>
  <button id="btnAuto">▶ Авто</button>
  <span class="badge">Tick: <span id="lblTick">0</span></span>
  <span class="badge">Ботов: <span id="lblBots">0</span></span>
  <span class="badge">Ср.возраст: <span id="lblAge">0</span></span>
</div>
<canvas id="sim" width="800" height="800"></canvas>
<div id="stats"></div>
<script>
  const WS_URL = `ws://${location.host}/ws`;
  const canvas = document.getElementById('sim');
  const ctx = canvas.getContext('2d');
  let autoMode = false;

  const conn = document.getElementById('conn');
  const lblTick = document.getElementById('lblTick');
  const lblBots = document.getElementById('lblBots');
  const lblAge = document.getElementById('lblAge');

  let ws;

  function connect() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => { conn.style.color = '#0f0'; conn.title = 'Connected'; };
    ws.onclose = () => { conn.style.color = '#f00'; conn.title = 'Disconnected';
                         setTimeout(connect, 1000); };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'state') render(data);
    };
  }
  connect();

  function render(data) {
    const w = data.width, h = data.height;
    const cw = canvas.width / w, ch = canvas.height / h;

    // Фон
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Ячейки — энергия фона (синий канал)
    if (data.cells) {
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const e = data.cells[y][x];
          const v = Math.min(255, Math.max(0, e));
          ctx.fillStyle = `rgb(0, ${Math.floor(v * 0.4)}, ${Math.floor(v * 0.8 + 40)})`;
          ctx.fillRect(x * cw, (h - 1 - y) * ch, cw, ch);
        }
      }
    }

    // Боты — цвет по энергии
    if (data.bots) {
      for (const b of data.bots) {
        if (!b.alive) continue;
        const bx = b.x * cw, by = (h - 1 - b.y) * ch;
        const e = b.energy;
        let color;
        if (e > 200) color = '#0f0';
        else if (e > 100) color = '#ff0';
        else if (e > 50) color = '#f80';
        else color = '#f00';
        ctx.fillStyle = color;
        ctx.fillRect(bx + 1, by + 1, cw - 2, ch - 2);
      }
    }

    // Статистика
    if (data.stats) {
      lblTick.textContent = data.tick;
      lblBots.textContent = data.stats.alive_bots;
      lblAge.textContent = data.stats.average_age.toFixed(1);
    }
  }

  // Нажатие на canvas — один тик (ручной режим)
  canvas.addEventListener('click', () => {
    if (ws.readyState === WebSocket.OPEN) ws.send('next');
  });

  // Пробел — пауза авто-режима
  document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
      e.preventDefault();
      toggleAuto();
    }
  });

  document.getElementById('btnAuto').addEventListener('click', toggleAuto);

  function toggleAuto() {
    autoMode = !autoMode;
    document.getElementById('btnAuto').textContent = autoMode ? '❚❚ Пауза' : '▶ Авто';
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(autoMode ? 'start_auto' : 'stop_auto');
    }
  }
</script>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════════
# WebSocket handler
# ═══════════════════════════════════════════════════════════════

# Shared state между WS-сессиями
class SimState:
    """Обёртка для доступа к симуляции из asyncio"""
    def __init__(self, service: SimulationService, provider: StateProvider):
        self.service = service
        self.provider = provider
        self.auto_mode = False
        self._lock = asyncio.Lock()


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sim: SimState = request.app['sim']
    loop = asyncio.get_event_loop()

    async def safe_send(data):
        """Отправить JSON, не падать если клиент отключился"""
        try:
            await ws.send_json(data)
        except (ConnectionResetError, ClientConnectionResetError):
            pass

    async def send_state():
        """Собрать и отправить состояние симуляции клиенту"""
        state = sim.provider.get_world_state()
        stats = sim.provider.get_statistics()

        # Ячейки: 2D массив энергии (обращаемся напрямую к map)
        w, h = state['width'], state['height']
        world_map = sim.provider.world.map.map  # list[list[Cell]]
        cells_energy = [[world_map[y][x]._energy for x in range(w)] for y in range(h)]

        # Боты компактно
        bots = []
        for b in state['bots']:
            if b['alive']:
                bots.append({
                    'x': b['x'], 'y': b['y'],
                    'energy': b['energy'], 'alive': b['alive'],
                })

        await safe_send({
            'type': 'state',
            'width': w,
            'height': h,
            'tick': stats['tick'],
            'cells': cells_energy,
            'bots': bots,
            'stats': stats,
        })

    async def do_tick_and_send():
        """Один тик + отправка состояния"""
        async with sim._lock:
            await loop.run_in_executor(None, sim.service.tick)
        await send_state()

    # Авто-режим: цикл тиков
    async def auto_loop():
        while True:
            if sim.auto_mode:
                await do_tick_and_send()
            await asyncio.sleep(0)  # yield, чтобы не блокировать сокет

    auto_task = asyncio.create_task(auto_loop())

    try:
        # Отправить начальное состояние
        await send_state()

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                cmd = msg.data.strip()
                if cmd == 'next':
                    await do_tick_and_send()
                elif cmd == 'start_auto':
                    sim.auto_mode = True
                elif cmd == 'stop_auto':
                    sim.auto_mode = False
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WS error: {ws.exception()}")
    finally:
        sim.auto_mode = False
        auto_task.cancel()
        logger.info("WebSocket disconnected")

    return ws


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

async def main():
    config, args = load_config()

    # Логирование
    logging.basicConfig(
        level=config.log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%d/%m/%y %H:%M'
    )

    # Мир
    if config.save_file.exists():
        from persistence.serializer import WorldSerializer
        logger.info(f"Loading world from {config.save_file}")
        world = WorldSerializer.load(config.save_file, config.genome)
    else:
        logger.info("Creating new world")
        world_map = WorldMap(config.world.width, config.world.height)
        world = World(world_map)
        world.genome_config = config.genome

    # Сервисы
    service = SimulationService(world, config)
    provider = StateProvider(world)
    sim = SimState(service, provider)

    # aiohttp приложение
    app = web.Application()

    async def index_handler(request):
        return web.Response(text=INDEX_HTML, content_type='text/html')

    app['sim'] = sim
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    logger.info("=" * 60)
    logger.info("WEB SIMULATION STARTING")
    logger.info(f"  Open http://localhost:8080")
    logger.info(f"  World: {world.width}x{world.height}")
    logger.info(f"  Config: {config}")
    logger.info("=" * 60)

    print(f"\n  🌐  http://localhost:8080\n")
    print(f"  Клик по canvas — один тик")
    print(f"  Пробел — пауза/продолжение авто-режима")
    print(f"  Ctrl+C для выхода\n")

    try:
        await asyncio.Event().wait()  # бесконечное ожидание
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        service.stop()
        await runner.cleanup()

    if not config.save_file.exists():
        from persistence.serializer import WorldSerializer
        logger.info(f"Saving world to {config.save_file}")
        WorldSerializer.save(world, config.save_file)

    logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
