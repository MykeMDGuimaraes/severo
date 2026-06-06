"""
Interface base para canais de mensagem do Severo.
Cada canal implementa parse_incoming (entrada) e send (saída).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParseResult:
    """
    Resultado da análise de um webhook.

    action:
      - "process"        → processar normalmente (user_id, text, message_id)
      - "ignore"         → descartar; `reason` diz o motivo (group|internal|fromMe|no_text|unknown_event)
      - "media_fallback" → mídia sem texto; responder mensagem fixa (sem modelo)
    """
    action: str = "process"
    user_id: str = ""
    text: str = ""
    message_id: str = ""
    reason: str = ""


class Channel(ABC):
    name: str  # identificador do canal: "whatsapp" | "telegram"

    @abstractmethod
    def parse_incoming(self, body: dict) -> ParseResult:
        """
        Analisa o payload do webhook e retorna um ParseResult.
        Nunca retorna None — sempre um ParseResult com action apropriada.
        """

    @abstractmethod
    def send(self, user_id: str, texto: str) -> bool:
        """
        Envia mensagem ao usuário.
        Retorna True em sucesso, False em falha — nunca propaga exceção.
        """
