"""
Canal Telegram via Bot API.
Usado para testes internos do funil — canal de produção é WhatsApp.
"""
import logging
import os

import requests

from .base import Channel

logger = logging.getLogger("argos")


class TelegramChannel(Channel):
    name = "telegram"

    def __init__(self) -> None:
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def _api(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def parse_incoming(self, body: dict) -> tuple[str, str] | None:
        # Ignorar mensagens editadas para evitar reprocessamento
        if "edited_message" in body:
            return None

        message = body.get("message", {})
        if not message:
            return None

        chat_id = str(message.get("chat", {}).get("id", ""))
        if not chat_id:
            return None

        texto = message.get("text", "").strip()
        if not texto:
            return None

        return chat_id, texto

    def send(self, chat_id: str, texto: str) -> bool:
        try:
            resp = requests.post(
                self._api("sendMessage"),
                json={"chat_id": chat_id, "text": texto},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("[TELEGRAM] Erro ao enviar para %s: %s", chat_id, e)
            return False

    def setup_webhook(self, webhook_url: str, secret_token: str) -> bool:
        """
        Registra o webhook no Telegram. Chamado uma vez no startup.
        Telegram exige HTTPS na URL do webhook.
        """
        try:
            resp = requests.post(
                self._api("setWebhook"),
                json={"url": webhook_url, "secret_token": secret_token},
                timeout=10,
            )
            ok = resp.status_code == 200
            if not ok:
                logger.error("[TELEGRAM] Falha ao registrar webhook: %s", resp.text)
            return ok
        except Exception as e:
            logger.error("[TELEGRAM] Erro ao registrar webhook: %s", e)
            return False
