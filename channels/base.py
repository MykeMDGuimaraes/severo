"""
Interface base para canais de mensagem do Argos.
Cada canal implementa parse_incoming (entrada) e send (saída).
"""
from abc import ABC, abstractmethod


class Channel(ABC):
    name: str  # identificador do canal: "whatsapp" | "telegram"

    @abstractmethod
    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        """
        Extrai (identificador_usuario, texto) do payload do webhook.
        Retorna None se a mensagem deve ser ignorada
        (fromMe, evento desconhecido, sem texto, etc.).
        """

    @abstractmethod
    def send(self, user_id: str, texto: str) -> bool:
        """
        Envia mensagem ao usuário.
        Retorna True em sucesso, False em falha — nunca propaga exceção.
        """
