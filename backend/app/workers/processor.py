"""Worker legado — use sync_worker.py"""

import asyncio
import json
import redis
from ..config import settings

QUEUE_KEY = "inspear:inform:queue"


async def process_loop():
    r = redis.from_url(settings.redis_url)
    print(f"[worker] Escutando fila {QUEUE_KEY}")
    while True:
        try:
            item = r.blpop(QUEUE_KEY, timeout=5)
            if item:
                _, data = item
                payload = json.loads(data)
                print(f"[worker] Inform recebido: {payload.get('serial_number')}")
                # MVP: ingestão síncrona via API; worker processará batch TR-069
        except Exception as e:
            print(f"[worker] erro: {e}")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(process_loop())