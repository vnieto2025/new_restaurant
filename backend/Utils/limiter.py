import threading
import time
from collections import defaultdict, deque
from Utils.tools import CustomException


class Limiter:
    """ Límite de intentos por clave en una ventana de tiempo (en memoria).
        Sirve para una sola instancia del backend; con varias se pasa a Redis (ADR-004). """

    def __init__(self):
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int, message: str):
        current = time.monotonic()
        with self.lock:
            hits = self.hits[key]
            while hits and current - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                raise CustomException(message, 429)
            hits.append(current)

    def reset(self, key: str = None):
        with self.lock:
            if key is None:
                self.hits.clear()
            else:
                self.hits.pop(key, None)


limiter = Limiter()
