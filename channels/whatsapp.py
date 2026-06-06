"""
Canal WhatsApp via UazAPI.
Encapsula parsing de webhooks e envio de mensagens.
"""
import logging
import os

import requests

from .base import Channel, ParseResult

logger = logging.getLogger("severo")


def _headers() -> dict:
    return {"apikey": os.getenv("UAZAPI_TOKEN", "")}


def _url(path: str) -> str:
    base = os.getenv("UAZAPI_URL", "").rstrip("/")
    return f"{base}{path}"


class WhatsAppChannel(Channel):
    name = "whatsapp"

    def parse_incoming(self, body: dict) -> ParseResult:
        evento = body.get("event", "")
        if evento not in ("MESSAGES_UPSERT", "messages.upsert"):
            return ParseResult(action="ignore", reason="unknown_event")

        data = body.get("data", {})
        key = data.get("key", {})
        message_id = key.get("id", "")

        if key.get("fromMe", False):
            return ParseResult(action="ignore", reason="fromMe", message_id=message_id)

        jid: str = key.get("remoteJid", "")

        # Drop de grupo ANTES de qualquer strip — senão @g.us viraria "número"
        if jid.endswith("@g.us"):
            return ParseResult(action="ignore", reason="group", message_id=message_id)

        numero = jid.replace("@s.whatsapp.net", "")
        if not numero:
            return ParseResult(action="ignore", reason="no_sender", message_id=message_id)

        # Filtro de números internos (equipe) — CSV em INTERNAL_JIDS
        internos = {
            n.strip() for n in os.getenv("INTERNAL_JIDS", "").split(",") if n.strip()
        }
        if numero in internos:
            return ParseResult(action="ignore", reason="internal", message_id=message_id)

        texto = self._extrair_texto(data.get("message", {}))
        if not texto:
            # Há mídia mas sem texto → fallback fixo (item 7), ainda passa pelo dedup
            return ParseResult(
                action="media_fallback", user_id=numero, message_id=message_id
            )

        return ParseResult(
            action="process", user_id=numero, text=texto, message_id=message_id
        )

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
        instance = os.getenv("UAZAPI_INSTANCE", "severo")
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
