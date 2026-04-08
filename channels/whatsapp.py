"""
Canal WhatsApp via UazAPI.
Encapsula parsing de webhooks e envio de mensagens.
"""
import logging
import os

import requests

from .base import Channel

logger = logging.getLogger("argos")


def _headers() -> dict:
    return {"apikey": os.getenv("UAZAPI_TOKEN", "")}


def _url(path: str) -> str:
    base = os.getenv("UAZAPI_URL", "").rstrip("/")
    return f"{base}{path}"


class WhatsAppChannel(Channel):
    name = "whatsapp"

    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        evento = body.get("event", "")
        if evento not in ("MESSAGES_UPSERT", "messages.upsert"):
            return None

        data = body.get("data", {})
        key = data.get("key", {})

        # Ignorar mensagens enviadas pelo próprio Argos
        if key.get("fromMe", False):
            return None

        jid: str = key.get("remoteJid", "")
        numero = jid.replace("@s.whatsapp.net", "").replace("@g.us", "")
        if not numero:
            return None

        texto = self._extrair_texto(data.get("message", {}))
        if not texto:
            return None

        return numero, texto

    def _extrair_texto(self, msg_data: dict) -> str:
        return (
            msg_data.get("conversation")
            or msg_data.get("extendedTextMessage", {}).get("text")
            or msg_data.get("imageMessage", {}).get("caption")
            or msg_data.get("videoMessage", {}).get("caption")
            or msg_data.get("buttonsResponseMessage", {}).get("selectedDisplayText")
            or msg_data.get("listResponseMessage", {}).get("title")
            or ""
        ).strip()

    def send(self, numero: str, texto: str) -> bool:
        instance = os.getenv("UAZAPI_INSTANCE", "argos")
        try:
            resp = requests.post(
                _url(f"/message/sendText/{instance}"),
                headers=_headers(),
                json={"number": numero, "text": texto, "delay": 1200},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("[WHATSAPP] Erro ao enviar para %s: %s", numero[:6], e)
            return False
