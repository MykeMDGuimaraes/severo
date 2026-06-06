"""
Dedup de mensagens por messageId — cache em memória, TTL curto.
Single replica no Swarm: memória basta. Múltiplas réplicas exigiriam
dedup compartilhado (Supabase) — ver README.
"""
import time as _time


class DedupCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl = ttl_seconds
        self._seen: dict[str, float] = {}

    def is_duplicate(self, message_id: str, now: float | None = None) -> bool:
        """
        True se message_id já foi visto dentro do TTL.
        IDs vazios nunca são considerados duplicados (sem id confiável → processa).
        Faz limpeza lazy dos expirados a cada chamada.
        """
        if not message_id:
            return False
        agora = now if now is not None else _time.monotonic()

        # Limpeza lazy
        expirados = [k for k, ts in self._seen.items() if agora - ts >= self.ttl]
        for k in expirados:
            del self._seen[k]

        if message_id in self._seen:
            return True

        self._seen[message_id] = agora
        return False
